import os, time
import shutil
import threading
import traceback
from pathlib import Path

from android_notify.internal.java_classes import String, autoclass, cast, Intent
from kivy.clock import Clock
from android_notify.config import on_android_platform, get_python_activity_context

from ui.widgets.layouts import LoadingLayout
from utils.helper import appFolder
from utils.config_manager import ConfigManager
from utils.logger import app_logger

my_config = ConfigManager()

class ImageOperation:
    def __init__(self,load_saved):
        self.showing_loading_screen = False # To fix when no image chosen from Half Popup
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
        # print('entered',files)

        if not files:
            Clock.schedule_once(lambda dt: self.load_saved(has_files=False))# for showing bottom nav
            self.hide_spinner()
            return
        new_images = []
        try:
            uris=self.get_selected_uris()
        except Exception as error_getting_uris:
            print(f"Error getting uris: {error_getting_uris}")
            uris=[]
        if not uris:
            print("gotten files:",files,uris)

        self.intent = None
        copy_time = time.time()  # Get current timestamp once for consistency

        for i, src in enumerate(files):
            # print(i,src,'i and src')
            if not os.path.exists(src):
                continue
            destination_path = self.unique(os.path.basename(src))
            try:
                shutil.copy2(src, destination_path)
                # Set the modification time to current time
                os.utime(destination_path, (copy_time, copy_time))
            except PermissionError:
                try:
                    if i < len(uris):
                        copy_image_to_internal(destination_path,uris[i])
                    else:
                        continue
                except Exception as error_using_java_copy:
                    print("error_using_java_copy: ", error_using_java_copy)
                    traceback.print_exc()
            except Exception as e:
                print(f"Error copying file '{src}' to '{destination_path}', Error: {e}")
                traceback.print_exc()
                continue
            # generate low-res thumbnail for preview
            try:
                create_thumbnail(destination_path, destination_dir=self.wallpapers_dir)
            except Exception as error_creating_thumbnail:
                print("Error creating thumbnail for:", error_creating_thumbnail,"destination_path: ", destination_path)
                traceback.print_exc()

            new_images.append(str(destination_path))
        for img in new_images:
            my_config.add_wallpaper(img)

        Clock.schedule_once(self.ui_things, 0)

    def copy_add(self, files):
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
        self.load_saved()
        self.hide_spinner()

    def get_selected_uris(self):
        uris = []
        # print('must be after chooser callback',self.intent,'i',self.i)
        if not self.intent:
            print("No intent",self.intent)
        #     time.sleep(3)
        # print('self.intent',self.intent)
        if not self.intent:
            return uris

        clip = self.intent.getClipData()
        if clip:
            for i in range(clip.getItemCount()):
                uri = clip.getItemAt(i).getUri()
                if uri:
                    uris.append(uri)
            return uris

        uri = self.intent.getData()
        if uri:
            uris.append(uri)

        return uris

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
                    self.show_spinner()
                    def start_thread(_):
                        threading.Thread(target=self._process_single_image,args=(uri,),daemon=True).start()
                    Clock.schedule_once(start_thread, 0)


            elif action == Intent.ACTION_SEND_MULTIPLE:
                uris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM)
                image_uris = [u for u in uris if is_image_uri(u)]
                if image_uris:
                    self.show_spinner()
                    def start_thread(_):
                        threading.Thread(target=self._process_multiple_images,args=(image_uris,),daemon=True).start()
                    Clock.schedule_once(start_thread, 0)

            else:
                app_logger.warning(f"Didn't recognize intent action: {action}, type:{type_}")

            # print(f"{tag} -end {len(os.listdir(self.wallpapers_dir))}")

        except Exception as error_handle_image_sharing_from_others_app:
            print(f"error_{tag}",error_handle_image_sharing_from_others_app)


    def setup_share_from_others_to_app_listener(self):
        if not on_android_platform():
            app_logger.warning("Can't Share Image to App, You're not on Android")
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

    except Exception as error_making_thumbnail:
        print(f"Error creating thumbnail for: {error_making_thumbnail}", src)
        traceback.print_exc()
        return str(src)


def copy_image_to_internal(destination_name, uri):
    import os
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
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

    FileOutputStream = autoclass("java.io.FileOutputStream")
    BufferedInputStream = autoclass("java.io.BufferedInputStream")
    BufferedOutputStream = autoclass("java.io.BufferedOutputStream")

    activity = PythonActivity.mActivity
    cr = activity.getContentResolver()

    # uri = path_to_image_uri(image_path)

    if not uri:
        raise Exception("Image not found in MediaStore")

    input_stream = BufferedInputStream(cr.openInputStream(uri))

    internal_dir = activity.getFilesDir().getAbsolutePath()
    destination_path = os.path.join(internal_dir, destination_name)

    output_stream = BufferedOutputStream(
        FileOutputStream(destination_path)
    )

    buffer = bytearray(1024 * 8)
    while True:
        count = input_stream.read(buffer)
        if count == -1:
            break
        output_stream.write(buffer, 0, count)

    output_stream.flush()
    input_stream.close()
    output_stream.close()

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
        intent.setType("*/*")
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