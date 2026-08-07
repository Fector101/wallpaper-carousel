import os

from android_notify.config import on_android_platform
from android_notify.internal.java_classes import BuildVersion

if on_android_platform():
    from android.permissions import check_permission, Permission, request_permissions

# p4a's Permission class doesn't include this Android 14+ constant
_READ_MEDIA_VISUAL_USER_SELECTED = "android.permission.READ_MEDIA_VISUAL_USER_SELECTED"


def _is_first_image_permission_ask():
    marker = ".ASKED_IMAGE_PERMISSION"
    path = os.path.join(os.path.dirname(__file__), marker)
    if os.path.exists(path):
        return False
    try:
        open(path, 'w').close()
    except Exception:
        pass
    return True


def _remove_image_permission_marker():
    marker = ".ASKED_IMAGE_PERMISSION"
    path = os.path.join(os.path.dirname(__file__), marker)
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _open_app_settings():
    try:
        from android_notify.config import get_python_activity_context
        from android_notify.internal.java_classes import Intent, Settings, Uri

        context = get_python_activity_context()
        if not context:
            return
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        intent.setData(Uri.parse(f"package:{context.getPackageName()}"))
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
    except Exception as e:
        print(f"_open_app_settings: error opening settings: {e}")


def _can_show_permission_dialog(permissions):
    from android_notify.config import get_python_activity_context
    context = get_python_activity_context()
    return any(context.shouldShowRequestPermissionRationale(p) for p in permissions)


ACCESS_GRANTED = "GRANTED"
ACCESS_PARTIAL = "PARTIAL"
ACCESS_DENIED = "DENIED"


def _required_image_permissions():
    sdk_int = BuildVersion.SDK_INT
    if sdk_int >= 34: # android 14+
        return [Permission.READ_MEDIA_IMAGES, _READ_MEDIA_VISUAL_USER_SELECTED]
    elif sdk_int >= 33: # android 13+
        return [Permission.READ_MEDIA_IMAGES]
    else: # android 12 and below
        return [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]


def _get_image_permissions():
    """Return ACCESS_GRANTED, ACCESS_PARTIAL, or ACCESS_DENIED for image access."""
    sdk_int = BuildVersion.SDK_INT
    if sdk_int >= 34: # android 14+
        if check_permission(Permission.READ_MEDIA_IMAGES):
            return ACCESS_GRANTED
        if check_permission(_READ_MEDIA_VISUAL_USER_SELECTED):
            return ACCESS_PARTIAL
        return ACCESS_DENIED
    if sdk_int >= 33: # android 13+
        return ACCESS_GRANTED if check_permission(Permission.READ_MEDIA_IMAGES) else ACCESS_DENIED
    # android 12 and below
    return ACCESS_GRANTED if check_permission(Permission.READ_EXTERNAL_STORAGE) else ACCESS_DENIED


def ask_permission_to_images(callback=None):
    try:
        perms = _required_image_permissions()

        status = _get_image_permissions()
        if status == ACCESS_GRANTED:
            _remove_image_permission_marker()
            if callback:
                callback(ACCESS_GRANTED)
            return

        if status == ACCESS_PARTIAL:
            # system already showed its picker and granted limited access
            if callback:
                callback(ACCESS_PARTIAL)
            return

        if not _is_first_image_permission_ask() and not _can_show_permission_dialog(perms):
            _open_app_settings()
            if callback:
                callback(ACCESS_DENIED)
            return

        def wrapped(permissions, grants):
            status = _get_image_permissions()
            print(f"ask_permission_to_images: requested={permissions}, grants={grants} -> {status}")
            if status == ACCESS_GRANTED:
                _remove_image_permission_marker()
            if callback:
                callback(status)

        request_permissions(perms, wrapped)
    except Exception as error_asking_file_permission:
        print(f'Error asking for permission: {error_asking_file_permission}')
        if callback:
            callback(ACCESS_DENIED)


