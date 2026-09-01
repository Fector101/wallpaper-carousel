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
from utils.helper import appFolder

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

boot_log("image_operations: configmanager and dirs done")

_ANDROID_THUMBNAIL_LOCK = threading.Lock()

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
        # _t = time.time()
        max_width = size[0]
        max_height = size[1]

        # 1. Load image
        bitmap = BitmapFactory.decodeFile(src_path_)
        if bitmap is None:
            raise Exception("Failed to decode image")
        # print(f"  [thumb] decodeFile {time.time()-_t:.3f}s")

        # _t2 = time.time()
        # 2. Convert to RGB (ARGB_8888 ≈ RGB)
        bitmap = bitmap.copy(BitmapConfig.ARGB_8888, False)
        # print(f"  [thumb] bitmap.copy {time.time()-_t2:.3f}s")

        # 3. Compute thumbnail size (keep aspect ratio)
        # _t2 = time.time()
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
        # print(f"  [thumb] createScaledBitmap {time.time()-_t2:.3f}s")

        # 4. Save as JPEG
        # _t2 = time.time()
        out = FileOutputStream(destination_path)
        resized.compress(CompressFormat.JPEG, quality, out)
        out.close()
        # print(f"  [thumb] compress+write {time.time()-_t2:.3f}s")

        # Cleanup
        bitmap.recycle()
        resized.recycle()
        # print(f"  [thumb] android total {time.time()-_t:.3f}s")

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
        return str(destination)
    except OSError as os_error:
        app_logger.exception(f"OSError creating thumbnail for: {src_path}, os_error:{os_error}")
    except Exception as error_making_thumbnail:
        print(f"Error creating thumbnail for: {error_making_thumbnail} src_path:{src_path}")
        traceback.print_exc()
        return str(src_path)

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


boot_log("image_operations: module imported")
