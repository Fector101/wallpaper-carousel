import os, time
import shutil
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from android_notify.internal.java_classes import String, autoclass, cast, Intent, BuildVersion, Uri, BitmapFactory, File
from kivy.clock import Clock
from android_notify.config import on_android_platform, on_pydroid_app, get_package_name
from kivymd.app import MDApp

from ui.widgets.layouts import LoadingLayout
from utils.helper import appFolder
from utils.config_manager import ConfigManager
from utils.logger import app_logger

if on_android_platform():
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Bitmap = autoclass('android.graphics.Bitmap')
    BitmapConfig = autoclass('android.graphics.Bitmap$Config')
    CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
    FileOutputStream = autoclass('java.io.FileOutputStream')
    Math = autoclass('java.lang.Math')
    ImagesMedia = autoclass("android.provider.MediaStore$Images$Media")
    BufferedInputStream = autoclass("java.io.BufferedInputStream")
    BufferedOutputStream = autoclass("java.io.BufferedOutputStream")
    FileUtils = autoclass("android.os.FileUtils")
    Environment = autoclass('android.os.Environment')
    ContentValues = autoclass('android.content.ContentValues')
    FileInputStream = autoclass('java.io.FileInputStream')
    MediaColumns = autoclass('android.provider.MediaStore$MediaColumns')
    OpenableColumns = autoclass("android.provider.OpenableColumns")
    Options = autoclass("android.graphics.BitmapFactory$Options")
    FileProvider = autoclass('androidx.core.content.FileProvider')
    ClipData = autoclass('android.content.ClipData')
    ArrayList = autoclass('java.util.ArrayList')
    mActivity = PythonActivity.mActivity
    content_resolver = mActivity.getContentResolver()
    package_name = get_package_name()
    file_provider_authority = package_name + ".fileprovider"


my_config = ConfigManager()


def _format_started_time(timestamp):
    return time.strftime('%H:%M:%S', time.localtime(timestamp))


def _add_wallpapers_to_config(new_images):
    data = my_config._read()
    for img in new_images:
        if img not in data["wallpapers"]:
            data["wallpapers"].append(img)
    my_config._write(data)

