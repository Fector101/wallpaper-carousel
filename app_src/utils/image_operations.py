import os, time
import shutil
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from android_notify.internal.java_classes import String, autoclass, cast, Intent
from kivy.clock import Clock
from android_notify.config import on_android_platform, get_python_activity_context, on_pydroid_app
from kivymd.app import MDApp

from ui.widgets.layouts import LoadingLayout
from utils.helper import appFolder
from utils.config_manager import ConfigManager
from utils.logger import app_logger

my_config = ConfigManager()

class ImageOperation:
    def __init__(self,load_saved):
        self.app = MDApp.get_running_app()

        self.showing_loading_screen = False # To fix when no image chosen from Half Popup
        self._file_picker_active = False # True while file picker is open; prevents on_resume from tearing down spinner
        self._processing_intent = False # True when import_from_intent is running; guards against plyer duplicate
        self._unique_lock = threading.Lock()
        self._picker_request_code = 65432
        self.spinner_layout = None
        self.app_dir = Path(appFolder())
        self.intent = None
        self.wallpapers_dir = self.app_dir / "wallpapers"
        try:
            self.wallpapers_dir.mkdir(parents=True, exist_ok=True)
            (self.wallpapers_dir / "thumbs").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating wallpapers directory: {e}")

        self.load_saved = load_saved

    def show_spinner(self):
        def ui(_):
            self.spinner_layout = LoadingLayout()
            self.showing_loading_screen = True
        Clock.schedule_once(ui)

    def hide_spinner(self):
        """
        Don't Call self.__copy_add removes spinner, This method is for a specific edge case
        Fix for Half Screen File Chooser filechooser.open_file not calling on_selection"""
        if self.showing_loading_screen:
            Clock.schedule_once(self.spinner_layout.remove)
        self.showing_loading_screen = False

    def __copy_add(self, files):
        print(f"[DBG] __copy_add: entered with {len(files)} files: {files}")
        if not files:
            print("[DBG] __copy_add: no files, cleaning up")
            self._file_picker_active = False
            self._processing_intent = False
            Clock.schedule_once(lambda dt: self.load_saved(has_files=False))
            self.hide_spinner()
            return
        try:
            uris = self.get_selected_uris()
            print(f"[DBG] __copy_add: got {len(uris)} URIs from intent")
        except Exception as e:
            print(f"[DBG] __copy_add: error getting uris: {e}")
            uris = []
        if not uris:
            print(f"[DBG] __copy_add: no URIs from intent, files={files}")

        self.intent = None
        copy_time = time.time()

        if uris:
            try:
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                _mAct = PythonActivity.mActivity
                for _uri in uris:
                    try:
                        _mAct.grantUriPermission(
                            _mAct.getPackageName(), _uri,
                            Intent.FLAG_GRANT_READ_URI_PERMISSION
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        new_images = []
        images_lock = threading.Lock()

        def process_one(i, src):
            result = None
            print(f"[DBG] __copy_add [{i+1}/{len(files)}]: src={src}")
            src_exists = os.path.exists(src)

            if not src_exists:
                print(f"[DBG] __copy_add [{i+1}/{len(files)}]: src does not exist")
                if i < len(uris):
                    dst_name = os.path.basename(src) or f"{int(time.time())}_{i}.png"
                    with self._unique_lock:
                        dst = self.unique(dst_name)
                    print(f"[DBG] __copy_add [{i+1}/{len(files)}]: URI fallback -> {dst}")
                    try:
                        copy_image_to_internal(destination_name=dst, uri=uris[i])
                        create_thumbnail(dst, destination_dir=self.wallpapers_dir)
                        result = str(dst)
                    except Exception as e:
                        print(f"[DBG] __copy_add [{i+1}/{len(files)}]: URI fallback failed: {e}")
                else:
                    print(f"[DBG] __copy_add [{i+1}/{len(files)}]: no URI fallback, skip")
                return result

            with self._unique_lock:
                dst = self.unique(os.path.basename(src))
            print(f"[DBG] __copy_add [{i+1}/{len(files)}]: destination={dst}")

            try:
                shutil.copy2(src, dst)
                os.utime(dst, (copy_time, copy_time))
            except PermissionError:
                print(f"[DBG] __copy_add [{i+1}/{len(files)}]: PermissionError, java copy")
                if i < len(uris):
                    try:
                        copy_image_to_internal(destination_name=dst, uri=uris[i])
                    except Exception as e:
                        print(f"[DBG] __copy_add [{i+1}/{len(files)}]: java copy failed: {e}")
                        return result
                else:
                    return result
            except Exception as e:
                print(f"[DBG] __copy_add [{i+1}/{len(files)}]: copy error: {e}")
                return result

            try:
                create_thumbnail(dst, destination_dir=self.wallpapers_dir)
            except Exception as e:
                print(f"[DBG] __copy_add [{i+1}/{len(files)}]: thumbnail error: {e}")

            return str(dst)

        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in pool.map(lambda args: process_one(*args), enumerate(files)):
                if result:
                    new_images.append(result)

        print(f"[DBG] __copy_add: batch-adding {len(new_images)} wallpapers to config")
        data = my_config._read()
        for img in new_images:
            if img not in data["wallpapers"]:
                data["wallpapers"].append(img)
        my_config._write(data)

        print(f"[DBG] __copy_add: scheduling ui_things")
        Clock.schedule_once(self.ui_things, 0)

    def copy_add(self, files):
        if self._processing_intent:
            print("[DBG] copy_add: import_from_intent already running, skipping plyer callback")
            return
        threading.Thread(target=self.__copy_add, args=(files,)).start()

    def unique(self, destination_name):
        destination_path = self.wallpapers_dir / destination_name
        base, ext = os.path.splitext(destination_name)
        i = 1
        while destination_path.exists():
            destination_path = self.wallpapers_dir / f"{base}_{i}{ext}"
            i += 1
        return destination_path

    def ui_things(self, _):
        self._file_picker_active = False
        print(f"[DBG] ui_things: refreshing gallery and hiding spinner")
        self.load_saved()
        self.hide_spinner()

    def get_selected_uris(self):
        uris = []
        if not self.intent:
            print("[DBG] get_selected_uris: no intent")
            return uris

        clip = self.intent.getClipData()
        if clip:
            count = clip.getItemCount()
            print(f"[DBG] get_selected_uris: clipData with {count} items")
            for i in range(count):
                uri = clip.getItemAt(i).getUri()
                if uri:
                    print(f"[DBG] get_selected_uris: clip item {i}: {uri.toString() if uri else 'None'}")
                    uris.append(uri)
            print(f"[DBG] get_selected_uris: returning {len(uris)} URIs from clip")
            return uris

        uri = self.intent.getData()
        if uri:
            print(f"[DBG] get_selected_uris: single URI: {uri.toString()}")
            uris.append(uri)
        else:
            print("[DBG] get_selected_uris: no clipData and no data URI")

        print(f"[DBG] get_selected_uris: returning {len(uris)} URIs")
        return uris

    def has_pending_intent(self):
        return self.intent is not None

    def launch_file_picker(self):
        """Launch Android file picker directly, bypassing plyer's slow URI resolution."""
        if not on_android_platform():
            return
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        mActivity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
        mActivity.startActivityForResult(
            Intent.createChooser(intent, cast('java.lang.CharSequence', String("Select Images"))),
            self._picker_request_code
        )

    def import_from_intent(self):
        """Process URIs from a pending intent in parallel.
        Runs in a background thread; calls ui_things when done."""
        if self._processing_intent:
            print("[DBG] import_from_intent: already running, skipping")
            return
        self._processing_intent = True
        def _run():
            try:
                uris = self.get_selected_uris()
                log = f"import_from_intent: got {len(uris)} URIs from intent"
                print(log)
                app_logger.info(log)
                if not uris:
                    self._file_picker_active = False
                    self._processing_intent = False
                    Clock.schedule_once(lambda dt: self.hide_spinner(), 0)
                    return

                self.intent = None

                # Grant URI permission so processed images are accessible
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                _mAct = PythonActivity.mActivity
                for _uri in uris:
                    try:
                        _mAct.grantUriPermission(
                            _mAct.getPackageName(), _uri,
                            Intent.FLAG_GRANT_READ_URI_PERMISSION
                        )
                    except Exception:
                        pass

                new_images = []
                images_lock = threading.Lock()

                def process_one(i, uri):
                    try:
                        log_i = f"import_from_intent [{i+1}/{len(uris)}]: processing {uri}"
                        print(log_i)
                        app_logger.info(log_i)
                        file_name = get_file_name_from_uri(uri)
                        if not file_name:
                            file_name = f"{int(time.time())}_{i}.png"
                        with self._unique_lock:
                            destination_path = self.unique(file_name)
                        log_i_cp = f"import_from_intent: copying -> {destination_path}"
                        print(log_i_cp)
                        app_logger.info(log_i_cp)
                        copy_image_to_internal(destination_name=destination_path, uri=uri)
                        create_thumbnail(destination_path, destination_dir=self.wallpapers_dir)
                        with images_lock:
                            new_images.append(str(destination_path))
                        log_i_done = f"import_from_intent: done {destination_path}"
                        print(log_i_done)
                        app_logger.info(log_i_done)
                    except Exception as e:
                        err = f"import_from_intent: error importing {uri}: {e}"
                        print(err)
                        app_logger.exception(err)
                        traceback.print_exc()

                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda args: process_one(*args), enumerate(uris)))

                summary = f"import_from_intent: imported {len(new_images)}/{len(uris)} images"
                print(summary)
                app_logger.info(summary)
                data = my_config._read()
                for img in new_images:
                    if img not in data["wallpapers"]:
                        data["wallpapers"].append(img)
                my_config._write(data)
                self._processing_intent = False
                Clock.schedule_once(lambda dt: self.ui_things(dt), 0)
                Clock.schedule_once(lambda dt: self.app.bottom_bar.show(animation=False, hidden_by="pic"), 0)
            except Exception as e:
                self._file_picker_active = False
                self._processing_intent = False
                err = f"import_from_intent: error: {e}"
                print(err)
                app_logger.exception(err)
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.hide_spinner(), 0)

        threading.Thread(target=_run, daemon=True).start()

    def hide_nav_btns(self):
        def ui_thing(*a):
            self.app.bottom_bar.hide(animation=False, hidden_by="pic")
        Clock.schedule_once(ui_thing)
    def handle_image_sharing_from_others_app(self, intent):
        tag="handle_image_sharing_from_others_app"
        if intent is None:
            app_logger.warning(f"{tag}- Intent is None")
            return None
        try:
            action = intent.getAction()
            type_ = intent.getType()

            # print(f"{tag} -start {len(os.listdir(self.wallpapers_dir))}, action:{action},type_{type_}")
            if action == Intent.ACTION_SEND:
                uri = intent.getParcelableExtra(Intent.EXTRA_STREAM)
                if uri:
                    uri = cast("android.net.Uri", uri)
                else:
                    uri = intent.getData()

                if uri and is_image_uri(uri):
                    self.hide_nav_btns()
                    self.show_spinner()
                    def start_thread(_):
                        threading.Thread(target=self._process_single_image,args=(uri,),daemon=True).start()
                    Clock.schedule_once(start_thread, 0)


            elif action == Intent.ACTION_SEND_MULTIPLE:
                uris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM)
                image_uris = [u for u in uris if is_image_uri(u)]
                if image_uris:
                    self.hide_nav_btns()
                    self.show_spinner()
                    def start_thread(_):
                        threading.Thread(target=self._process_multiple_images,args=(image_uris,),daemon=True).start()
                    Clock.schedule_once(start_thread, 0)

            else:
                app_logger.warning(f"Didn't recognize intent action: {action}, type:{type_}")

            # print(f"{tag} -end {len(os.listdir(self.wallpapers_dir))}")

        except Exception as error_handle_image_sharing_from_others_app:
            print(f"error_{tag}",error_handle_image_sharing_from_others_app)
            traceback.print_exc()


    def setup_share_from_others_to_app_listener(self):
        if not on_android_platform():
            app_logger.warning("Can't Share Image to App, You're not on Android")
            return
        elif on_pydroid_app():
            app_logger.warning("NewIntentListener proxy can't be created on pydroid3")
            return
        try:
            from android import activity  # type: ignore
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity.bind(on_new_intent=self.handle_image_sharing_from_others_app)

            # Handle initial intent when app starts
            self.handle_image_sharing_from_others_app(PythonActivity.mActivity.getIntent())
        except Exception as error_setup_share_from_others_to_app_listener:
            print("error_setup_share_from_others_to_app_listener",error_setup_share_from_others_to_app_listener)
            traceback.print_exc()

    def _process_multiple_images(self, image_uris):
        try:
            new_images = []
            if image_uris and len(image_uris) > 0:
                for each_uri in image_uris:
                    file_path = self.unique(get_file_name_from_uri(each_uri))
                    new_images.append(str(file_path))
                    copy_image_to_internal(destination_name=file_path, uri=each_uri)
                    print(f"done shared multiple{file_path}")

            for img in new_images:
                my_config.add_wallpaper(img)

            print("shared multiple")

        except Exception as e:
            print("error_processing_images", e)

        finally:
            Clock.schedule_once(self.ui_things)

    def _process_single_image(self, uri):
        try:

            file_path = self.unique(get_file_name_from_uri(uri))
            my_config.add_wallpaper(str(file_path))

            copy_image_to_internal(destination_name=file_path, uri=uri)

            print(f"done shared single{file_path}")

        except Exception as e:
            print("error_processing_single", e)

        finally:
            Clock.schedule_once(self.ui_things)


