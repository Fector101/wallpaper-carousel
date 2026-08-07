import importlib

import pytest
from unittest import mock

import utils.permissions as permissions

from android_notify.internal.java_classes import BuildVersion


@pytest.fixture
def android_permissions_module():
    with mock.patch("android_notify.config.on_android_platform", return_value=True):
        importlib.reload(permissions)
    yield
    with mock.patch("android_notify.config.on_android_platform", return_value=False):
        importlib.reload(permissions)


def _set_sdk(sdk_int):
    BuildVersion.SDK_INT = sdk_int


def test_required_image_permissions_sdk_34(android_permissions_module):
    _set_sdk(34)
    assert permissions._required_image_permissions() == [
        permissions.Permission.READ_MEDIA_IMAGES,
        permissions._READ_MEDIA_VISUAL_USER_SELECTED,
    ]


def test_required_image_permissions_sdk_33(android_permissions_module):
    _set_sdk(33)
    assert permissions._required_image_permissions() == [permissions.Permission.READ_MEDIA_IMAGES]


def test_required_image_permissions_sdk_below_33(android_permissions_module):
    _set_sdk(29)
    assert permissions._required_image_permissions() == [
        permissions.Permission.READ_EXTERNAL_STORAGE,
        permissions.Permission.WRITE_EXTERNAL_STORAGE,
    ]


def test_status_sdk_34_granted(android_permissions_module):
    _set_sdk(34)
    with mock.patch.object(permissions, "check_permission", return_value=True):
        assert permissions._get_image_permissions() == permissions.ACCESS_GRANTED


def test_status_sdk_34_partial(android_permissions_module):
    _set_sdk(34)
    with mock.patch.object(
        permissions, "check_permission",
        side_effect=lambda perm: perm == permissions._READ_MEDIA_VISUAL_USER_SELECTED,
    ):
        assert permissions._get_image_permissions() == permissions.ACCESS_PARTIAL


def test_status_sdk_34_denied(android_permissions_module):
    _set_sdk(34)
    with mock.patch.object(permissions, "check_permission", return_value=False):
        assert permissions._get_image_permissions() == permissions.ACCESS_DENIED


def test_status_sdk_33_granted(android_permissions_module):
    _set_sdk(33)
    with mock.patch.object(permissions, "check_permission", return_value=True):
        assert permissions._get_image_permissions() == permissions.ACCESS_GRANTED


def test_status_sdk_33_denied(android_permissions_module):
    _set_sdk(33)
    with mock.patch.object(permissions, "check_permission", return_value=False):
        assert permissions._get_image_permissions() == permissions.ACCESS_DENIED


def test_status_sdk_32_granted(android_permissions_module):
    _set_sdk(29)
    with mock.patch.object(permissions, "check_permission", return_value=True):
        assert permissions._get_image_permissions() == permissions.ACCESS_GRANTED


def test_status_sdk_32_denied(android_permissions_module):
    _set_sdk(29)
    with mock.patch.object(permissions, "check_permission", return_value=False):
        assert permissions._get_image_permissions() == permissions.ACCESS_DENIED


def test_has_permission_to_images_true_only_on_full(android_permissions_module):
    _set_sdk(34)
    with mock.patch.object(permissions, "check_permission", return_value=True):
        assert permissions.has_permission_to_images() is True
    with mock.patch.object(
        permissions, "check_permission",
        side_effect=lambda perm: perm == permissions._READ_MEDIA_VISUAL_USER_SELECTED,
    ):
        assert permissions.has_permission_to_images() is False
    with mock.patch.object(permissions, "check_permission", return_value=False):
        assert permissions.has_permission_to_images() is False


def test_ask_permission_skips_request_when_granted(android_permissions_module):
    _set_sdk(34)
    received = []
    with mock.patch.object(permissions, "check_permission", return_value=True), \
         mock.patch.object(permissions, "request_permissions") as req:
        permissions.ask_permission_to_images(callback=received.append)
    assert received == [permissions.ACCESS_GRANTED]
    req.assert_not_called()


def test_ask_permission_short_circuits_partial(android_permissions_module):
    _set_sdk(34)
    received = []
    with mock.patch.object(
        permissions, "check_permission",
        side_effect=lambda perm: perm == permissions._READ_MEDIA_VISUAL_USER_SELECTED,
    ), mock.patch.object(permissions, "request_permissions") as req:
        permissions.ask_permission_to_images(callback=received.append)
    assert received == [permissions.ACCESS_PARTIAL]
    req.assert_not_called()


def test_ask_permission_requests_when_denied_and_reports_granted(android_permissions_module):
    _set_sdk(34)
    received = []
    statuses = iter([permissions.ACCESS_DENIED, permissions.ACCESS_GRANTED])
    with mock.patch.object(permissions, "_get_image_permissions", side_effect=lambda: next(statuses)), \
         mock.patch.object(permissions, "_is_first_image_permission_ask", return_value=True), \
         mock.patch.object(permissions, "_can_show_permission_dialog", return_value=True), \
         mock.patch.object(
             permissions, "request_permissions",
             side_effect=lambda perms, cb: cb(perms, [True, True]),
         ):
        permissions.ask_permission_to_images(callback=received.append)
    assert received == [permissions.ACCESS_GRANTED]


def test_ask_permission_reports_denied(android_permissions_module):
    _set_sdk(34)
    received = []
    statuses = iter([permissions.ACCESS_DENIED, permissions.ACCESS_DENIED])
    with mock.patch.object(permissions, "_get_image_permissions", side_effect=lambda: next(statuses)), \
         mock.patch.object(permissions, "_is_first_image_permission_ask", return_value=True), \
         mock.patch.object(permissions, "_can_show_permission_dialog", return_value=True), \
         mock.patch.object(
             permissions, "request_permissions",
             side_effect=lambda perms, cb: cb(perms, [False, False]),
         ):
        permissions.ask_permission_to_images(callback=received.append)
    assert received == [permissions.ACCESS_DENIED]


def test_ask_permission_denied_on_error(android_permissions_module):
    _set_sdk(34)
    received = []
    with mock.patch.object(permissions, "_required_image_permissions", side_effect=RuntimeError("boom")):
        permissions.ask_permission_to_images(callback=received.append)
    assert received == [permissions.ACCESS_DENIED]