class ImageOperation:
    def __init__(self,load_saved):
        self.app = MDApp.get_running_app()

        self.showing_loading_screen = False # To fix when no image chosen from Half Popup
        self._file_picker_active = False # True while file picker is open; prevents on_resume from tearing down spinner
        self._processing_intent = False # True when import_from_intent is running; guards against plyer duplicate
        self._processing_start = None # timestamp when import processing began
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

    def __grant_uri_permissions(self, uris):
        for _uri in uris:
            try:
                mActivity.grantUriPermission(
                    package_name, _uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                )
            except Exception as e3:
                app_logger.exception(e3)

    def __copy_add(self, files):
        if not files:
            self._file_picker_active = False
            self._processing_intent = False
            Clock.schedule_once(lambda dt: self.load_saved(has_files=False))
            self.hide_spinner()
            return
        self._processing_start = time.time()
        app_logger.info(
            f"__copy_add: started processing choice at "
            f"{_format_started_time(self._processing_start)}"
        )
        try:
            uris = self.get_selected_uris()
        except Exception as e:
            print(f"[DBG] __copy_add: error getting uris: {e}")
            uris = []
        if not uris:
            print(f"[DBG] __copy_add: no URIs from intent, files={files}")

        self.intent = None
        copy_time = time.time()

        if uris:
            try:
                self.__grant_uri_permissions(uris)
            except Exception as e4:
                app_logger.exception(e4)
                pass

        new_images = []
        images_lock = threading.Lock()

        def process_one(i, src):
            result = None
            src_exists = os.path.exists(src)

            if not src_exists:
                if i < len(uris):
                    dst_name = os.path.basename(src) or f"{int(time.time())}_{i}.png"
                    with self._unique_lock:
                        dst = self.unique(dst_name)
                    try:
                        copy_image_to_internal(destination_name=dst, uri=uris[i])
                        create_thumbnail(dst, destination_dir=self.wallpapers_dir)
                        result = str(dst)
                    except Exception as e:
                        pass
                else:
                    pass
                return result

            with self._unique_lock:
                dst = self.unique(os.path.basename(src))

            try:
                shutil.copy2(src, dst)
                os.utime(dst, (copy_time, copy_time))
            except PermissionError:
                if i < len(uris):
                    try:
                        copy_image_to_internal(destination_name=dst, uri=uris[i])
                    except Exception as e:
                        return result
                else:
                    return result
            except Exception as e:
                return result

            try:
                create_thumbnail(dst, destination_dir=self.wallpapers_dir)
            except Exception as e:
                pass

            return str(dst)

        with ThreadPoolExecutor(max_workers=3) as pool:
            for result in pool.map(lambda args: process_one(*args), enumerate(files)):
                if result:
                    new_images.append(result)

        _add_wallpapers_to_config(new_images)

        Clock.schedule_once(self.ui_things, 0)

    def copy_add(self, files):
        if self._processing_intent:
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
        elapsed = None
        if self._processing_start is not None:
            elapsed = time.time() - self._processing_start
        when = time.strftime('%H:%M:%S')
        elapsed_str = f" ({elapsed:.2f}s after processing started)" if elapsed is not None else ""
        app_logger.info(f"ui_things: about to add widgets at {when}{elapsed_str}")
        self.load_saved()
        self.hide_spinner()
        self._processing_start = None

    def get_selected_uris(self):
        uris = []
        if not self.intent:
            return uris

        clip = self.intent.getClipData()
        if clip:
            count = clip.getItemCount()
            for i in range(count):
                uri = clip.getItemAt(i).getUri()
                if uri:
                    uris.append(uri)
            return uris

        uri = self.intent.getData()
        if uri:
            uris.append(uri)
        else:
            pass

        return uris

    def has_pending_intent(self):
        return self.intent is not None

    def launch_file_picker(self):
        """Launch Android file picker directly, bypassing plyer's slow URI resolution."""
        if not on_android_platform():
            return
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
            return
        self._processing_intent = True
        def _run():
            try:
                self._processing_start = time.time()
                app_logger.info(
                    f"import_from_intent: started processing choice at "
                    f"{_format_started_time(self._processing_start)}"
                )
                uris = self.get_selected_uris()
                log = f"import_from_intent: got {len(uris)} URIs from intent"
                if not uris:
                    self._file_picker_active = False
                    self._processing_intent = False
                    Clock.schedule_once(lambda dt: self.hide_spinner(), 0)
                    return

                self.intent = None

                # Grant URI permission so processed images are accessible
                self.__grant_uri_permissions(uris)

                new_images = []
                images_lock = threading.Lock()

                def process_one(i, uri):
                    t0 = time.time()
                    try:
                        file_name, src_path = get_uri_name_and_path(uri)
                        if not file_name:
                            file_name = f"{int(time.time())}_{i}.png"
                        with self._unique_lock:
                            destination_path = self.unique(file_name)
                        t1 = time.time()
                        copy_uri_to_internal(destination_path, uri, src_path)
                        t2 = time.time()
                        create_thumbnail(destination_path, destination_dir=self.wallpapers_dir)
                        t3 = time.time()
                        with images_lock:
                            new_images.append(str(destination_path))
                        app_logger.info(
                            f"import_from_intent [{i+1}/{len(uris)}]: "
                            f"{os.path.basename(str(destination_path))} "
                            f"native={'yes' if src_path else 'no'} "
                            f"meta={t1-t0:.3f}s copy={t2-t1:.3f}s thumb={t3-t2:.3f}s"
                        )
                    except Exception as e:
                        app_logger.exception(f"import_from_intent: error importing {uri}: {e}")
                        traceback.print_exc()

                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda args: process_one(*args), enumerate(uris)))

                summary = f"import_from_intent: imported {len(new_images)}/{len(uris)} images"
                app_logger.info(summary)
                _add_wallpapers_to_config(new_images)
                self._processing_intent = False
                Clock.schedule_once(lambda dt: self.ui_things(dt), 0)
                Clock.schedule_once(lambda dt: self.app.bottom_bar.show(animation=False, hidden_by="pic"), 0)
            except Exception as e:
                self._file_picker_active = False
                self._processing_intent = False
                err = f"import_from_intent: error: {e}"
                app_logger.exception(err)
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.hide_spinner(), 0)

        threading.Thread(target=_run, daemon=True).start()

    def import_from_mediastore(self):
        """Query MediaStore for images accessible via limited permission.
        Used on API 35+ when READ_MEDIA_VISUAL_USER_SELECTED is granted
        but READ_MEDIA_IMAGES is not (system already showed its picker)."""
        if self._processing_intent:
            return
        self._processing_intent = True
        def _run():
            try:
                self._processing_start = time.time()
                app_logger.info(
                    f"import_from_mediastore: started processing choice at "
                    f"{_format_started_time(self._processing_start)}"
                )
                cursor = content_resolver.query(
                    ImagesMedia.EXTERNAL_CONTENT_URI, None, None, None, None
                )
                if cursor is None or cursor.getCount() == 0:
                    self._file_picker_active = False
                    self._processing_intent = False
                    Clock.schedule_once(lambda dt: self.hide_spinner(), 0)
                    return
                uris = []
                while cursor.moveToNext():
                    id_val = cursor.getLong(
                        cursor.getColumnIndexOrThrow(String("_id"))
                    )
                    item_uri = Uri.withAppendedPath(
                        ImagesMedia.EXTERNAL_CONTENT_URI,
                        String(str(id_val))
                    )
                    uris.append(item_uri)
                cursor.close()
                self.intent = None
                new_images = []
                images_lock = threading.Lock()
                def process_one(i, item_uri):
                    t0 = time.time()
                    try:
                        file_name, src_path = get_uri_name_and_path(item_uri)
                        if not file_name:
                            file_name = f"{int(time.time())}_{i}.png"
                        with self._unique_lock:
                            destination_path = self.unique(file_name)
                        t1 = time.time()
                        copy_uri_to_internal(destination_path, item_uri, src_path)
                        t2 = time.time()
                        create_thumbnail(
                            destination_path, destination_dir=self.wallpapers_dir
                        )
                        t3 = time.time()
                        with images_lock:
                            new_images.append(str(destination_path))
                        app_logger.info(
                            f"import_from_mediastore [{i+1}/{len(uris)}]: "
                            f"{os.path.basename(str(destination_path))} "
                            f"native={'yes' if src_path else 'no'} "
                            f"meta={t1-t0:.3f}s copy={t2-t1:.3f}s thumb={t3-t2:.3f}s"
                        )
                    except Exception as e:
                        app_logger.exception(
                            f"import_from_mediastore: error importing {item_uri}: {e}"
                        )
                        traceback.print_exc()
                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(
                        pool.map(
                            lambda args: process_one(*args), enumerate(uris)
                        )
                    )
                summary = (
                    f"import_from_mediastore: imported "
                    f"{len(new_images)}/{len(uris)} images"
                )
                app_logger.info(summary)
                _add_wallpapers_to_config(new_images)
                self._file_picker_active = False
                self._processing_intent = False
                Clock.schedule_once(lambda dt: self.ui_things(dt), 0)
                Clock.schedule_once(
                    lambda dt: self.app.bottom_bar.show(
                        animation=False, hidden_by="pic"
                    ),
                    0,
                )
            except Exception as e:
                self._file_picker_active = False
                self._processing_intent = False
                err = f"import_from_mediastore: error: {e}"
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
            activity.bind(on_new_intent=self.handle_image_sharing_from_others_app)

            # Handle initial intent when app starts
            self.handle_image_sharing_from_others_app(mActivity.getIntent())
        except Exception as error_setup_share_from_others_to_app_listener:
            print("error_setup_share_from_others_to_app_listener",error_setup_share_from_others_to_app_listener)
            traceback.print_exc()

    def _process_multiple_images(self, image_uris):
        try:
            new_images = []
            if image_uris and len(image_uris) > 0:
                for each_uri in image_uris:
                    file_name, src_path = get_uri_name_and_path(each_uri)
                    if not file_name:
                        file_name = f"{int(time.time())}.png"
                    file_path = self.unique(file_name)
                    new_images.append(str(file_path))
                    copy_uri_to_internal(file_path, each_uri, src_path)

            for img in new_images:
                my_config.add_wallpaper(img)


        except Exception as e:
            print("error_processing_images", e)

        finally:
            Clock.schedule_once(self.ui_things)

    def _process_single_image(self, uri):
        try:

            file_name, src_path = get_uri_name_and_path(uri)
            if not file_name:
                file_name = f"{int(time.time())}.png"
            file_path = self.unique(file_name)
            my_config.add_wallpaper(str(file_path))

            copy_uri_to_internal(file_path, uri, src_path)


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
        app_logger.exception(f"OSError creating thumbnail for: {src}")
    except Exception as error_making_thumbnail:
        print(f"Error creating thumbnail for: {error_making_thumbnail}", src)
        traceback.print_exc()
        return str(src)