def create_thumbnail(src, destination_dir=None, size=(320, 320), quality=60):
    """Create a low-resolution JPEG thumbnail for src and return its path.
    If Pillow is not available or creation fails, returns the original path string.
    """

    if str(src).endswith(".webp"):
        return str(src)

    try:
        from PIL import Image
    except ImportError:
        Image=None
        if not on_android_platform():
            print("Pillow not available, cannot create thumbnail.")
            # Pillow not available and not on android -> fall back to original image path
            return str(src)

    try:
        src_path = Path(src)
        destination = thumbnail_path_for(src_path, destination_dir)
        # If thumbnail already exists and is newer than source, reuse it
        if destination.exists() and destination.stat().st_mtime >= src_path.stat().st_mtime:
            return str(destination)

        if Image:
            with Image.open(src_path) as im:
                im = im.convert('RGB')
                im.thumbnail(size, Image.LANCZOS)
                im.save(destination, format='JPEG', quality=quality)
        elif on_android_platform():
            try:
                use_android_classes_to_create_thumbnail(str(src_path), str(destination), size, quality)
            except Exception as error_using_android_classes_to_create_thumbnail:
                print("error_using_android_classes_to_create_thumbnail",error_using_android_classes_to_create_thumbnail)
                traceback.print_exc()
        return str(destination)
    except OSError as e:
        app_logger.exception(f"OSError creating thumbnail for {src}")
    except Exception as error_making_thumbnail:
        print(f"Error creating thumbnail for: {error_making_thumbnail}", src)
        traceback.print_exc()
        return str(src)


