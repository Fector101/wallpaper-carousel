import os
import shutil
import traceback
from pathlib import Path

from android_notify.config import on_android_platform
from utils.helper import appFolder
from utils.config_manager import ConfigManager


class ImageOperation:
    def __init__(self,update_thumbnails_function):
        self.app_dir = Path(appFolder())
        self.myconfig = ConfigManager()
        self.intent = None
        self.wallpapers_dir = self.app_dir / "wallpapers"
        try:
            self.wallpapers_dir.mkdir(parents=True, exist_ok=True)
            (self.wallpapers_dir / "thumbs").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating wallpapers directory: {e}")

        self.update_thumbnails_function = update_thumbnails_function

    def copy_add(self, files):
        if not files:
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

        for i, src in enumerate(files):
            # print(i,src,'i and src')
            if not os.path.exists(src):
                continue
            dest = self.unique(os.path.basename(src))
            try:
                shutil.copy2(src, dest)
            except PermissionError:
                try:
                    if i < len(uris):
                        copy_image_to_internal(dest,uris[i])
                    else:
                        continue
                except Exception as error_using_java_copy:
                    print("error_using_java_copy: ", error_using_java_copy)
                    traceback.print_exc()
            except Exception as e:
                print(f"Error copying file '{src}' to '{dest}': {e}")
                traceback.print_exc()
                continue
            # generate low-res thumbnail for preview
            try:
                create_thumbnail(dest, dest_dir=self.wallpapers_dir)
            except Exception as error_creating_thumbnail:
                print("Error creating thumbnail for:", error_creating_thumbnail,"dest: ", dest)
                traceback.print_exc()

            new_images.append(str(dest))
        for img in new_images:
            self.myconfig.add_wallpaper(img)
        self.update_thumbnails_function(new_images)

    def unique(self, dest_name):
        dest = self.wallpapers_dir / dest_name
        base, ext = os.path.splitext(dest_name)
        i = 1
        while dest.exists():
            dest = self.wallpapers_dir / f"{base}_{i}{ext}"
            i += 1
        return dest

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


def create_thumbnail(src, dest_dir=None, size=(320, 320), quality=60):
    """Create a low-resolution JPEG thumbnail for src and return its path.
    If Pillow is not available or creation fails, returns the original path string.
    """

    if str(src).endswith(".webp"):
        return str(src)

    try:
        from PIL import Image
    except ImportError:
        Image=None
        if on_android_platform():
            print("Pillow not available, cannot create thumbnail.")
            # Pillow not available and not on android -> fall back to original image path
            return str(src)

    try:
        src_path = Path(src)
        destination = thumbnail_path_for(src_path, dest_dir)
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


def copy_image_to_internal(dest_name,uri):
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
    dest_path = os.path.join(internal_dir, dest_name)

    output_stream = BufferedOutputStream(
        FileOutputStream(dest_path)
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

    return dest_path


def thumbnail_path_for(src, dest_dir=None):
    """Return a consistent thumbnail Path for a source image.
    Thumbnails are stored in a subfolder named 'thumbs' under dest_dir (or source folder by default).
    """
    p = Path(src)
    if dest_dir:
        dest_dir = Path(dest_dir)
    else:
        dest_dir = p.parent
    thumb_dir = dest_dir / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir / f"{p.stem}_thumb.jpg"


def use_android_classes_to_create_thumbnail(src, dest_dir=None, size=(320, 320), quality=60):
    from jnius import autoclass

    BitmapFactory = autoclass('android.graphics.BitmapFactory')
    Bitmap = autoclass('android.graphics.Bitmap')
    BitmapConfig = autoclass('android.graphics.Bitmap$Config')
    CompressFormat = autoclass('android.graphics.Bitmap$CompressFormat')
    FileOutputStream = autoclass('java.io.FileOutputStream')
    Math = autoclass('java.lang.Math')

    src_path = src
    dest_path = dest_dir
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
    out = FileOutputStream(dest_path)
    resized.compress(CompressFormat.JPEG, quality, out)
    out.close()

    # Cleanup
    bitmap.recycle()
    resized.recycle()


def get_or_create_thumbnail(src, dest_dir=None, size=(320, 320)):
    """Convenience wrapper to obtain a thumbnail path, creating it if necessary."""
    return create_thumbnail(src, dest_dir=dest_dir, size=size)


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
