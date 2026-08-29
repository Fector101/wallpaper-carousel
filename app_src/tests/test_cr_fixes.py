from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from kivy.resources import resource_add_path

resource_add_path(str(Path(__file__).resolve().parent.parent))

import utils.helper as helper
from utils.constants import ServiceStatus

import ui.screens.settings_screen as settings_module
import main


class _Rec:
    def __init__(self):
        self.calls = []

    def set_service_status(self, status):
        self.calls.append(status)


class _PopupRecorder:
    shown = []

    def __init__(self, **kw):
        self.kw = kw

    def show(self):
        _PopupRecorder.shown.append(self)


def _make_screen():
    screen = settings_module.SettingsScreen.__new__(settings_module.SettingsScreen)
    screen.built_ui = True
    screen._carousel_status_dot = SimpleNamespace(md_bg_color=None)
    screen._carousel_status_label = SimpleNamespace(text="")
    screen.carousel_tools = None
    screen._startup_timeout_event = None
    screen._stop_timeout_event = None
    return screen


def test_service_start_desktop_returns_true():
    svc = helper.Service("Wallpapercarousel")
    with mock.patch.object(helper.Service, "_Service__run_service_file"):
        assert svc.start() is True


def test_service_start_android_true_false():
    svc = helper.Service("Wallpapercarousel")
    with mock.patch("utils.helper._on_android_platform", return_value=True), \
         mock.patch.object(helper.Service, "is_running", return_value=False):
        with mock.patch.object(
            helper.Service, "_Service__get_static_method",
            return_value=mock.Mock(),
        ):
            assert svc.start() is True
        def boom(*a, **k):
            raise RuntimeError("no such method")
        with mock.patch.object(
            helper.Service, "_Service__get_static_method", side_effect=boom,
        ):
            assert svc.start() is False


def test_start_service_marks_failed_when_start_returns_false():
    screen = _Rec()
    dummy = SimpleNamespace(
        sm=SimpleNamespace(settings_screen=screen),
        service_port=1,
        ui_service_listener=SimpleNamespace(UI_PORT=2),
    )
    with mock.patch.object(main, "Service") as fake_cls:
        fake_cls.return_value.start.return_value = False
        raised = False
        try:
            main.WallpaperCarouselApp.start_service(dummy)
        except Exception:
            raised = True
        assert raised
        assert ServiceStatus.FAILED in screen.calls
        assert ServiceStatus.STARTING in screen.calls


def test_terminate_stop_none_is_stopped():
    screen = _make_screen()
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "toast") as toast:
        fake_cls.return_value.stop.return_value = None
        screen._terminate_carousel_confirm()
        assert screen._carousel_status_label.text == "Stopped"
        toast.assert_called_once_with("Already stopped")


def test_terminate_stop_false_is_failed():
    screen = _make_screen()
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "toast") as toast:
        fake_cls.return_value.stop.return_value = False
        screen._terminate_carousel_confirm()
        assert screen._carousel_status_label.text == "Failed"
        toast.assert_called_once_with("Stop failed")


def test_terminate_stop_true_waits_for_status():
    screen = _make_screen()
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "toast") as toast:
        fake_cls.return_value.stop.return_value = True
        screen._terminate_carousel_confirm()
        assert screen._carousel_status_label.text == "Stopping..."
        assert not toast.called
        assert screen._stop_timeout_event is not None
        screen._cancel_stop_timeout()


def test_restart_running_shows_popup():
    screen = _make_screen()
    _PopupRecorder.shown = []
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "CarouselConfirmPopup", _PopupRecorder), \
         mock.patch.object(screen, "_restart_service_confirm") as confirm:
        fake_cls.return_value.is_running.return_value = True
        screen.restart_service()
        assert len(_PopupRecorder.shown) == 1
        assert not confirm.called


def test_restart_query_failure_shows_popup():
    screen = _make_screen()
    _PopupRecorder.shown = []
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "CarouselConfirmPopup", _PopupRecorder), \
         mock.patch.object(screen, "_restart_service_confirm") as confirm:
        fake_cls.return_value.is_running.side_effect = RuntimeError("boom")
        screen.restart_service()
        assert len(_PopupRecorder.shown) == 1
        assert not confirm.called


def test_restart_not_running_restarts_directly():
    screen = _make_screen()
    _PopupRecorder.shown = []
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "CarouselConfirmPopup", _PopupRecorder), \
         mock.patch.object(screen, "_restart_service_confirm") as confirm:
        fake_cls.return_value.is_running.return_value = False
        screen.restart_service()
        assert not _PopupRecorder.shown
        assert confirm.called


def test_restart_none_desktop_restarts_directly():
    screen = _make_screen()
    _PopupRecorder.shown = []
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "CarouselConfirmPopup", _PopupRecorder), \
         mock.patch.object(screen, "_restart_service_confirm") as confirm:
        fake_cls.return_value.is_running.return_value = None
        screen.restart_service()
        assert not _PopupRecorder.shown
        assert confirm.called