def copy_image_to_internal(destination_name, uri):
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    FileOutputStream = autoclass("java.io.FileOutputStream")
    BufferedInputStream = autoclass("java.io.BufferedInputStream")
    BufferedOutputStream = autoclass("java.io.BufferedOutputStream")

    activity = PythonActivity.mActivity
    cr = activity.getContentResolver()

    if not uri:
        raise Exception("Image not found in MediaStore")

    uri_str = uri.toString() if hasattr(uri, 'toString') else str(uri)
    print(f"[DBG] copy_image_to_internal: start name={destination_name} uri={uri_str}")

    try:
        input_stream = BufferedInputStream(cr.openInputStream(uri))
    except Exception as e:
        print(f"[DBG] copy_image_to_internal: error opening input stream: {e}")
        raise

    internal_dir = activity.getFilesDir().getAbsolutePath()
    destination_path = os.path.join(internal_dir, destination_name)
    print(f"[DBG] copy_image_to_internal: destination_path={destination_path}")

    output_stream = BufferedOutputStream(FileOutputStream(destination_path))

    total = 0
    buffer = bytearray(1024 * 8)
    while True:
        count = input_stream.read(buffer)
        if count == -1:
            break
        output_stream.write(buffer, 0, count)
        total += count

    output_stream.flush()
    input_stream.close()
    output_stream.close()
    print(f"[DBG] copy_image_to_internal: wrote {total} bytes")

    current_time = time.time()
    os.utime(destination_path, (current_time, current_time))

    print(f"[DBG] copy_image_to_internal: done returning {destination_path}")
    return destination_path


