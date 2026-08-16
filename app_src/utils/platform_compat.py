"""Shared platform helpers extracted from helper.py and image_operations.py.

Provides dependency-free detection of Android/Pydroid environments,
a thread-safe lazy Java-class wrapper, and a thin toast/app_storage_dir
layer that defers JNI imports to first call.
"""

import os
import threading


def on_android_platform():
    return bool(
        os.environ.get("KIVY_BUILD") in {"android"}
        or "P4A_BOOTSTRAP" in os.environ
        or "ANDROID_ARGUMENT" in os.environ
        or os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
    )


def on_pydroid_app():
    return "ru.iiec.pydroid3" in os.environ.get("PYTHONHOME", "")


class LazyJavaClass:
    """Defers jnius import to first use, not at module level.

    Distinct Java classes are keyed by their resolved Java name to
    prevent collisions when the same python_name maps to different
    Java classes across modules.
    """

    __slots__ = ("_python_name", "_java_name")
    _cache = {}
    _lock = threading.Lock()

    def __init__(self, python_name, java_name=None):
        self._python_name = python_name
        self._java_name = java_name

    def _get(self):
        with self._lock:
            key = self._java_name or self._python_name
            if key not in self._cache:
                from jnius import autoclass
                self._cache[key] = autoclass(key)
            return self._cache[key]

    def __getattr__(self, item):
        return getattr(self._get(), item)

    def __call__(self, *args, **kwargs):
        return self._get()(*args, **kwargs)


def toast(msg):
    from ui.widgets.android import toast as _toast_impl
    _toast_impl(msg)


def app_storage_dir():
    if on_pydroid_app():
        return os.getcwd()
    if on_android_platform():
        android_private = os.environ.get("ANDROID_PRIVATE")
        if android_private:
            return android_private
        from android.storage import app_storage_path  # type: ignore
        return str(app_storage_path())
    return os.getcwd()
