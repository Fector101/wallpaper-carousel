# DO NOT IMPORT ANY UI THING TOP GLOBAL LEVEL
import sys
import threading

def _toast(msg):
    from ui.widgets.android import toast as _toast_impl
    _toast_impl(msg)

# Local platform checks — no jnius import at module level
def _on_android_platform():
    import os
    return bool(
        os.environ.get('KIVY_BUILD') in {'android'}
        or 'P4A_BOOTSTRAP' in os.environ
        or 'ANDROID_ARGUMENT' in os.environ
        or os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
    )

def _on_pydroid_app():
    import os
    return "ru.iiec.pydroid3" in os.environ.get("PYTHONHOME", "")

# Local _LazyJavaClass — defers jnius import to first use, not module level
class _LazyJavaClass:
    __slots__ = ("_python_name", "_java_name")
    _cache = {}
    _lock = threading.Lock()

    def __init__(self, python_name, java_name=None):
        self._python_name = python_name
        self._java_name = java_name

    def _get(self):
        with self._lock:
            name = self._python_name
            if name not in self._cache:
                from jnius import autoclass
                self._cache[name] = autoclass(self._java_name or name)
            return self._cache[name]

    def __getattr__(self, item):
        return getattr(self._get(), item)

if _on_android_platform():
    Log = _LazyJavaClass("Log", "android.util.Log")
    WallpaperManager = _LazyJavaClass("WallpaperManager", "android.app.WallpaperManager")
    ApplicationInfo = _LazyJavaClass("ApplicationInfo", "android.content.pm.ApplicationInfo")
    PythonActivity = _LazyJavaClass("PythonActivity", "org.kivy.android.PythonActivity")
else:
    WallpaperManager = None


def is_wine():
    """
	Detect if the application is running under Wine.
	"""
    import os, platform
    if "WINELOADER" in os.environ:
        return True

    # Check platform.system for specific hints
    if platform.system().lower() == "windows":
        # If running in "Windows" mode but in a Linux environment, it's likely Wine
        return "XDG_SESSION_TYPE" in os.environ or "HOME" in os.environ

    return False


def makeFolder(my_folder):
    """Safely creates a folder if it doesn't exist."""
    import os
    if is_wine():
        my_folder = my_folder.replace('\\', '/')

    if not os.path.exists(my_folder):
        try:
            os.makedirs(my_folder)
        except Exception as e:
            print(f"Error creating folder '{my_folder}': {e}")
    return my_folder


def appFolder() -> str:
    """Creates (if needed) and returns the Laner download folder path."""
    import os
    if _on_pydroid_app():
        folder_path = os.getcwd()
    elif _on_android_platform():
        from android.storage import app_storage_path  # type: ignore # , primary_external_storage_path
        # folder_path = os.path.join(primary_external_storage_path(), 'Pictures', 'Waller')
        folder_path = str(os.path.join(app_storage_path()))
    else:
        folder_path = os.getcwd()

    makeFolder(folder_path)
    return folder_path


class Tee:
    """Redirects writes to both the original stream and a file."""

    def __init__(self, file_path, mode='a'):
        self.file = open(file_path, mode, encoding='utf-8')
        self.stdout = sys.__stdout__  # keep original console output

    def write(self, message):
        # Write to console
        self.stdout.write(message)
        self.stdout.flush()

        # Write to file
        self.file.write(message)
        self.file.flush()

        self.fix_log_to_terminal_on_android(message)

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    @staticmethod
    def fix_log_to_terminal_on_android(message):
        if _on_android_platform():

            Log.d("python", message)




def app_external_storage_path():
    from android_notify.config import get_python_activity_context
    context = get_python_activity_context()

    ext_dir = context.getExternalFilesDir(None)
    return ext_dir.getAbsolutePath() if ext_dir else appFolder()
	
def write_logs_to_file(log_folder_name="logs", file_name="all_output1.txt"):
    from utils.constants import DEV
    import os
    from datetime import datetime
    if DEV or not _on_android_platform():
        return
    try:

        log_folder = os.path.join(app_external_storage_path(), log_folder_name)
        makeFolder(log_folder)

        # Log file path
        log_file_path = os.path.join(log_folder, file_name)

        # Add a timestamp header for new session
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"New session started: {datetime.now()}\n")
            f.write("=" * 60 + "\n")

        # Redirect stdout and stderr
        tee = Tee(log_file_path)
        sys.stdout = tee
        sys.stderr = tee
    except Exception as error_saving_logs:
        print('Error directing logs:', error_saving_logs)


