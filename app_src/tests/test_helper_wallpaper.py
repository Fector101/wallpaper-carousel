"""Tests for utils.helper.change_wallpaper: target flags, API gating, decode failures and
the rule that nothing it does may touch the UI directly (it runs on a worker thread)."""

import sys
import types

import pytest

import utils.helper as helper


class FakeBitmap:
    def __init__(self, path):
        self.path = str(path)


def _install_android_side(monkeypatch, sdk_int=30, set_bitmap_error=None, changed=1, decodes=True):
    """Fakes the Java classes change_wallpaper reaches for. Returns what was recorded."""
    recorded = {"sets": [], "scheduled": [], "toasts": []}

    class FakeWallpaperManager:
        FLAG_SYSTEM = 1
        FLAG_LOCK = 2

        def setBitmap(self, bitmap, region, allow_backup, flags):
            recorded["sets"].append(
                {
                    "path": bitmap.path,
                    "region": region,
                    "allow_backup": allow_backup,
                    "flags": flags,
                }
            )
            if set_bitmap_error is not None:
                raise set_bitmap_error
            return changed

    def fake_decode_file(path):
        return FakeBitmap(path) if decodes else None

    manager_stub = type(
        "WallpaperManagerStub",
        (),
        {
            "FLAG_SYSTEM": FakeWallpaperManager.FLAG_SYSTEM,
            "FLAG_LOCK": FakeWallpaperManager.FLAG_LOCK,
            "getInstance": staticmethod(lambda _context: FakeWallpaperManager()),
        },
    )

    monkeypatch.setattr(helper, "WallpaperManager", manager_stub)
    monkeypatch.setattr(helper, "_toast", lambda message: recorded["toasts"].append(message))

    java_classes = types.ModuleType("android_notify.internal.java_classes")
    java_classes.BuildVersion = type("BuildVersion", (), {"SDK_INT": sdk_int})
    java_classes.BitmapFactory = type("BitmapFactory", (), {"decodeFile": staticmethod(fake_decode_file)})
    java_classes.__path__ = []
    monkeypatch.setitem(sys.modules, "android_notify.internal.java_classes", java_classes)

    monkeypatch.setattr(
        "kivy.clock.Clock.schedule_once",
        lambda callback, *_args, **_kwargs: recorded["scheduled"].append(callback),
    )
    return recorded


@pytest.fixture
def wallpaper(tmp_path):
    path = tmp_path / "wallpapers" / "wall.jpg"
    path.parent.mkdir()
    path.write_bytes(b"image")
    return str(path)


@pytest.mark.parametrize(
    "target, flags",
    [
        (helper.WALLPAPER_TARGET_HOME, 1),
        (helper.WALLPAPER_TARGET_LOCK, 2),
        (helper.WALLPAPER_TARGET_BOTH, 3),
    ],
)
def test_target_selects_the_matching_flags(monkeypatch, wallpaper, target, flags):
    recorded = _install_android_side(monkeypatch)

    assert helper.change_wallpaper(wallpaper, target=target) is True

    assert [call["flags"] for call in recorded["sets"]] == [flags]
    assert recorded["sets"][0]["path"] == wallpaper
    # setBitmap(Bitmap, Rect, boolean, int): jnius resolves overloads by arity, so the arity and
    # the order of these arguments is what the real call has to match.
    assert recorded["sets"][0]["region"] is None
    assert recorded["sets"][0]["allow_backup"] is True


def test_default_target_is_the_lock_screen(monkeypatch, wallpaper):
    # utils/service_helper.set_wallpaper calls change_wallpaper(path) with no target and has
    # always set the lock screen, so the default must stay the lock screen.
    recorded = _install_android_side(monkeypatch)

    assert helper.change_wallpaper(wallpaper) is True

    assert [call["flags"] for call in recorded["sets"]] == [2]


def test_lock_screen_is_refused_below_api_24(monkeypatch, wallpaper):
    recorded = _install_android_side(monkeypatch, sdk_int=23)

    assert helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_LOCK) is False

    assert recorded["sets"] == []


