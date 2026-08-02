import os

# p4a's Permission class doesn't include this Android 15+ constant
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
        print("_open_app_settings: opened app settings for manual permission grant")
    except Exception as e:
        print(f"_open_app_settings: error opening settings: {e}")


def _can_show_permission_dialog(permissions):
    from android_notify.config import get_python_activity_context
    context = get_python_activity_context()
    return any(context.shouldShowRequestPermissionRationale(p) for p in permissions)


def _get_image_permissions():
    from android_notify.internal.java_classes import BuildVersion
    from android.permissions import Permission

    sdk_int = BuildVersion.SDK_INT
    if sdk_int >= 35:
        return [Permission.READ_MEDIA_IMAGES, _READ_MEDIA_VISUAL_USER_SELECTED]
    elif sdk_int >= 33:
        return [Permission.READ_MEDIA_IMAGES]
    elif sdk_int >= 29:
        return [Permission.READ_EXTERNAL_STORAGE]
    else:
        return [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]


def _has_image_access():
    """Returns True if user has ANY level of image access (full or partial)."""
    from android_notify.internal.java_classes import BuildVersion
    from android.permissions import check_permission

    perms = _get_image_permissions()
    for each in perms:
        state = check_permission(each)
        print(f"_has_image_access: {each}={state}")

    if BuildVersion.SDK_INT >= 35:
        return any(check_permission(p) for p in perms)
    return all(check_permission(p) for p in perms)


def ask_permission_to_images(callback=None):
    try:
        from android.permissions import request_permissions, check_permission
        from android_notify.internal.java_classes import BuildVersion

        perms = _get_image_permissions()

        if _has_image_access():
            print(f"ask_permission_to_images: already has access")
            _remove_image_permission_marker()
            if callback:
                callback(True)
            return

        if not _is_first_image_permission_ask() and not _can_show_permission_dialog(perms):
            _open_app_settings()
            if callback:
                callback(False)
            return

        def wrapped(permissions, grants):
            if BuildVersion.SDK_INT >= 35:
                granted = any(grants)
            else:
                granted = all(grants)
            if granted:
                _remove_image_permission_marker()
            if callback:
                callback(granted)

        request_permissions(perms, wrapped)
    except Exception as error_asking_file_permission:
        print(f'Error asking for permission', error_asking_file_permission)
        if callback:
            callback(False)


def has_permission_to_images():
    try:
        return _has_image_access()
    except Exception as error_has_permission:
        print(f'Error checking permission status', error_has_permission)
        return True
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