def copy_image_to_internal(destination_name, uri):
    # MediaStore = autoclass("android.provider.MediaStore")
    # Environment = autoclass("android.os.Environment")
    # ContentUris = autoclass("android.content.ContentUris")
    # ImagesMedia = autoclass('android.provider.MediaStore$Images$Media')

    # def path_to_image_uri(path):
    #     cr = PythonActivity.mActivity.getContentResolver()
    #
    #     projection = ["_id"]
    #     selection = "_data=?"
    #     selection_args = [path]
    #
    #     cursor = cr.query(
    #         ImagesMedia.EXTERNAL_CONTENT_URI,
    #         projection,
    #         selection,
    #         selection_args,
    #         None
    #     )
    #
    #     if cursor and cursor.moveToFirst():
    #         image_id = cursor.getLong(0)
    #         cursor.close()
    #         return ContentUris.withAppendedId(
    #             ImagesMedia.EXTERNAL_CONTENT_URI,
    #             image_id
    #         )
    #
    #     if cursor:
    #         cursor.close()
    #
    #     return None


    if not uri:
        raise Exception("Image not found in MediaStore")

    internal_dir = mActivity.getFilesDir().getAbsolutePath()
    destination_path = os.path.join(internal_dir, destination_name)

    input_stream = BufferedInputStream(content_resolver.openInputStream(uri))
    try:
        if _try_java_native_copy(input_stream, destination_path):
            return destination_path
    finally:
        input_stream.close()

    # Fresh stream for the Python fallback (java copy may have consumed it).
    input_stream = BufferedInputStream(content_resolver.openInputStream(uri))
    try:
        output_stream = BufferedOutputStream(FileOutputStream(destination_path))
        try:
            buffer = bytearray(1024 * 64)
            while True:
                count = input_stream.read(buffer)
                if count == -1:
                    break
                output_stream.write(buffer, 0, count)
            output_stream.flush()
        finally:
            output_stream.close()
    finally:
        input_stream.close()

    current_time = time.time()
    os.utime(destination_path, (current_time, current_time))

    return destination_path


