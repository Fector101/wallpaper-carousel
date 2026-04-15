"""
Front-Facing Camera App - with quality selector + live preview rotation (canvas transform).
Enhanced UI design with modern look & feel.
"""

import traceback
from datetime import datetime
from functools import partial

from kivy.clock import Clock, mainthread

from android_notify.config import on_android_platform, get_package_name
from android_notify.internal.java_classes import cast, autoclass
from ui.widgets.layouts import MyMDScreen
from utils.logger import app_logger

if on_android_platform():
    from android.permissions import request_permissions, Permission # type: ignore

from utils.model import get_app


C_DEBUG = 1

C_SCAN_OK = 0
C_SCAN_KO = 1
C_SCAN_PC = 2

C_SCAN_QR = 69
C_SCAN_CAMERA = C_SCAN_QR+1



class CameraScreen(MyMDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()

        self._cb_end_scan = None
        self.name="camera"
        self._PythonActivity = autoclass("org.kivy.android.PythonActivity")
        self._Intent = autoclass("android.content.Intent")
        self._ActivityCamera = autoclass(f"{get_package_name()}.CameraActivity")

        self._Activity = autoclass("android.app.Activity")
        self.build()

    def build(self):
        print('called binding CameraScreen.build')
        if on_android_platform():
            from android import activity # type: ignore
            activity.bind(on_activity_result=self._on_activity_result)

    def do_photo(self, cb_end_scan):
        """"""
        self._cb_end_scan = cb_end_scan
        if on_android_platform():
            request_permissions(
                [Permission.CAMERA, Permission.VIBRATE],
                self._call_lib_photo
            )
        else:
            #handle pc
            Clock.schedule_once(partial(self._on_activity_result, C_SCAN_CAMERA, None, None), 0)

    @mainthread
    def _on_activity_result(self, request_code, result_code, intent, *args):
        """Call from java/android if on android, otherwiise diretly from Clock.schedule_interval
            *args is used only because schedule_interval pass dt. @https://kivy.org/doc/stable/api-kivy.clock.html
        """
        print(f"[PY] activity_result → req={request_code}, result={result_code}, intent={intent}, args:{args}")
        print(f"(C_SCAN_QR, C_SCAN_CAMERA): {C_SCAN_QR}, {C_SCAN_CAMERA}")
        # PY] activity_result → req=70, result=0, intent=<android.content.Intent at 0x6c7c404730 jclass=android/content/Intent jself=<LocalRef obj=0x0 at 0x6c7c418eb0>>, args:()


        if request_code not in (C_SCAN_QR, C_SCAN_CAMERA):
            return

        if on_android_platform():
            if result_code == self._Activity.RESULT_OK and intent:
                if request_code == C_SCAN_QR:
                    print('bad still thinks QR Code stuff exists')
                    get_str_data = self._ActivityQR.EXTRA_QR_DATA
                else:
                    get_str_data = self._ActivityCamera.EXTRA_PHOTO_PATH
                value = intent.getStringExtra(get_str_data)
                result = (C_SCAN_OK, value)
            else:
                msg = "QrWork::Timeout / Users ends"
                result = (C_SCAN_KO, msg)
        else:
            # handle pc
            result = "Not android"

        if callable(self._cb_end_scan):
            Clock.schedule_once(lambda dt: self._cb_end_scan(result), 0)
        else:
            app_logger.error(f"Error: {self._cb_end_scan} not collable. Skip")



    def _call_lib_photo(self, permissions, grants):
        """"""
        print(f"permissions:{permissions}")
        if on_android_platform():
            if not all(grants):
                try:
                    print(f"QrWork::Not all permits: %s" % repr(grants))
                except Exception as e:
                    print(f'unfamiliar syntax e: {e}')
                return
            try:
                activity = cast("android.app.Activity", self._PythonActivity.mActivity)
                intent = self._Intent(activity, self._ActivityCamera)
                activity.startActivityForResult(intent, C_SCAN_CAMERA)
            except Exception as starting_activity_error:
                print(f"starting_activity_error; {starting_activity_error}")

    @mainthread
    def callable_test(self, result):
        print(f"callable_test from App._ret_scan_load_config {result}")
        # callable_test from App._ret_scan_load_config (1, 'QrWork::Timeout / Users ends')
        # callable_test from App._ret_scan_load_config (0, '/data/user/0/org.wally.waller/cache/captures/IMG_20260414_225638.jpg')
        print(f"got: {result}, [0]: {result[0]}")
        if not result[0]:
            complete_file_path = result[1]
            print(f"using file: {complete_file_path}")
            try:
                self.app.file_operation.copy_add([complete_file_path])
            except Exception as error_adding_image:
                print(f"error_adding_image:{error_adding_image}")
                traceback.print_exc()
        self.manager.current = "thumbs"

    def capture_photo(self, *args):
        print(f"args:{args}")
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            quality_name = self._quality.lower()
            png_name = f'capture_{quality_name}_{timestamp}.png'
            png_path = self._save_path(png_name)

            self.camera.export_to_png(png_path)
            final_path = self._fix_rotation_and_compress(png_path, timestamp, quality_name)

            self.status_label.text = f'Saved ({self._quality})'
            self.path_label.text = final_path
            self._scan_gallery(final_path)

        except Exception as e:
            self.status_label.text = f'Capture error: {e}'

    def start_camera(self):
        print("from start camera, start_camera")
        self.do_photo(self.callable_test)


    def go_to_gallery_screen(self,*_):
        self.release_camera()
        setattr(self.manager, "current", "thumbs")

if __name__ == '__main__':
    from kivymd.app import MDApp


    class FrontCameraApp(MDApp):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.c=CameraScreen()

        def build(self):
            self.title = ' Front Camera'
            Clock.schedule_once(lambda x: self.on_stop(),5)
            return self.c

        def on_stop(self):
            if hasattr(self.c, 'release_camera'):
                self.c.release_camera()


    FrontCameraApp().run()