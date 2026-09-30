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
        self.ticks = []

    def set_service_status(self, status, label=None):
        self.calls.append(status)
        self.labels.append(label)

    def on_service_start_attempt(self):
        self.calls.append(ServiceStatus.STARTING)

    def on_service_retry_tick(self, attempt, total, seconds_left):
        self.calls.append(ServiceStatus.RETRYING)
        self.ticks.append((attempt, total, seconds_left))

    def on_service_start_gave_up(self):
        self.calls.append(ServiceStatus.FAILED)


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
    app_obj._carousel_service = None
    return app_obj


def _retrying_service(start_results, **callbacks):
    """A Service whose start() returns start_results in order."""
    svc = helper.Service("Wallpapercarousel", **callbacks)
    svc.start = mock.Mock(side_effect=list(start_results))
    return svc


def _tick(schedule_once):
    """Fire the countdown tick the helper just scheduled via kivy.Clock."""
    schedule_once.call_args[0][0](0)


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



def test_start_with_retry_refused_schedules_countdown():
    screen = _Rec()
    svc = _retrying_service([False], on_start_attempt=screen.on_service_start_attempt,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is False

    assert screen.calls == [ServiceStatus.STARTING, ServiceStatus.RETRYING]
    assert screen.ticks == [(1, 4, 15)]
    schedule_once.assert_called_once()
    assert schedule_once.call_args[0][1] == 1


def test_start_with_retry_countdown_ticks_down_then_retries():
    screen = _Rec()
    svc = _retrying_service([False, False], on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is False

        for _ in range(helper.Service.START_RETRY_DELAY_SECONDS):
            _tick(schedule_once)

    # one tick per second, second attempt only fires at 0
    assert screen.ticks == [
        (1, 4, 15), (1, 4, 14), (1, 4, 13), (1, 4, 12), (1, 4, 11),
        (1, 4, 10), (1, 4, 9), (1, 4, 8), (1, 4, 7), (1, 4, 6),
        (1, 4, 5), (1, 4, 4), (1, 4, 3), (1, 4, 2), (1, 4, 1),
        (2, 4, 15),
    ]
    assert svc.start.call_count == 2
    assert ServiceStatus.FAILED not in screen.calls


def test_start_with_retry_succeeds_on_retry_and_stops():
    screen = _Rec()
    svc = _retrying_service([False, True], on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        for _ in range(helper.Service.START_RETRY_DELAY_SECONDS):
            _tick(schedule_once)

    assert svc.start.call_count == 2
    assert len(screen.ticks) == 15
    assert ServiceStatus.FAILED not in screen.calls
    assert svc._retry_event is None


def test_start_with_retry_gives_up_after_four_retries():
    screen = _Rec()
    svc = _retrying_service([False] * 6, on_start_attempt=screen.on_service_start_attempt,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        for _ in range(4):
            for _ in range(helper.Service.START_RETRY_DELAY_SECONDS):
                _tick(schedule_once)

    # first attempt plus four retries
    assert svc.start.call_count == 5
    assert screen.calls.count(ServiceStatus.STARTING) == 5
    assert screen.calls[-1] == ServiceStatus.FAILED
    assert [tick[0] for tick in screen.ticks[::15]] == [1, 2, 3, 4]
    assert svc._retry_event is None


def test_start_with_retry_cancel_stops_the_countdown():
    screen = _Rec()
    svc = _retrying_service([False] * 3, on_retry=screen.on_service_retry_tick)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        svc.cancel_retry()

    assert schedule_once.return_value.cancel.called
    assert svc._retry_event is None
    assert svc.start.call_count == 1


def test_start_with_retry_none_result_is_not_a_refusal():
    # no mActivity (Pydroid / service-less context) must not spin the retry loop
    screen = _Rec()
    svc = _retrying_service([None], on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is None

    assert not schedule_once.called
    assert screen.ticks == []
    assert ServiceStatus.FAILED not in screen.calls


def test_start_service_wires_screen_callbacks():
    screen = _Rec()
    app_obj = _make_app(screen)
    with mock.patch.object(main, "Service") as fake_cls:
        fake_cls.return_value.start_with_retry.return_value = False

        assert main.WallpaperCarouselApp.start_service(app_obj) is False

    _, kwargs = fake_cls.call_args
    assert kwargs["on_start_attempt"] == screen.on_service_start_attempt
    assert kwargs["on_retry"] == screen.on_service_retry_tick
    assert kwargs["on_give_up"] == screen.on_service_start_gave_up
    assert app_obj._carousel_service is fake_cls.return_value


def test_start_service_error_is_reported_not_raised():
    app_obj = _make_app(_Rec())
    with mock.patch.object(main, "Service", side_effect=RuntimeError("no jvm")):
        assert main.WallpaperCarouselApp.start_service(app_obj) is False

    assert app_obj._carousel_service is None


def test_cancel_service_start_retry_delegates_to_service():
    app_obj = _make_app(_Rec())
    app_obj._carousel_service = mock.Mock()

    main.WallpaperCarouselApp.cancel_service_start_retry(app_obj)

    app_obj._carousel_service.cancel_retry.assert_called_once()


def test_cancel_service_start_retry_without_service_is_noop():
    app_obj = _make_app(_Rec())
    app_obj._carousel_service = None

    main.WallpaperCarouselApp.cancel_service_start_retry(app_obj)


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