def _try_java_native_copy(input_stream, destination_path):
    """Copy the stream entirely inside Java (one JNI call) on API 29+.
    Returns True when the copy succeeded, False to fall back to Python."""
    output_stream = None
    try:
        if BuildVersion.SDK_INT < 29:
            return False
        output_stream = FileOutputStream(destination_path)
        FileUtils.copy(input_stream, output_stream)
        output_stream.close()
        output_stream = None
        current_time = time.time()
        os.utime(destination_path, (current_time, current_time))
        return True
    except Exception as e:
        app_logger.exception(f"Java native copy failed, falling back to streaming: {e}")
        if output_stream:
            try:
                output_stream.close()
            except Exception as e1:
                app_logger.exception(e1)
                pass
        return False


def get_uri_name_and_path(uri):
    """Query a content:// URI once and return (display_name, real_path).
    real_path is only set when the URI resolves to an existing local file,
    so callers can use a fast native copy."""
    name = None
    path = None
    try:
        scheme = uri.getScheme().lower() if hasattr(uri, "getScheme") else "content"
        if scheme == "file":
            p = uri.getPath()
            if p and os.path.exists(p):
                path = p
                name = os.path.basename(p)
            return name, path
        if scheme != "content":
            return name, path

        cursor = None
        try:
            cursor = content_resolver.query(
                uri, ["_data", OpenableColumns.DISPLAY_NAME], None, None, None
            )
            if cursor and cursor.moveToFirst():
                data_idx = cursor.getColumnIndex(String("_data"))
                if data_idx != -1:
                    p = cursor.getString(data_idx)
                    if p and os.path.exists(p):
                        path = p
                name_idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if name_idx != -1:
                    name = cursor.getString(name_idx)
        finally:
            if cursor:
                cursor.close()
    except Exception as e2:
        app_logger.exception(f"get_uri_name_and_path error: {e2}")
    return name, path