def has_permission_to_images():
    try:
        return _get_image_permissions() == ACCESS_GRANTED or _get_image_permissions() == ACCESS_PARTIAL
    except Exception as error_has_permission:
        print(f'Error checking permission status: {error_has_permission}')
        return False
# Below Works but not need Use Only Permission for images makes more sense

# from kivy.utils import platform # OS
# from kivy.clock import Clock
#
#
# class Intent:
#     def __init__(self,context,activity='old'):
#         pass
#     def setData(uri_parsed):
#         pass
#
# class MActivity:
#     def getPackageName(self):
#         return 'package:org.laner.lan_ft'
#     def startActivity(self,intent:Intent):
#         pass
# class Environment:
#     def isExternalStorageManager(self):
#         return True
# class Uri:
#     def parse(self,package_name):
#         return ''
#
# if platform == 'android':
#     from android import mActivity
#     from android import api_version  # type: ignore
#     from jnius import autoclass
#     from kivymd.toast import toast
#     from android.permissions import request_permissions, Permission,check_permission
#     from android.storage import app_storage_path, primary_external_storage_path
#     Environment = autoclass('android.os.Environment')
#     Intent = autoclass('android.content.Intent')
#     Settings = autoclass('android.provider.Settings')
#     Uri = autoclass('android.net.Uri')
#     PythonActivity = autoclass('org.kivy.android.PythonActivity')
#     mActivity = PythonActivity.mActivity
# else:
#     mActivity=MActivity()
#     app_storage_path=''
#     primary_external_storage_path=''
#     api_version=None
#
# class PermissionHandler:
#     def __init__(self):
#         # Check if any permission is denied and show a prompt with info for the user to allow or cancel.
#         pass
#
#     def requestStorageAccess(self):
#         """Requests access to storage.
#         - If Android 11+, requests 'All Files Access'.
#         - Otherwise, requests storage read and write permissions.
#         """
#         if api_version == None:
#             return None
#
#         if api_version >= 30:
#             self.requestAllFilesAccess()
#         else:
#             self.requestReadWriteAccess()
#
#     def requestAllFilesAccess(self):
#         """Requests 'All Files Access' permission for Android 11+"""
#         if api_version == None:
#             return True
#
#         if not Environment.isExternalStorageManager():
#             try:
#                 intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
#                 print(f"package:{mActivity.getPackageName()}")
#                 intent.setData(Uri.parse(f"package:{mActivity.getPackageName()}"))
#                 Clock.schedule_once(lambda dt: mActivity.startActivity(intent), 2)
#             except Exception as e:
#                 print('PermissionHandler.requestAllFilesAccess --> ', e)
#                 Clock.schedule_once(lambda dt: toast("Failed to request storage permissions"), 2)
#
#     def requestReadWriteAccess(self):
#         """Requests storage read and write permissions."""
#         if api_version == None:
#             return True
#
#         permission_fail_msgs = {
#             Permission.READ_EXTERNAL_STORAGE: "Rejected access to Read Storage",
#             Permission.WRITE_EXTERNAL_STORAGE: "Rejected access to Write Storage"
#         }
#         storage_permissions = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
#         request_permissions(storage_permissions, lambda p, g: self.handlePermissionResult(p, g, permission_fail_msgs))
#         print("Storage permissions not called Android < 11 | Feature not available 101")
#
#     def handlePermissionResult(self, permissions: list, grants: list, fail_msgs: dict):
#         """
#         Handles the result of a permission request.
#
#         Args:
#             permissions (list): List of requested permissions.
#             grants (list): List of granted permissions.
#             fail_msgs (dict): Dictionary mapping permissions to failure messages.
#         """
#         if api_version == None:
#             return True
#
#         for permission in permissions:
#             if permission not in grants:
#                 txt = fail_msgs.get(permission, "Permission denied")
#                 Clock.schedule_once(lambda dt: toast(txt), 2)
#
#     def requestNotificationAccess(self):
#         """Requests notification permission."""
#         request_permissions([Permission.POST_NOTIFICATIONS], lambda p, g: self.handlePermissionResult(p, g, {'POST_NOTIFICATIONS': 'Rejected access to notifications'}))