class Service:
    def __init__(self, name, args_str="", extra=True):
        try:
            from android import mActivity  # type: ignore
        except (ModuleNotFoundError, ImportError):
            mActivity = None
        self.mActivity = mActivity if not _on_pydroid_app() else None
        self.args_str = args_str
        self.name = name
        self.extra = extra
        self._method_cache = {}
        self.service = self.__load_service_class() if self.mActivity else None

    def get_name(self):
        if not self.mActivity:
            return None
        context = self.mActivity.getApplicationContext()
        return str(context.getPackageName()) + '.Service' + self.name

    def __load_service_class(self):
        # Find the app's generated service class via the app class loader so this
        # works from background threads (JNI FindClass cannot see app dex classes
        # on natively-attached threads). Avoids autoclass()'s slow full-hierarchy
        # reflection and sidesteps pyjnius 1.7.0's corrupted Class.getMethod /
        # forName signatures.
        class_loader = self.mActivity.getClass().getClassLoader()
        return class_loader.loadClass(self.get_name())

    @staticmethod
    def __ensure_method_invoke():
        # The manual java.lang.reflect.Method wrapper in pyjnius 1.7.0 lacks
        # `invoke`; add it (idempotent) before we enumerate methods and call it.
        from jnius import JavaMethod
        from jnius.reflect import Method
        if not hasattr(Method, 'invoke'):
            Method.invoke = JavaMethod('(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;')

    def __get_static_method(self, method_name, argc):
        key = (method_name, argc)
        if key in self._method_cache:
            return self._method_cache[key]
        self.__ensure_method_invoke()
        for method in self.service.getMethods():
            if method.getName() == method_name and len(method.getParameterTypes()) == argc:
                self._method_cache[key] = method
                return method
        raise Exception(
            "No static method {0} with {1} arguments on {2}".format(method_name, argc, self.get_name()))

    def is_running(self):
        if not self.mActivity:
            return None

        from android_notify.internal.java_classes import cast

        service_name = self.get_name()
        context = self.mActivity.getApplicationContext()
        thing = self.mActivity.getSystemService(context.ACTIVITY_SERVICE)

        manager = cast('android.app.ActivityManager', thing)
        for service in manager.getRunningServices(100):
            found_service = service.service.getClassName()
            print("found_service: ", found_service)
            if found_service == service_name:
                return True
        return False

    def stop(self):
        if not self.mActivity:
            return None

        try:
            if not self.is_running():
                print("Service not running")
                return None

            self.__get_static_method('stop', 1).invoke(None, (self.mActivity,))
            return True

        except Exception as error_stopping_service:
            print("Error stopping service:", error_stopping_service)
            import traceback
            traceback.print_exc()
            return False

    def start(self):
        import json
        if not _on_android_platform():
            self.__run_service_file()
            return None
        if not self.mActivity:
            return None

        state = self.is_running()
        print(f"service name: {self.get_name()}, state: {state}, passed in name: {self.name}")

        arg = json.dumps(self.args_str)
        try:
            self.__get_static_method('start', 2).invoke(None, (self.mActivity, arg))
        except Exception as error_starting_service:
            print("Error starting service:", error_starting_service)
            import traceback
            traceback.print_exc()

    def __run_service_file(self):
        import os, json, runpy, threading
        from utils.constants import WALLPAPER_SERVICE_PATH

        def start_service():
            os.environ.setdefault("PYTHON_SERVICE_ARGUMENT", json.dumps(self.args_str))

            runpy.run_path(
                WALLPAPER_SERVICE_PATH,
                run_name="__main__"
            )

        threading.Thread(
            target=start_service,
            daemon=True
        ).start()