def thumbnail_path_for(src, destination_dir=None):
    """Return a consistent thumbnail Path for a source image.
    Thumbnails are stored in a subfolder named 'thumbs' under destination_dir (or source folder by default).
    """
    p = Path(src)
    if destination_dir:
        destination_dir = Path(destination_dir)
    else:
        destination_dir = p.parent
    thumb_dir = destination_dir / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir / f"{p.stem}_thumb.jpg"


def use_android_classes_to_create_thumbnail(src, destination_dir=None, size=(320, 320), quality=60):
    from jnius import autoclass

    BitmapFactory = autoclass('android.graphics.BitmapFactory')
    Bitmap = autoclass('android.graphics.Bitmap')
    BitmapConfig = autoclass('android.graphics.Bitmap$Config')
    CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
    FileOutputStream = autoclass('java.io.FileOutputStream')
    Math = autoclass('java.lang.Math')

    src_path = src
    destination_path = destination_dir
    max_width = size[0]
    max_height = size[1]

    # 1. Load image
    bitmap = BitmapFactory.decodeFile(src_path)
    if bitmap is None:
        raise Exception("Failed to decode image")

    # 2. Convert to RGB (ARGB_8888 ≈ RGB)
    bitmap = bitmap.copy(BitmapConfig.ARGB_8888, False)

    # 3. Compute thumbnail size (keep aspect ratio)
    width = bitmap.getWidth()
    height = bitmap.getHeight()

    scale = min(
        max_width / float(width),
        max_height / float(height)
    )

    new_w = Math.round(width * scale)
    new_h = Math.round(height * scale)

    # High-quality resize (Android internal filter)
    resized = Bitmap.createScaledBitmap(bitmap, new_w, new_h, True)

    # 4. Save as JPEG
    out = FileOutputStream(destination_path)
    resized.compress(CompressFormat.JPEG, quality, out)
    out.close()

    # Cleanup
    bitmap.recycle()
    resized.recycle()


