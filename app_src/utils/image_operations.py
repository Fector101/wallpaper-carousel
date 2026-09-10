from utils.boot_log import boot_log
import os, time
import shutil
import threading
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from kivy.clock import Clock
from kivymd.app import MDApp

from ui.widgets.layouts import LoadingLayout
from utils.helper import appFolder, format_size, crop_path_for

from utils.config_manager import ConfigManager
from utils.database import ImageDatabase
from utils.logger import app_logger
from utils.widget_intent import assign_picked_images_to_widget, clear_pending_widget_pick
from utils.platform_compat import on_android_platform as _on_android_platform, on_pydroid_app as _on_pydroid_app, LazyJavaClass as _LazyJavaClass

_mActivity = None
_mActivity_lock = threading.Lock()
_content_resolver = None
_content_resolver_lock = threading.Lock()

def _get_mActivity():
    global _mActivity
    with _mActivity_lock:
        if _mActivity is None:
            boot_log("image_operations: _get_mActivity start")
            PythonActivity = _LazyJavaClass("PythonActivity", "org.kivy.android.PythonActivity")
            _mActivity = PythonActivity.mActivity
            boot_log("image_operations: _get_mActivity done")
    return _mActivity

def _get_content_resolver():
    global _content_resolver
    with _content_resolver_lock:
        if _content_resolver is None:
            boot_log("image_operations: _get_content_resolver start")
            _content_resolver = _get_mActivity().getContentResolver()
            boot_log("image_operations: _get_content_resolver done")
    return _content_resolver

def _get_package_name():
    boot_log("image_operations: _get_package_name start")
    from android_notify.config import get_package_name
    result = get_package_name()
    boot_log("image_operations: _get_package_name done")
    return result

if _on_android_platform():
    String = _LazyJavaClass("String", "java.lang.String")
    Intent = _LazyJavaClass("Intent", "android.content.Intent")
    BuildVersion = _LazyJavaClass("BuildVersion", "android.os.Build$VERSION")
    Uri = _LazyJavaClass("Uri", "android.net.Uri")
    File = _LazyJavaClass("File", "java.io.File")
    BitmapFactory = _LazyJavaClass("BitmapFactory", "android.graphics.BitmapFactory")
    Bitmap = _LazyJavaClass("Bitmap", "android.graphics.Bitmap")
    BitmapConfig = _LazyJavaClass("BitmapConfig", "android.graphics.Bitmap$Config")
    CompressFormat = _LazyJavaClass("CompressFormat", "android.graphics.Bitmap$CompressFormat")
    FileOutputStream = _LazyJavaClass("FileOutputStream", "java.io.FileOutputStream")
    Math = _LazyJavaClass("Math", "java.lang.Math")
    ImagesMedia = _LazyJavaClass("ImagesMedia", "android.provider.MediaStore$Images$Media")
    BufferedInputStream = _LazyJavaClass("BufferedInputStream", "java.io.BufferedInputStream")
    BufferedOutputStream = _LazyJavaClass("BufferedOutputStream", "java.io.BufferedOutputStream")
    FileUtils = _LazyJavaClass("FileUtils", "android.os.FileUtils")
    Environment = _LazyJavaClass("Environment", "android.os.Environment")
    ContentValues = _LazyJavaClass("ContentValues", "android.content.ContentValues")
    FileInputStream = _LazyJavaClass("FileInputStream", "java.io.FileInputStream")
    MediaColumns = _LazyJavaClass("MediaColumns", "android.provider.MediaStore$MediaColumns")
    OpenableColumns = _LazyJavaClass("OpenableColumns", "android.provider.OpenableColumns")
    Options = _LazyJavaClass("Options", "android.graphics.BitmapFactory$Options")
    FileProvider = _LazyJavaClass("FileProvider", "androidx.core.content.FileProvider")
    ClipData = _LazyJavaClass("ClipData", "android.content.ClipData")
    ArrayList = _LazyJavaClass("ArrayList", "java.util.ArrayList")
    ContentUris = _LazyJavaClass("ContentUris", "android.content.ContentUris")

boot_log("image_operations: lazy classes created")

boot_log("image_operations: creating configmanager and dirs")

my_config = ConfigManager()
app_dir = Path(appFolder())

wallpapers_dir = app_dir / "wallpapers"
wallpapers_dir.mkdir(parents=True, exist_ok=True)

scaled_down_images_dir = app_dir / "scaled_down_images"
scaled_down_images_dir.mkdir(parents=True, exist_ok=True)

boot_log("image_operations: configmanager and dirs done")

_ANDROID_THUMBNAIL_LOCK = threading.Lock()
_SCALED_IMG_LOCK = threading.Lock()

def _format_started_time(timestamp):
    return time.strftime('%H:%M:%S', time.localtime(timestamp))