def format_time_remaining(seconds):
    """Format seconds into minutes:seconds for countdown"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def smart_convert_minutes(minutes: float) -> str:
    total_seconds = int(minutes * 60)

    hours = total_seconds // 3600
    remaining_seconds = total_seconds % 3600
    mins = remaining_seconds // 60
    secs = remaining_seconds % 60

    result_parts = []

    if hours > 0:
        result_parts.append(f"{hours}hr" if hours == 1 else f"{hours}hrs")

    if mins > 0:
        result_parts.append(f"{mins}min" if mins == 1 else f"{mins}mins")

    if secs > 0:
        result_parts.append(f"{secs}sec" if secs == 1 else f"{secs}secs")

    return " ".join(result_parts) if result_parts else "0secs"


def get_free_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", 0))  # bind to a random free port
    port = s.getsockname()[1]
    s.close()
    return port


def change_wallpaper(wallpaper_path, do_ui_thing=None):
    """Actually set the wallpaper"""
    import os, traceback
    def run_ui_thing():
        if do_ui_thing:
            from kivy.clock import Clock
            try:
                Clock.schedule_once(do_ui_thing)
            except Exception as error_running_ui_function:
                print(f"Error doing UI thing: {error_running_ui_function}")
                traceback.print_exc()
    try:
        if not wallpaper_path or not os.path.exists(wallpaper_path):
            print("Invalid wallpaper path")
            run_ui_thing()
            return False

        from android_notify.config import get_python_activity_context, from_service_file
        from android_notify.internal.java_classes import BuildVersion, BitmapFactory

        context = get_python_activity_context()
        wallpaper_manager = WallpaperManager.getInstance(context) if WallpaperManager else None

        if not wallpaper_manager:
            print("Failed to set wallpaper: wallpaper_manager = None")
            run_ui_thing()
            return None

        elif BuildVersion.SDK_INT >= 24:  # Android 7.0+
            bitmap = BitmapFactory.decodeFile(wallpaper_path)
            FLAG_LOCK = WallpaperManager.FLAG_LOCK
            wallpaper_manager.setBitmap(bitmap, None, True, FLAG_LOCK)
            if not from_service_file():
                _toast("Changed Wallpaper")
            # print(f"Success: Lock screen wallpaper changed to: {os.path.basename(wallpaper_path)}")
        else:
            _toast("Changed Not Supported")
            print("Fail: Lock screen wallpaper not supported on this Android version.")
        run_ui_thing()
        return True
    except Exception as e:
        _toast("Failed to Change")
        print("Failed to set wallpaper:", e)
        run_ui_thing()
        return False


class Font:
    def __init__(self, name, base_folder):
        self.base_folder = base_folder
        self.name = name

    def get_type_path(self, fn_type):
        import os
        return os.path.join(self.base_folder, self.name + '-' + fn_type + '.ttf')


def load_kv_file(module_name="", py_file_absolute_path=""):
    import os
    if module_name:
        print("using absolute py path")
        return None
    if not os.path.exists(py_file_absolute_path):
        print("Invalid py file path")
        return False

    from kivy.lang import Builder

    # Remove any .py or .pyc extension and add .kv
    if py_file_absolute_path.endswith(".pyc"):
        kv_file_path = py_file_absolute_path[:-4] + ".kv"
    else:
        # This handles both .py files and any other case
        kv_file_path = py_file_absolute_path.rsplit(".py", 1)[0] + ".kv"

    Builder.unload_file(filename=kv_file_path)
    Builder.load_file(filename=kv_file_path)

    return kv_file_path


def toInt(text):
    if not text:
        return None
    try:
        return int(text)
    except ValueError as error_changing_to_int:
        print(error_changing_to_int)
        import traceback
        traceback.print_exc()
    return None


def fix_input_on_linux():
    from kivy.utils import platform
    if platform != 'linux':
        return None
    from kivy import Config
    # Linux has some weirdness with the touchpad by default... remove it
    options = Config.options('input')
    for option in options:
        if Config.get('input', option) == 'probesysfs':
            Config.remove_option('input', option)

    return None


def register_fonts():
    from kivy.core.text import LabelBase
    robot_mono = Font(name='RobotoMono', base_folder="assets/fonts/Roboto_Mono/static")
    LabelBase.register(
        name="RobotoMono",
        fn_regular=robot_mono.get_type_path('Regular'),
        fn_italic=robot_mono.get_type_path('Italic'),
        fn_bold=robot_mono.get_type_path('Bold'),
    )


def _ui_port_store_path():
    import os
    return os.path.join(appFolder(), "ui_port.txt")

def _service_port_store_path():
    import os
    return os.path.join(appFolder(), "port.txt")


def get_stored_running_ui_server_port():
    import os
    path = _ui_port_store_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return toInt(f.read())
    return None


def get_stored_running_service_server_port():
    import os
    path = _service_port_store_path()
    if os.path.exists(path):
        with open(path, "r") as f:
            return toInt(f.read())
    return None


def get_current_wallpaper():
    import os
    try:
        current_wallpaper_store_path = os.path.join(appFolder(), 'wallpaper.txt')
        with open(current_wallpaper_store_path, "r") as f:
            path = f.read()
    except FileNotFoundError:
        path = "assets/icons/icon.png"
    return path or "assets/icons/icon.png"


def is_running_debug_build():
    if not _on_android_platform():
        return True

    try:
        context = PythonActivity.mActivity
        return (
            context.getApplicationInfo().flags &
            ApplicationInfo.FLAG_DEBUGGABLE
        ) != 0
    except Exception as e:
        print(f"Error checking debuggable status: {e}")
        return False