def get_or_create_thumbnail(src, destination_dir=None, size=(320, 320)):
    """Convenience wrapper to obtain a thumbnail path, creating it if necessary."""
    return create_thumbnail(src, destination_dir=destination_dir, size=size)


def save_existing_file_to_public_pictures(input_file_path):
    # Working copying image from app to public path
    from jnius import autoclass
    from android_notify.config import get_python_activity_context
    context = get_python_activity_context()

    Environment = autoclass('android.os.Environment')
    ContentValues = autoclass('android.content.ContentValues')
    BuildVERSION = autoclass('android.os.Build$VERSION')
    File = autoclass('java.io.File')
    FileInputStream = autoclass('java.io.FileInputStream')
    # Nested Java classes
    MediaColumns = autoclass('android.provider.MediaStore$MediaColumns')
    ImagesMedia = autoclass('android.provider.MediaStore$Images$Media')

    # Extract filename
    file_name = os.path.basename(input_file_path)

    # Detect mime type
    if file_name.lower().endswith(".png"):
        mime_type = "image/png"
    else:
        mime_type = "image/jpeg"

    content_values = ContentValues()
    content_values.put(MediaColumns.DISPLAY_NAME, file_name)
    content_values.put(MediaColumns.MIME_TYPE, mime_type)

    if BuildVERSION.SDK_INT >= 29:
        content_values.put(
            MediaColumns.RELATIVE_PATH,
            Environment.DIRECTORY_PICTURES + "/.waller"
        )

    resolver = context.getContentResolver()
    uri = resolver.insert(ImagesMedia.EXTERNAL_CONTENT_URI, content_values)

    if uri:
        input_file = File(input_file_path)
        input_stream = FileInputStream(input_file)
        output_stream = resolver.openOutputStream(uri)

        buffer = bytearray(8192)
        while True:
            length = input_stream.read(buffer)
            if length <= 0:
                break
            output_stream.write(buffer, 0, length)

        input_stream.close()
        output_stream.close()

    print("This is Uri:", uri)
    print("This is File:", input_file_path)
    return uri

    # try:
    #     my_img = os.path.join(os.path.join(os.get cwd(), "assets", "images", "test.jpg"))
    #     save_existing_file_to_public_pictures(my_img)
    # except Exception as e:
    #     print("Error loading images", e)
    #     traceback.print_exc()


