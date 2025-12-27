import os
from jnius import autoclass


ON_ANDROID = False
def is_platform_android():
    # Took this from kivy to fix my logs in P4A.hook, so no need to import things i don't need by doing `from kivy.utils import platform`
    if os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME"):
        return True
    kivy_build = os.environ.get('KIVY_BUILD', '')
    if kivy_build in {'android'}:
        return True
    elif 'P4A_BOOTSTRAP' in os.environ:
        return True
    elif 'ANDROID_ARGUMENT' in os.environ:
        return True

    return False


if is_platform_android():
    ON_ANDROID = True

def from_service_file():
    return 'PYTHON_SERVICE_ARGUMENT' in os.environ


def on_flet_app():
    return os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")

def get_activity_class_name():
    ACTIVITY_CLASS_NAME = os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME") # flet python
    if not ACTIVITY_CLASS_NAME:
        try:
            from android import config
            ACTIVITY_CLASS_NAME = config.JAVA_NAMESPACE
        except (ImportError, AttributeError):
            ACTIVITY_CLASS_NAME = 'org.kivy.android'
    return ACTIVITY_CLASS_NAME



def get_python_activity():
    if not ON_ANDROID:
        from .facade import PythonActivity
        return PythonActivity
    ACTIVITY_CLASS_NAME = get_activity_class_name()
    if on_flet_app():
        PythonActivity = autoclass(ACTIVITY_CLASS_NAME)
    else:
        PythonActivity = autoclass(ACTIVITY_CLASS_NAME + '.PythonActivity')
    return PythonActivity


def get_python_service():
    if not ON_ANDROID:
        return None
    PythonService = autoclass(get_activity_class_name() + '.PythonService')
    return PythonService.mService


def get_python_activity_context():
    if not ON_ANDROID:
        from .facade import Context
        return Context

    PythonActivity = get_python_activity()
    if from_service_file():
        service = get_python_service()
        context = service.getApplication().getApplicationContext()
    else:
        context = PythonActivity.mActivity
    return context

