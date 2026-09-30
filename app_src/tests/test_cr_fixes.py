from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from jnius import JavaException
from kivy.resources import resource_add_path

resource_add_path(str(Path(__file__).resolve().parent.parent))

import utils.helper as helper
from utils.constants import ServiceStatus

import ui.screens.settings_screen as settings_module
import main


class _Rec:
    def __init__(self):
        self.calls = []
        self.labels = []

    def set_service_status(self, status, label=None):
        self.calls.append(status)
        self.labels.append(label)


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
    screen.app = SimpleNamespace(
        cancel_service_start_retry=mock.Mock(),
        start_service=mock.Mock(return_value=True),
    )
    return screen


def _make_app(settings_screen=None):
    app_obj = main.WallpaperCarouselApp.__new__(main.WallpaperCarouselApp)
    app_obj.sm = SimpleNamespace()
    if settings_screen is not None:
        app_obj.sm.settings_screen = settings_screen
    app_obj.service_port = 1
    app_obj.ui_service_listener = SimpleNamespace(UI_PORT=2)
    app_obj._service_start_attempt = 0
    app_obj._service_start_retry_event = None
    return app_obj


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
        with mock.patch.object(helper.Service, "_Service__get_static_method", side_effect=boom):
            assert svc.start() is False


def _java_exception(*stack_lines):
    error = JavaException(
        "JVM exception occurred: java.lang.reflect.InvocationTargetException")
    error.stacktrace = list(stack_lines)
    return error


def _start_with_java_error(error):
    service_method = mock.Mock()
    service_method.invoke.side_effect = error
    svc = helper.Service("Wallpapercarousel")
    with mock.patch("utils.helper._on_android_platform", return_value=True), \
         mock.patch.object(helper.Service, "is_running", return_value=False), \
         mock.patch.object(
             helper.Service, "_Service__get_static_method",
             return_value=service_method,
         ):
        return svc, svc.start()


def test_service_start_process_is_bad_returns_false():
    error = _java_exception(
        "java.lang.reflect.InvocationTargetException",
        "\tat org.wally.waller.ServiceWallpapercarousel.start(ServiceWallpapercarousel.java:26)",
        "Caused by:",
        "java.lang.SecurityException: Unable to start service Intent { "
        "cmp=org.wally.waller/.ServiceWallpapercarousel (has extras) }: Unable to launch "
        "app org.wally.waller/10933 for service Intent { "
        "cmp=org.wally.waller/.ServiceWallpapercarousel }: process is bad",
    )
    svc, result = _start_with_java_error(error)

    assert result is False
    assert "process is bad" in svc.start_error


def test_service_start_other_java_exception_returns_false():
    error = _java_exception(
        "java.lang.IllegalStateException",
        "Not allowed to start service Intent { cmp=org.wally.waller/.ServiceWallpapercarousel }",
    )
    svc, result = _start_with_java_error(error)

    assert result is False
    assert "Not allowed to start service" in svc.start_error


def test_service_start_success_has_no_start_error():
    svc = helper.Service("Wallpapercarousel")
    svc.start_error = "left over from an earlier attempt"
    with mock.patch("utils.helper._on_android_platform", return_value=True), \
         mock.patch.object(helper.Service, "is_running", return_value=False), \
         mock.patch.object(
             helper.Service, "_Service__get_static_method",
             return_value=mock.Mock(),
         ):
        assert svc.start() is True
    assert svc.start_error is None



def test_start_service_failure_schedules_retry():
    screen = _Rec()
    app_obj = _make_app(screen)
    with mock.patch.object(main, "Service") as fake_cls, \
         mock.patch.object(main.Clock, "schedule_once") as schedule_once:
        fake_cls.return_value.start.return_value = False

        assert main.WallpaperCarouselApp.start_service(app_obj) is False

    assert ServiceStatus.STARTING in screen.calls
    assert ServiceStatus.RETRYING in screen.calls
    assert ServiceStatus.FAILED not in screen.calls
    assert screen.labels[-1] == "Retrying in 15s (1/4)"
    schedule_once.assert_called_once()
    assert schedule_once.call_args[0][1] == 15