def _add_wallpapers_to_config(new_images):
    data = my_config.read()
    for img in new_images:
        if img not in data["wallpapers"]:
            data["wallpapers"].append(img)
    my_config.write(data)

def unique(destination_name):
    destination_path = wallpapers_dir / destination_name
    base, ext = os.path.splitext(destination_name)
    i = 1
    while destination_path.exists():
        destination_path = wallpapers_dir / f"{base}_{i}{ext}"
        i += 1
    return destination_path


class ImageOperation:
    def __init__(self,load_saved):
        boot_log("image_operations: ImageOperation.__init__")
        self.app = MDApp.get_running_app()
        self.load_saved = load_saved
        self.user_carousel_size = [0,0]
        self._picker_request_code = 65432
        self.showing_loading_screen = False # To fix when no image chosen from Half Popup
        self.processing_intent = False # True when import_images_from_android is running; guards against plyer duplicate
        self.file_picker_active = False # True while file picker is open; prevents on_resume from tearing down spinner
        self.spinner_layout = None
        self.intent = None
        self._processing_start = None # timestamp when import processing began
        self._unique_lock = threading.Lock()

    def launch_file_picker(self):
        """Launch Android file picker directly, bypassing plyer's slow URI resolution."""
        if not _on_android_platform():
            return
        from jnius import cast
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType(String("image/*"))
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, True)
        _get_mActivity().startActivityForResult(
            Intent.createChooser(intent, cast('java.lang.CharSequence', String("Select Images"))),
            self._picker_request_code
        )

    def import_images_from_plyer(self,files):
        print("files",files)
        if not files:
            self.file_picker_active = False
            self.processing_intent = False
            clear_pending_widget_pick(self.app)
            Clock.schedule_once(lambda dt: self.load_saved(has_files=False))
            self.hide_spinner()
            return
        self._processing_start = time.time()
        new_images = []
        images_lock = threading.Lock()
        copy_time = time.time()
        def process_one(_,src):
            t0 = time.time()
            with self._unique_lock:
                dst = unique(os.path.basename(src))
            try:
                shutil.copy2(src, dst)
                create_thumbnail(dst, destination_dir=wallpapers_dir)
                dest_path = scaled_down_path_for(dst)
                carousel_size = self.get_user_carousel_size()
                create_scaled_down_img(
                    src_path=dst,
                    dest_path=dest_path,
                    max_width=carousel_size[0],
                    max_height=carousel_size[1],
                )
                os.utime(dst, (copy_time, copy_time))
                with images_lock:
                    new_images.append(str(dst))
            except Exception as error_copying_files:
                app_logger.exception(f"import_images_from_plyer: error importing {src}: {error_copying_files}")
            pass
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda args: process_one(*args), enumerate(files)))
        _add_wallpapers_to_config(new_images)
        ImageDatabase().insert_images(new_images)
        assign_picked_images_to_widget(self.app, new_images)
        self.file_picker_active = False
        self.processing_intent = False
        Clock.schedule_once(self.ui_things, 0)
        Clock.schedule_once(lambda dt: self.app.bottom_bar.show(animation=False, hidden_by="pic"), 0)

    def get_user_carousel_size(self):
        from kivy.core.window import Window
        win_size = Window.size
        if self.user_carousel_size == [0,0]:
            self.user_carousel_size = [win_size[0], win_size[1]*0.8] # 80% of screen height
        return self.user_carousel_size
    def import_images_from_android(self, only_limited_access=False,image_uris=None):
        """Process URIs from a pending intent in parallel.
        Runs in a background thread; calls ui_things when done.
        ---
        Query MediaStore for images accessible via limited permission.
                Used on API 34+ when READ_MEDIA_VISUAL_USER_SELECTED is granted
                but READ_MEDIA_IMAGES is not (system already showed its picker)."""
        if self.processing_intent:
            return
        TAG = "mediaStore" if only_limited_access else "intent"
        self.processing_intent = True
        def _run(uris):
            try:
                self._processing_start = time.time()
                app_logger.info(f"import_from_{TAG}: started processing choice at: {_format_started_time(self._processing_start)}")
                if not uris:
                    if only_limited_access:
                        uris=get_selected_uris_from_cursor()
                    else:
                        uris = get_selected_uris_from_intent(intent=self.intent)
                    if not uris:
                        self._file_picker_active = False
                        self.processing_intent = False
                        clear_pending_widget_pick(self.app)
                        Clock.schedule_once(lambda dt: self.hide_spinner(), 0)
                        return

                    self.intent = None

                    if not only_limited_access:
                        # Grant URI permission so processed images are accessible
                        grant_uri_permissions(uris)

                new_images = []
                images_lock = threading.Lock()

                def process_one(i, uri):
                    t0 = time.time()
                    try:
                        file_name, src_path = get_uri_name_and_path(uri)
                        if not file_name:
                            file_name = f"{int(time.time())}_{i}.png"
                        with self._unique_lock:
                            destination_path = unique(file_name)
                        # ----- create copy and thumbnail -----
                        t1 = time.time()
                        copy_image_to_internal(destination_path=destination_path, uri=uri,src_path=src_path)
                        t2 = time.time()
                        create_thumbnail(src_path=destination_path, destination_dir=wallpapers_dir)
                        dest_path=scaled_down_path_for(destination_path)
                        carousel_size = self.get_user_carousel_size()
                        create_scaled_down_img(
                            src_path=destination_path,
                            dest_path=dest_path,
                            max_width=carousel_size[0],
                            max_height=carousel_size[1],
                        )
                        t3 = time.time()
                        print(f"image_operations: process_one [{i+1}/{len(uris)}] meta={t1-t0:.3f}s copy={t2-t1:.3f}s thumb={t3-t2:.3f}s")
                        with images_lock:
                            new_images.append(str(destination_path))
                        # app_logger.info(
                        #     f"import_images_from_android [{i+1}/{len(uris)}]: "
                        #     f"{os.path.basename(str(destination_path))} "
                        #     f"python={'yes' if src_path else 'no'} "
                        #     f"meta={t1-t0:.3f}s copy={t2-t1:.3f}s thumb={t3-t2:.3f}s"
                        # )
                    except Exception as error_importing_img:
                        app_logger.exception(f"import_from_{TAG}: error importing {uri}: {error_importing_img}")
                        traceback.print_exc()

                with ThreadPoolExecutor(max_workers=3) as pool:
                    list(pool.map(lambda args: process_one(*args), enumerate(uris)))

                app_logger.info(f"import_from_{TAG}: imported- {len(new_images)}/{len(uris)} images")
                _add_wallpapers_to_config(new_images)
                ImageDatabase().insert_images(new_images)
                assign_picked_images_to_widget(self.app, new_images)
                self._file_picker_active = False
                self.processing_intent = False
                Clock.schedule_once(lambda dt: self.ui_things(dt), 0)
                Clock.schedule_once(lambda dt: self.app.bottom_bar.show(animation=False, hidden_by="pic"), 0)
            except Exception as e:
                self.file_picker_active = False
                self.processing_intent = False
                app_logger.exception(f"import_from_{TAG}: error: {e}")
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.hide_spinner(), 0)

        threading.Thread(target=_run, args=([image_uris]),daemon=True).start()

    def ui_things(self, _):
        self.file_picker_active = False
        elapsed = None
        if self._processing_start is not None:
            elapsed = time.time() - self._processing_start
        when = time.strftime('%H:%M:%S')
        elapsed_str = f" ({elapsed:.2f}s after processing started)" if elapsed is not None else ""
        app_logger.info(f"ui_things: about to add widgets at {when}{elapsed_str}")
        self.load_saved()
        self.hide_spinner()
        self._processing_start = None

    def handle_image_sharing_from_others_app(self, intent):
        from jnius import cast
        tag="handle_image_sharing_from_others_app"
        if intent is None:
            app_logger.warning(f"{tag}- Intent is None")
            return False
        try:
            action = intent.getAction()
            type_ = intent.getType()

            if action == Intent.ACTION_SEND:
                uri = intent.getParcelableExtra(Intent.EXTRA_STREAM)
                if uri:
                    uri = cast("android.net.Uri", uri)
                else:
                    uri = intent.getData()
                if not uri or not is_image_uri(uri):
                    return False
                image_uris=[uri]
            elif action == Intent.ACTION_SEND_MULTIPLE:
                uris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM)
                image_uris = [u for u in uris if is_image_uri(u)]
            else:
                return False

            # Clear the intent so it doesn't get reprocessed
            try:
                intent.replaceExtras(None)
            except Exception as error_clearing_intent_extras:
                app_logger.exception(f"Error clearing intent extras: {error_clearing_intent_extras}")
                traceback.print_exc()

            self.hide_nav_btns()
            self.show_spinner()
            def start_thread(_):
                threading.Thread(target=self.import_images_from_android,args=(False,image_uris),daemon=True).start()
            Clock.schedule_once(start_thread, 0)
            return True

        except Exception as error_handle_image_sharing_from_others_app:
            print(f"error_{tag}",error_handle_image_sharing_from_others_app)
            traceback.print_exc()
            return False

    def hide_nav_btns(self):
        def ui_thing(*_):
            self.app.bottom_bar.hide(animation=False, hidden_by="pic")
        Clock.schedule_once(ui_thing)

    def show_spinner(self):
        def ui(_):
            self.spinner_layout = LoadingLayout()
            self.showing_loading_screen = True
        Clock.schedule_once(ui)

    def hide_spinner(self):
        """
        Don't Call self.__copy_add removes spinner, This method is for a specific edge case
        Fix for Half Screen File Chooser filechooser.open_file not calling on_selection"""
        def task(_):
            self.spinner_layout.remove()
            self.showing_loading_screen = False
        if self.showing_loading_screen:
            Clock.schedule_once(task)

    def has_pending_intent(self):
        return self.intent is not None