def copy_uri_to_internal(destination_path, uri, src_path=None):
    """Copy a URI's content to internal storage as fast as possible.
    Uses native shutil.copy2 when the URI resolves to a local file,
    falling back to a Java-native (or buffered) stream copy."""
    t0 = time.time()
    if src_path is None:
        _, src_path = get_uri_name_and_path(uri)
    if src_path:
        shutil.copy2(src_path, str(destination_path))
        current_time = time.time()
        os.utime(destination_path, (current_time, current_time))
        app_logger.info(
            f"copy_uri_to_internal: native copy {os.path.basename(str(destination_path))} "
            f"({time.time()-t0:.3f}s)"
        )
        return str(destination_path)
    result = copy_image_to_internal(destination_name=str(destination_path), uri=uri)
    app_logger.info(
        f"copy_uri_to_internal: stream copy {os.path.basename(str(destination_path))} "
        f"({time.time()-t0:.3f}s)"
    )
    return result


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

    if BuildVersion.SDK_INT >= 29:
        content_values.put(
            MediaColumns.RELATIVE_PATH,
            Environment.DIRECTORY_PICTURES + "/.waller"
        )

    uri = content_resolver.insert(ImagesMedia.EXTERNAL_CONTENT_URI, content_values)

    if uri:
        input_file = File(input_file_path)
        input_stream = FileInputStream(input_file)
        output_stream = content_resolver.openOutputStream(uri)

        buffer = bytearray(8192)
        while True:
            length = input_stream.read(buffer)
            if length <= 0:
                break
            output_stream.write(buffer, 0, length)

        input_stream.close()
        output_stream.close()

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


        file = File(image_absolute_path)

        uri = FileProvider.getUriForFile(
            mActivity,
            file_provider_authority,
            file
        )

        intent = Intent(Intent.ACTION_SEND)
        intent.setType("image/*")
        intent.putExtra(Intent.EXTRA_STREAM, cast('android.os.Parcelable', uri))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        # preview
        clip = ClipData.newUri(content_resolver, String("Image"), uri)
        intent.setClipData(clip)

        chooser = Intent.createChooser(intent, String("Share Image"))
        mActivity.startActivity(chooser)
        app_logger.info("Sharing image to other app")

    except Exception as error_from_trying_to_share_image_to_other_apps:
        print("error_from_trying_to_share_image_to_other_apps",error_from_trying_to_share_image_to_other_apps)
        traceback.print_exc()


def share_images_to_other_app(image_paths):
    if not on_android_platform():
        app_logger.warning("Can't share to Another App, Not on Android.")
        return None
    try:

        uris = ArrayList()
        for path in image_paths:
            file = File(path)
            uri = FileProvider.getUriForFile(
                mActivity,
                file_provider_authority,
                file
            )
            uris.add(uri)

        intent = Intent(Intent.ACTION_SEND_MULTIPLE)
        intent.setType("image/*")
        intent.putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        clip = ClipData.newUri(content_resolver, String("Image"), uris.get(0))
        intent.setClipData(clip)

        chooser = Intent.createChooser(intent, String("Share Images"))
        mActivity.startActivity(chooser)
        app_logger.info(f"Sharing {len(image_paths)} images to other app")

    except Exception as error_from_trying_to_share_images_to_other_apps:
        print("error_from_trying_to_share_images_to_other_apps", error_from_trying_to_share_images_to_other_apps)
        traceback.print_exc()


def get_file_name_from_uri(uri):
    try:

        cursor = content_resolver.query(uri, None, None, None, None)

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
    mime = content_resolver.getType(uri)
    return mime and mime.startswith("image/")