def test_start_service_retry_succeeds_and_stops_retrying():
    screen = _Rec()
    app_obj = _make_app(screen)
    with mock.patch.object(main, "Service") as fake_cls, \
         mock.patch.object(main.Clock, "schedule_once") as schedule_once:
        fake_cls.return_value.start.side_effect = [False, True]
        assert main.WallpaperCarouselApp.start_service(app_obj) is False
        retry_callback = schedule_once.call_args[0][0]

        retry_callback(0)

    assert fake_cls.return_value.start.call_count == 2
    assert schedule_once.call_count == 1
    assert ServiceStatus.FAILED not in screen.calls
    assert app_obj._service_start_retry_event is None


def test_start_service_gives_up_after_four_retries():
    screen = _Rec()
    app_obj = _make_app(screen)
    with mock.patch.object(main, "Service") as fake_cls, \
         mock.patch.object(main.Clock, "schedule_once") as schedule_once:
        fake_cls.return_value.start.return_value = False
        main.WallpaperCarouselApp.start_service(app_obj)

        for _ in range(4):
            schedule_once.call_args[0][0](0)

    # first try plus four retries
    assert fake_cls.return_value.start.call_count == 5
    assert schedule_once.call_count == 4
    retrying_labels = [
        label for status, label in zip(screen.calls, screen.labels)
        if status == ServiceStatus.RETRYING
    ]
    assert retrying_labels == [
        "Retrying in 15s (1/4)",
        "Retrying in 15s (2/4)",
        "Retrying in 15s (3/4)",
        "Retrying in 15s (4/4)",
    ]
    assert ServiceStatus.FAILED in screen.calls
    assert app_obj._service_start_retry_event is None


def test_start_service_error_is_retried_not_raised():
    screen = _Rec()
    app_obj = _make_app(screen)
    with mock.patch.object(main, "Service") as fake_cls, \
         mock.patch.object(main.Clock, "schedule_once") as schedule_once:
        fake_cls.side_effect = RuntimeError("no jvm")

        assert main.WallpaperCarouselApp.start_service(app_obj) is False

    assert ServiceStatus.RETRYING in screen.calls
    assert ServiceStatus.FAILED not in screen.calls
    schedule_once.assert_called_once()


def test_cancel_service_start_retry_cancels_pending_event():
    app_obj = _make_app(_Rec())
    event = mock.Mock()
    app_obj._service_start_retry_event = event

    main.WallpaperCarouselApp.cancel_service_start_retry(app_obj)

    event.cancel.assert_called_once()
    assert app_obj._service_start_retry_event is None


def test_set_service_status_label_override():
    screen = _make_screen()

    screen.set_service_status(ServiceStatus.RETRYING, "Retrying in 15s (2/4)")

    assert screen._carousel_status_label.text == "Retrying in 15s (2/4)"


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


def test_terminate_cancels_pending_start_retry():
    screen = _make_screen()
    with mock.patch.object(settings_module, "Service") as fake_cls:
        fake_cls.return_value.stop.return_value = None
        screen._terminate_carousel_confirm()

    screen.app.cancel_service_start_retry.assert_called_once()


def _run_restart_confirm(screen):
    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "Clock") as clock, \
         mock.patch.object(settings_module, "toast") as toast:
        fake_cls.return_value.stop.return_value = True
        screen._restart_service_confirm()
        # last schedule_once is the restart delay, the earlier one is the startup timeout
        after_stop = clock.schedule_once.call_args_list[-1][0][0]
        after_stop(0)
    return toast


def test_restart_toasts_only_when_service_started():
    screen = _make_screen()

    toast = _run_restart_confirm(screen)

    toast.assert_called_once_with("Service boosted!")


def test_restart_stays_quiet_while_start_is_retried():
    screen = _make_screen()
    screen.app.start_service.return_value = False

    toast = _run_restart_confirm(screen)

    assert not toast.called


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