def grant_uri_permissions(uris):
    for _uri in uris:
        try:
            _get_mActivity().grantUriPermission(
                _get_package_name(), _uri,
                Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
        except Exception as error_grant_uri_permissions:
            app_logger.exception(error_grant_uri_permissions)

def get_uri_name_and_path(uri):
    """Query a content:// URI once and return (display_name, real_path).
    real_path is only set when the URI resolves to an existing local file,
    so callers can use a fast native copy."""
    t0 = time.time()
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
            cursor = _get_content_resolver().query(
                uri, ["_data", OpenableColumns.DISPLAY_NAME], None, None, None
            )
            if cursor and cursor.moveToFirst():
                # path
                data_idx = cursor.getColumnIndex(String("_data"))
                if data_idx != -1:
                    p = cursor.getString(data_idx)
                    if p and os.path.exists(p):
                        path = p
                        print(f"path: {path}")
                # name
                name_idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if name_idx != -1:
                    name = cursor.getString(name_idx)
        finally:
            if cursor:
                cursor.close()
    except Exception as e2:
        app_logger.exception(f"get_uri_name_and_path error: {e2}")
    return name, path

def get_selected_uris_from_intent(intent):
    uris = []
    if not intent:
        return uris

    clip = intent.getClipData()
    if clip:
        count = clip.getItemCount()
        for i in range(count):
            uri = clip.getItemAt(i).getUri()
            if uri:
                uris.append(uri)
        return uris

    uri = intent.getData()
    if uri:
        uris.append(uri)
    else:
        pass

    # if uris:
    #     return uris
    
    # Shared-image intents can carry streams rather than data/ClipData.  Use
    # the literal action key so this parser remains usable in desktop tests
    # without forcing Android classes to be initialized.
    # stream_key = "android.intent.extra.STREAM"
    # stream_list = intent.getParcelableArrayListExtra(stream_key)
    # if stream_list:
    #     return [uri for uri in stream_list if uri]

    # stream = intent.getParcelableExtra(stream_key)
    # if stream:
    #     return [stream]

    # stream_array = intent.getParcelableArrayExtra(stream_key)
    # if stream_array:
    #     return [uri for uri in stream_array if uri]

    return uris

def get_selected_uris_from_cursor():
    collection = ImagesMedia.EXTERNAL_CONTENT_URI
    cursor = _get_content_resolver().query(
        collection, None, None, None, None
    )
    if cursor is None or cursor.getCount() == 0:
        return []

    uris = []
    id_column = cursor.getColumnIndexOrThrow(ImagesMedia._ID)
    while cursor.moveToNext():
        id_val = cursor.getLong(id_column)
        item_uri = Uri.withAppendedPath(
            ImagesMedia.EXTERNAL_CONTENT_URI,
            String(str(id_val))
        )
        uris.append(item_uri)
    cursor.close()
    return uris

def copy_image_to_internal(destination_path, uri, src_path=None):
    """Copy a URI's content to internal storage as fast as possible.
    Uses native shutil.copy2 when the URI resolves to a local file,
    falling back to a Java-native (or buffered) stream copy."""
    t0 = time.time()
    try:
        if src_path is None:
            _, src_path = get_uri_name_and_path(uri)
        if src_path:
            # works for half screen picker
            shutil.copy2(src_path, str(destination_path))
            current_time = time.time()
            os.utime(destination_path, (current_time, current_time))
            app_logger.info(
                f"[copy_image_to_internal: python] copy {os.path.basename(str(destination_path))} "
                f"({time.time() - t0:.3f}s)"
            )
            return str(destination_path)
    except PermissionError as error_copying_using_python:
        # Fails when using android picker to choose a file from gallery app
        #  PermissionError: [Errno 13] Permission denied: '/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images/IMG-20260803-WA0016.jpg'
        print(f"permission error_copying_using_python: {error_copying_using_python}")
    except Exception as error_copying_using_python:
        print(f"error_copying_using_python: {error_copying_using_python}")


    result = copy_uri_to_internal(destination_name=str(destination_path), uri=uri)
    app_logger.info(
        f"[copy_image_to_internal: stream] copy {os.path.basename(str(destination_path))} "
        f"({time.time() - t0:.3f}s)"
    )
    return result

def create_thumbnail(src_path, destination_dir=None, size=(320, 320), quality=60):
    """Create a low-resolution JPEG thumbnail for src and return its path.
    If Pillow is not available or creation fails, returns the original path string.
    """
    # _thumb_t0 = time.time()
    # print(f"image_operations: create_thumbnail start {os.path.basename(str(src_path))}")
    def use_android_classes_to_create_thumbnail(src_path_, destination_path):
        _t = time.time()
        max_width = size[0]
        max_height = size[1]

        # 1. Load image
        bitmap = BitmapFactory.decodeFile(src_path_)
        if bitmap is None:
            raise Exception("Failed to decode image")
        print(f"  [thumb] decodeFile {time.time()-_t:.3f}s") # 0.590s

        _t2 = time.time()
        # 2. Convert to RGB (ARGB_8888 ≈ RGB)
        bitmap = bitmap.copy(BitmapConfig.ARGB_8888, False)
        print(f"  [thumb] bitmap.copy {time.time()-_t2:.3f}s")#0.065s

        # 3. Compute thumbnail size (keep aspect ratio)
        _t2 = time.time()
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
        print(f"  [thumb] createScaledBitmap {time.time()-_t2:.3f}s")#0.568s

        # 4. Save as JPEG
        _t2 = time.time()
        out = FileOutputStream(destination_path)
        resized.compress(CompressFormat.JPEG, quality, out)
        out.close()
        print(f"  [thumb] compress+write {time.time()-_t2:.3f}s")#0.099s

        # Cleanup
        bitmap.recycle()
        resized.recycle()
        print(f"  [thumb] android total {time.time()-_t:.3f}s")#1.331s

    if str(src_path).endswith(".webp"):
        return str(src_path)

    try:
        from PIL import Image
    except ImportError:
        Image=None
        if not _on_android_platform():
            print("Pillow not available, cannot create thumbnail.")
            # Pillow not available and not on android -> fall back to original image path
            return str(src_path)

    try:
        src_path = Path(src_path)
        # _thumb_t1 = time.time()
        destination = thumbnail_path_for(src_path, destination_dir)
        # print(f"  [thumb] thumbnail_path_for {time.time()-_thumb_t1:.3f}s")
        # If thumbnail already exists and is newer than source, reuse it
        if destination.exists() and destination.stat().st_mtime >= src_path.stat().st_mtime:
            # print(f"  [thumb] reused existing thumbnail in {time.time()-_thumb_t0:.3f}s")
            return str(destination)

        if Image:
            # _thumb_t2 = time.time()
            with Image.open(src_path) as im:
                im = im.convert('RGB')
                # print(f"  [thumb] PIL open+convert {time.time()-_thumb_t2:.3f}s")
                # _thumb_t3 = time.time()
                im.thumbnail(size, Image.LANCZOS)
                # print(f"  [thumb] PIL thumbnail {time.time()-_thumb_t3:.3f}s")
                # _thumb_t4 = time.time()
                im.save(destination, format='JPEG', quality=quality)
                # print(f"  [thumb] PIL save {time.time()-_thumb_t4:.3f}s")
            # print(f"  [thumb] pillow total {time.time()-_thumb_t2:.3f}s")
        elif _on_android_platform():
            # BitmapFactory/decodeFile + the JNI round-trips below are not safe to
            # run from multiple threads at once: concurrent first-use class
            # resolution made decodeFile return another thread's image, so
            # thumbnails ended up as copies of a different wallpaper. Serialize it.
            # _thumb_t2 = time.time()
            with _ANDROID_THUMBNAIL_LOCK:
                # print(f"  [thumb] lock wait {time.time()-_thumb_t2:.3f}s")
                try:
                    use_android_classes_to_create_thumbnail(str(src_path), str(destination))
                except Exception as error_using_android_classes_to_create_thumbnail:
                    print("error_using_android_classes_to_create_thumbnail",error_using_android_classes_to_create_thumbnail)
                    traceback.print_exc()
        # print(f"  [thumb] create_thumbnail done in {time.time()-_thumb_t0:.3f}s")
        return str(destination) # TODO: Stop Returning caller already knows path format, well aspect there is an error then the format is the original path
    except OSError as os_error:
        app_logger.exception(f"OSError creating thumbnail for: {src_path}, os_error:{os_error}")
        return str(src_path)
    except Exception as error_making_thumbnail:
        print(f"Error creating thumbnail for: {error_making_thumbnail} src_path:{src_path}")
        traceback.print_exc()
        return str(src_path)

def create_scaled_down_img(src_path, dest_path, max_width, max_height, quality=75):
    """Resize an image to fit within max_width x max_height using Android Java classes."""

    if max_width <= 0 or max_height <= 0:
        raise ValueError("Image dimensions must be positive")

    if os.path.exists(dest_path):
        return str(dest_path)
    def create_scaled_down_img_android(src_path=src_path, dest_path=dest_path, max_width=max_width, max_height=max_height, quality=quality):
        from jnius import autoclass

        BitmapFactory = autoclass('android.graphics.BitmapFactory')
        BitmapFactoryOptions = autoclass('android.graphics.BitmapFactory$Options')
        Bitmap = autoclass('android.graphics.Bitmap')
        BitmapConfig = autoclass('android.graphics.Bitmap$Config')
        CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
        FileOutputStream = autoclass('java.io.FileOutputStream')
        Math = autoclass('java.lang.Math')
        src_path=str(src_path)
        dest_path=str(dest_path)
        opts = BitmapFactoryOptions()
        opts.inJustDecodeBounds = True
        BitmapFactory.decodeFile(src_path, opts)

        opts.inSampleSize = _compute_in_sample_size(
            max_width, max_height, opts.outWidth, opts.outHeight
        )
        opts.inJustDecodeBounds = False
        bitmap = BitmapFactory.decodeFile(src_path, opts)
        if bitmap is None:
            raise Exception(f"Failed to decode image: {src_path}")

        bitmap = bitmap.copy(BitmapConfig.ARGB_8888, False)

        width = bitmap.getWidth()
        height = bitmap.getHeight()

        scale = min(1.0, min(max_width / float(width), max_height / float(height)))
        new_w = Math.round(width * scale)
        new_h = Math.round(height * scale)

        resized = Bitmap.createScaledBitmap(bitmap, new_w, new_h, True)

        out = FileOutputStream(dest_path)
        resized.compress(CompressFormat.JPEG, quality, out)
        out.close()

        print(f"src_path: {format_size(os.path.getsize(src_path))}")
        print(f"dest_path: {format_size(os.path.getsize(dest_path))}")

        bitmap.recycle()
        resized.recycle()
        return None

    def create_scaled_down_img_PIL():
        try:
            from PIL import Image
        except Exception as error_getting_pil:
            print("error_getting_pil", error_getting_pil)
            return src_path

        img = Image.open(src_path)
        img_width, img_height = img.size

        # 1. Start with a scale factor of 1.0 (100% size)
        scale_factor = 1.0

        # 2. If it's too wide, calculate width scale factor
        if img_width > max_width:
            scale_factor = max_width / img_width

        # 3. If it's STILL too tall after width scaling, shrink it further to fit height
        if (img_height * scale_factor) > max_height:
            scale_factor = max_height / img_height

        # 4. Apply the final scale factor uniformly to both sides
        new_width = int(img_width * scale_factor)
        new_height = int(img_height * scale_factor)

        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        resized_img.save(dest_path)
        print(f"OG : {format_size(os.path.getsize(src_path))}")
        print(f"pil scaled image : {format_size(os.path.getsize(dest_path))}")
        return None

    if str(src_path).endswith(".webp"):
        return str(src_path)

    try:
        from PIL import Image
    except ImportError:
        Image=None
        if not _on_android_platform():
            print("Pillow not available, cannot create scaled down image.")
            # Pillow not available and not on android -> fall back to original image path
            return str(src_path)

    try:
        if Image:
            create_scaled_down_img_PIL()
        elif _on_android_platform():
            with _SCALED_IMG_LOCK:
                try:
                    create_scaled_down_img_android()
                except Exception as error_using_android_classes_to_create_scaled_down_image:
                    print("error_using_android_classes_to_create_scaled_down_image",
                          error_using_android_classes_to_create_scaled_down_image)
                    traceback.print_exc()
                    try:
                        os.remove(dest_path)
                    except FileNotFoundError:
                        pass
                    return str(src_path)
    except OSError as os_error:
        app_logger.exception(f"OSError creating scaled down image for: {src_path}, os_error:{os_error}")
        return str(src_path)
    except Exception as error_making_scaled_down_img:
        print(f"Error creating scaled down image for: {error_making_scaled_down_img} src_path:{src_path}")
        traceback.print_exc()
        return str(src_path)

    return str(dest_path)

def copy_uri_to_internal(destination_name, uri):
    if not uri:
        raise Exception("Image not found in MediaStore")

    internal_dir = _get_mActivity().getFilesDir().getAbsolutePath()
    destination_path = os.path.join(internal_dir, destination_name)

    input_stream = BufferedInputStream(_get_content_resolver().openInputStream(uri))
    try:
        if _try_java_native_copy(input_stream, destination_path):
            return destination_path
    finally:
        input_stream.close()

    # Fresh stream for the Python fallback (java copy may have consumed it).
    input_stream = BufferedInputStream(_get_content_resolver().openInputStream(uri))
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

def scaled_down_path_for(src):
    """Return the cached scaled-down Path for a source image.

    Scaled-down images live in a 'scaled_down_images' subfolder under the source
    folder. The output name is derived from the full source filename
    (``<stem>_<ext>.jpg``, e.g. ``foo.png`` -> ``foo_png.jpg``) so distinct
    sources sharing a stem never collide on one cached file.
    """
    p = Path(src)
    destination_dir = p.parent
    scaled_down_dir = destination_dir / "scaled_down_images"
    scaled_down_dir.mkdir(parents=True, exist_ok=True)
    return scaled_down_dir / f"{p.stem}_{p.suffix.lstrip('.') or 'img'}.jpg"

def compute_preview_crop(win_size, image_widget_size, texture_size, scale, pos):
    """Compute the visible region of a preview image as a crop box and its
    normalized viewport.

    The preview scatter shows a cover-fitted image the size of
    ``image_widget_size`` scaled by ``scale`` and translated by ``pos`` inside a
    window of ``win_size`` (all in Kivy widget/pixel coordinates). Returns a
    ``(box, viewport)`` tuple where ``box`` is ``(left, upper, right, lower)``
    in the source texture's pixel coordinates (ready for Pillow crop) and
    ``viewport`` is ``{"scale": ..., "cx": ..., "cy": ...}`` describing the
    on-screen viewport center normalized to the image widget. Returns ``None``
    when no region is visible (degenerate layout).
    """
    win_w, win_h = win_size
    img_w, img_h = image_widget_size
    tex_w, tex_h = texture_size
    x, y = pos
    if (
        min(win_w, win_h, img_w, img_h, tex_w, tex_h, scale) <= 0
        or win_w > img_w * scale
        or win_h > img_h * scale
    ):
        return None

    x0 = (0 - x) / scale
    x1 = (win_w - x) / scale
    y0 = (0 - y) / scale
    y1 = (win_h - y) / scale

    left_local = max(x0, 0)
    right_local = min(x1, img_w)
    bottom_local = max(y0, 0)
    top_local = min(y1, img_h)

    if left_local >= right_local or bottom_local >= top_local:
        return None

    left = int(round(left_local / img_w * tex_w))
    right = int(round(right_local / img_w * tex_w))
    upper = int(round((img_h - top_local) / img_h * tex_h))
    lower = int(round((img_h - bottom_local) / img_h * tex_h))

    left = max(left, 0)
    right = min(right, tex_w)
    upper = max(upper, 0)
    lower = min(lower, tex_h)
    if left >= right or upper >= lower:
        return None

    viewport = {
        "scale": scale,
        "cx": ((left_local + right_local) / 2) / img_w,
        "cy": ((bottom_local + top_local) / 2) / img_h,
    }
    return (left, upper, right, lower), viewport

def crop_and_save_region(src, box, quality=88):
    """Crop ``src`` to ``box`` and store it as the user-selected wallpaper.

    ``box`` is ``(left, upper, right, lower)`` in the source texture's pixel
    coordinates. The cropped image is saved at :func:`utils.helper.crop_path_for`
    so any future wallpaper set for ``src`` uses this tuned version. Returns the
    crop path.
    """
    import os
    src = str(src)
    left, upper, right, lower = tuple(int(v) for v in box)
    if right - left <= 0 or lower - upper <= 0:
        raise ValueError("Crop box must have positive width and height")

    dest_path = str(crop_path_for(src))

    def create_cropped_img_android():
        from jnius import autoclass
        BitmapFactoryAndroid = autoclass('android.graphics.BitmapFactory')
        Bitmap = autoclass('android.graphics.Bitmap')
        CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
        FileOutputStream = autoclass('java.io.FileOutputStream')
        bitmap = BitmapFactoryAndroid.decodeFile(src)
        if bitmap is None:
            raise Exception(f"Failed to decode image: {src}")
        cropped = Bitmap.createBitmap(bitmap, left, upper, right - left, lower - upper)
        out = FileOutputStream(dest_path)
        cropped.compress(CompressFormat.JPEG, quality, out)
        out.close()
        bitmap.recycle()
        cropped.recycle()

    try:
        from PIL import Image
        with Image.open(src) as img:
            cropped_img = img.crop((left, upper, right, lower))
            cropped_img.save(dest_path, quality=quality)
    except Exception as error_cropping_with_pil:
        print(f"error_cropping_with_pil: {error_cropping_with_pil}")
        traceback.print_exc()
        if not _on_android_platform():
            raise
        try:
            os.remove(dest_path)
        except FileNotFoundError:
            pass
        create_cropped_img_android()

    return dest_path

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

def is_image_uri(uri):
    mime = _get_content_resolver().getType(uri)
    return mime and mime.startswith("image/")

def get_or_create_thumbnail(src, destination_dir=None, size=(320, 320)):
    """Convenience wrapper to obtain a thumbnail path, creating it if necessary."""
    return create_thumbnail(src, destination_dir=destination_dir, size=size)

def get_or_create_scaled_down_image(src, size):
    """Convenience wrapper to obtain a thumbnail path, creating it if necessary."""
    destination_path = scaled_down_path_for(src)
    if not size:
        from kivy.core.window import Window
        running_app = MDApp.get_running_app()
        screen_manager = running_app.sm
        fullscreen = screen_manager.fullscreen
        carousel = fullscreen.carousel
        carousel_height = carousel.size[1]
        win_w, _ = Window.size
        size = (win_w, carousel_height)

    try:
        return create_scaled_down_img(
            src_path=src,
            dest_path=destination_path,
            max_width=size[0],
            max_height=size[1]
        )
    except ValueError:
        return str(src)

def _default_scaled_down_size():
    """Resolve the typical carousel display size for scaled-down wallpapers.

    Matches ``ImageOperation.get_user_carousel_size``: window width x 80% of
    window height, so it works without a fully built UI graph. Falls back to a
    landscape phone-ish size when the window isn't available.
    """
    try:
        from kivy.core.window import Window
        win_size = Window.size
        return (int(win_size[0]), int(win_size[1] * 0.8))
    except Exception:
        pass
    return (1080, 2300)

def backfill_scaled_down_images(size=None):
    """Generate missing scaled-down cache images for all configured wallpapers.

    Old installs predate the scaled-down image cache, so nothing is cached on
    first launch after the upgrade. Iterate every configured wallpaper and
    create its scaled-down file when missing. Meant to run on a background
    thread at startup; on-demand callers short-circuit once the file exists.
    """
    if not size:
        size = _default_scaled_down_size()
    wallpapers = set(my_config.get_wallpapers())
    wallpapers.update(my_config.get_day_wallpapers())
    wallpapers.update(my_config.get_noon_wallpapers())
    for src in sorted(wallpapers):
        try:
            if not os.path.exists(str(src)):
                continue
            dest_path = scaled_down_path_for(src)
            if dest_path.exists():
                continue
            create_scaled_down_img(
                src_path=str(src),
                dest_path=dest_path,
                max_width=size[0],
                max_height=size[1],
            )
        except Exception as error_backfilling_scaled_image:
            app_logger.exception(
                f"backfill_scaled_down_images failed for {src}: {error_backfilling_scaled_image}"
            )

def get_image_info(path):
    info_dict = {
                "Pixels": "Nil",
                "Megapixels": "Nil",
                "Size": "Nil",
                "MIME": "Nil",
                "long_date": "Nil", # Monday, 12th Oct 2026
                "time": "Nil", # 12:30PM
            }

    # Check if file exists
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

    from datetime import datetime
    ctime_timestamp = os.path.getctime(path)
    creation_date = datetime.fromtimestamp(ctime_timestamp)
    # Separate into two format strings
    info_dict["long_date"] = creation_date.strftime("%A, %d %B %Y")  # August 25, 2026
    info_dict["time"] = creation_date.strftime("%I:%M %p")  # 12:06 PM

    if not _on_android_platform():
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
    if not _on_android_platform():
        app_logger.warning("Can't share to Another App, Not on Android.")
        return None
    try:
        from jnius import cast


        file = File(image_absolute_path)

        uri = FileProvider.getUriForFile(
            _get_mActivity(),
            _get_package_name() + ".fileprovider",
            file
        )

        intent = Intent(Intent.ACTION_SEND)
        intent.setType(String("image/*"))
        intent.putExtra(Intent.EXTRA_STREAM, cast('android.os.Parcelable', uri))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        # preview
        clip = ClipData.newUri(_get_content_resolver(), String("Image"), uri)
        intent.setClipData(clip)

        chooser = Intent.createChooser(intent, String("Share Image"))
        _get_mActivity().startActivity(chooser)
        app_logger.info("Sharing image to other app")

    except Exception as error_from_trying_to_share_image_to_other_apps:
        print("error_from_trying_to_share_image_to_other_apps",error_from_trying_to_share_image_to_other_apps)
        traceback.print_exc()

def share_images_to_other_app(image_paths):
    if not _on_android_platform():
        app_logger.warning("Can't share to Another App, Not on Android.")
        return None
    try:

        uris = ArrayList()
        for path in image_paths:
            file = File(path)
            uri = FileProvider.getUriForFile(
                _get_mActivity(),
                _get_package_name() + ".fileprovider",
                file
            )
            uris.add(uri)

        intent = Intent(Intent.ACTION_SEND_MULTIPLE)
        intent.setType(String("image/*"))
        intent.putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)

        clip = ClipData.newUri(_get_content_resolver(), String("Image"), uris.get(0))
        intent.setClipData(clip)

        chooser = Intent.createChooser(intent, String("Share Images"))
        _get_mActivity().startActivity(chooser)
        app_logger.info(f"Sharing {len(image_paths)} images to other app")

    except Exception as error_from_trying_to_share_images_to_other_apps:
        print("error_from_trying_to_share_images_to_other_apps", error_from_trying_to_share_images_to_other_apps)
        traceback.print_exc()

def _compute_in_sample_size(req_width, req_height, src_width, src_height):
    in_sample_size = 1
    if src_height > req_height or src_width > req_width:
        half_height = src_height // 2
        half_width = src_width // 2
        while (half_height // in_sample_size) >= req_height and \
                (half_width // in_sample_size) >= req_width:
            in_sample_size *= 2
    return in_sample_size




boot_log("image_operations: module imported")