def get_image_info(path):
    info_dict = {
                "Pixels": "Nil",
                "Megapixels": "Nil",
                "Size": "Nil",
                "MIME": "Nil"
            }

    # Check if file exists
    import os
    if not os.path.exists(path):
        return info_dict

    size_bytes = os.path.getsize(path)
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
    info_dict["Size"] = size_str

    if not on_android_platform():
        return info_dict

    # Android BitmapFactory
    from jnius import autoclass
    BitmapFactory = autoclass("android.graphics.BitmapFactory")
    Options = autoclass("android.graphics.BitmapFactory$Options")

    opts = Options()
    opts.inJustDecodeBounds = True
    BitmapFactory.decodeFile(path, opts)


    # Dimensions
    width, height = opts.outWidth, opts.outHeight
    pixels_str = f"{width}x{height}"

    # Megapixels
    mp = (width * height) / 1_000_000
    mp_str = f"{mp:.1f} MP"

    # Mime type
    mime = opts.outMimeType

    info_dict["Pixels"] = pixels_str
    info_dict["Megapixels"] = mp_str
    info_dict["MIME"] = mime

    return info_dict


def share_image_to_other_app(image_absolute_path):
    if not on_android_platform():
        app_logger.warning("Can't share to Another App, Not on Android.")
        return None
    try:
        from jnius import autoclass, cast

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        File = autoclass('java.io.File')
        FileProvider = autoclass('androidx.core.content.FileProvider')
        ClipData = autoclass('android.content.ClipData')

        context = PythonActivity.mActivity


        file = File(image_absolute_path)

        uri = FileProvider.getUriForFile(
            context,
            context.getPackageName() + ".fileprovider",
            file
        )

        intent = Intent(Intent.ACTION_SEND)
        intent.setType("image/*")
        intent.putExtra(Intent.EXTRA_STREAM, cast('android.os.Parcelable', uri))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        # preview
        clip = ClipData.newUri(context.getContentResolver(), String("Image"), uri)
        intent.setClipData(clip)

        chooser = Intent.createChooser(intent, String("Share Image"))
        context.startActivity(chooser)
        app_logger.info("Sharing image to other app")

    except Exception as error_from_trying_to_share_image_to_other_apps:
        print("error_from_trying_to_share_image_to_other_apps",error_from_trying_to_share_image_to_other_apps)
        traceback.print_exc()


def share_images_to_other_app(image_paths):
    if not on_android_platform():
        app_logger.warning("Can't share to Another App, Not on Android.")
        return None
    try:
        from jnius import autoclass, cast

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        File = autoclass('java.io.File')
        FileProvider = autoclass('androidx.core.content.FileProvider')
        ArrayList = autoclass('java.util.ArrayList')
        ClipData = autoclass('android.content.ClipData')

        context = PythonActivity.mActivity

        uris = ArrayList()
        for path in image_paths:
            file = File(path)
            uri = FileProvider.getUriForFile(
                context,
                context.getPackageName() + ".fileprovider",
                file
            )
            uris.add(uri)

        intent = Intent(Intent.ACTION_SEND_MULTIPLE)
        intent.setType("image/*")
        intent.putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        clip = ClipData.newUri(context.getContentResolver(), String("Image"), uris.get(0))
        intent.setClipData(clip)

        chooser = Intent.createChooser(intent, String("Share Images"))
        context.startActivity(chooser)
        app_logger.info(f"Sharing {len(image_paths)} images to other app")

    except Exception as error_from_trying_to_share_images_to_other_apps:
        print("error_from_trying_to_share_images_to_other_apps", error_from_trying_to_share_images_to_other_apps)
        traceback.print_exc()


def get_file_name_from_uri(uri):
    try:
        # PythonActivity = autoclass("org.kivy.android.PythonActivity")
        OpenableColumns = autoclass("android.provider.OpenableColumns")

        activity = get_python_activity_context()
        # activity = PythonActivity.mActivity
        cr = activity.getContentResolver()

        cursor = cr.query(uri, None, None, None, None)

        if cursor and cursor.moveToFirst():
            name_index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if name_index != -1:
                file_name = cursor.getString(name_index)
                cursor.close()
                return file_name
    except Exception as error_getting_file_name_from_uri:
        print("error_getting_file_name_from_uri",error_getting_file_name_from_uri)
        traceback.print_exc()
        # fallback if not found
        return f"{int(time.time())}.png"


def is_image_uri(uri):
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    resolver = PythonActivity.mActivity.getContentResolver()
    mime = resolver.getType(uri)
    return mime and mime.startswith("image/")