def test_home_screen_works_below_api_24(monkeypatch, wallpaper):
    # FLAG_SYSTEM has no lock-screen API floor, so an old device still gets a home screen.
    recorded = _install_android_side(monkeypatch, sdk_int=23)

    assert helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_HOME) is True

    assert [call["flags"] for call in recorded["sets"]] == [1]


def test_missing_path_never_touches_java(monkeypatch, tmp_path):
    recorded = _install_android_side(monkeypatch)

    assert helper.change_wallpaper(str(tmp_path / "nope.jpg")) is False

    assert recorded["sets"] == []


def test_undecodable_image_is_never_handed_to_the_wallpaper_manager(monkeypatch, wallpaper):
    # BitmapFactory.decodeFile returns null for a corrupt or non-image file. Passing that null
    # on to setBitmap throws a jnius error, so it has to be caught here instead.
    recorded = _install_android_side(monkeypatch, decodes=False)

    assert helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_HOME) is False

    assert recorded["sets"] == []


def test_failure_to_set_is_reported_and_swallowed(monkeypatch, wallpaper):
    recorded = _install_android_side(monkeypatch, set_bitmap_error=RuntimeError("boom"))

    assert helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_HOME) is False

    assert len(recorded["sets"]) == 1


@pytest.mark.parametrize(
    "scenario",
    ["success", "missing_path", "unsupported_lock"],
)
def test_do_ui_thing_runs_on_every_exit_path(monkeypatch, wallpaper, scenario):
    sdk_int = 23 if scenario == "unsupported_lock" else 30
    recorded = _install_android_side(monkeypatch, sdk_int=sdk_int)
    # do_ui_thing is the LoadingLayout.remove callback; it must always fire or the spinner
    # would stay on screen forever. It is queued on the Clock, so drain the queue to see it.
    ran = []

    if scenario == "missing_path":
        wallpaper = str(wallpaper) + "-gone"
    helper.change_wallpaper(
        wallpaper,
        target=helper.WALLPAPER_TARGET_LOCK,
        do_ui_thing=lambda *_args: ran.append(True),
    )
    for callback in recorded["scheduled"]:
        callback(0)

    assert ran == [True]


def test_no_wallpaper_manager_leaves_the_ui_callback_running(monkeypatch, wallpaper):
    recorded = _install_android_side(monkeypatch)
    monkeypatch.setattr(helper, "WallpaperManager", None)
    ran = []

    result = helper.change_wallpaper(wallpaper, do_ui_thing=lambda *_args: ran.append(True))
    for callback in recorded["scheduled"]:
        callback(0)

    assert result is None
    assert ran == [True]


def test_toast_is_built_on_the_clock_not_on_the_worker_thread(monkeypatch, wallpaper):
    # MDToast builds widgets, so a toast raised straight from the worker thread would touch
    # the widget tree off the main thread. It has to go through the Clock.
    recorded = _install_android_side(monkeypatch)

    helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_HOME)

    assert recorded["toasts"] == []
    for callback in recorded["scheduled"]:
        callback(0)
    assert recorded["toasts"] == ["Home screen wallpaper changed"]


def test_toast_names_the_screen_that_was_set(monkeypatch, wallpaper):
    recorded = _install_android_side(monkeypatch)

    helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_LOCK)
    for callback in recorded["scheduled"]:
        callback(0)

    assert recorded["toasts"] == ["Lock screen wallpaper changed"]


def test_service_file_stays_quiet(monkeypatch, wallpaper):
    # utils/service_helper sets wallpapers from a background service, which has no UI to
    # toast into.
    recorded = _install_android_side(monkeypatch)
    config = sys.modules["android_notify.config"]
    monkeypatch.setattr(config, "from_service_file", lambda: True)

    helper.change_wallpaper(wallpaper, target=helper.WALLPAPER_TARGET_LOCK)

    for callback in recorded["scheduled"]:
        callback(0)
    assert recorded["toasts"] == []
