from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import sys
import threading

import pytest
from jnius import JavaException
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.resources import resource_add_path

resource_add_path(str(Path(__file__).resolve().parent.parent))

import utils.helper as helper
from utils.constants import ServiceStatus

import ui.screens.full_screen as fullscreen_module
import ui.screens.settings_screen as settings_module
import ui.widgets.layouts as layouts
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

    def on_service_attempt_failed(self):
        self.calls.append(ServiceStatus.ATTEMPT_FAILED)

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
        service_retry_pending=mock.Mock(return_value=False),
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


def _run_attempt(schedule_once, screen):
    """Flash the failure, then run the countdown down to the next attempt."""
    _tick(schedule_once)  # _begin_countdown, after RETRY_FLASH_SECONDS
    for _ in range(helper.Service.START_RETRY_DELAY_SECONDS):
        _tick(schedule_once)


def _begin_countdown(schedule_once):
    """Fire only the flash->countdown handoff, not the countdown itself."""
    assert schedule_once.call_args[0][0].__name__ == "_begin_countdown"
    _tick(schedule_once)


class _StrictColorProperty:
    """Mimics ColorProperty(None), whose allownone defaults to False."""

    def __init__(self):
        self._value = None

    def __set__(self, _obj, value):
        if value is None:
            raise ValueError("None is not allowed for text_color_disabled")
        self._value = value

    def __get__(self, _obj, _owner=None):
        return self._value


class _StrictColorButton:
    def __init__(self):
        self.disabled = False
        self.md_bg_color = None
        self.txt = SimpleNamespace(
            text_color=None,
            text_color_disabled=_StrictColorProperty(),
        )


class _CarouselToolsRecorder:
    """Stands in for CarouselTools; records the disabled state per status."""

    def __init__(self):
        self.restart_btn = SimpleNamespace(txt=SimpleNamespace(text=""))
        self.stop_btn = SimpleNamespace(txt=SimpleNamespace(text=""))
        self.restart_enabled = []

    def set_restart_enabled(self, enabled):
        self.restart_enabled.append(enabled)


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


_PROCESS_IS_BAD_TRACE = (
    "java.lang.reflect.InvocationTargetException",
    "\tat org.wally.waller.ServiceWallpapercarousel.start(ServiceWallpapercarousel.java:26)",
    "Caused by:",
    "java.lang.SecurityException: Unable to start service Intent { "
    "cmp=org.wally.waller/.ServiceWallpapercarousel (has extras) }: Unable to launch "
    "app org.wally.waller/10933 for service Intent { "
    "cmp=org.wally.waller/.ServiceWallpapercarousel }: process is bad",
)


def test_service_start_process_is_bad_returns_false():
    svc, result = _start_with_java_error(_java_exception(*_PROCESS_IS_BAD_TRACE))

    assert result is False
    assert "process is bad" in svc.start_error


def test_last_cause_picks_the_deepest_caused_by():
    trace = "\n".join(_PROCESS_IS_BAD_TRACE)

    cause = helper._last_cause(trace)

    assert cause.startswith("java.lang.SecurityException")
    assert "process is bad" in cause
    # the wrapper frames must not be what gets reported
    assert "InvocationTargetException" not in cause


def test_last_cause_falls_back_when_there_is_no_caused_by():
    assert helper._last_cause(
        "java.lang.IllegalStateException\n\tat org.wally.waller.Foo.bar(Foo.java:1)"
    ) == "java.lang.IllegalStateException"
    assert helper._last_cause("") is None
    assert helper._last_cause(None) is None


def test_service_start_logs_the_underlying_cause_not_just_the_wrapper():
    with mock.patch("utils.logger.app_logger") as app_logger:
        _start_with_java_error(_java_exception(*_PROCESS_IS_BAD_TRACE))

    logged = " ".join(
        str(call.args[0]) for call in app_logger.error.call_args_list)
    # the SecurityException that actually explains the failure
    assert "Unable to launch app" in logged
    assert "process is bad" in logged
    # and the full stack is still captured, at debug level
    debugged = " ".join(
        str(call.args[0]) for call in app_logger.debug.call_args_list)
    assert "ServiceWallpapercarousel.java:26" in debugged


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
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is False

    # the refusal is reported as a failure first, the countdown comes after
    assert screen.calls == [ServiceStatus.STARTING, ServiceStatus.ATTEMPT_FAILED]
    assert screen.ticks == []
    schedule_once.assert_called_once()
    assert schedule_once.call_args[0][0] == svc._begin_countdown
    assert schedule_once.call_args[0][1] == helper.Service.RETRY_FLASH_SECONDS


def test_start_with_retry_countdown_starts_after_the_failure_flash():
    screen = _Rec()
    svc = _retrying_service([False, False], on_start_attempt=screen.on_service_start_attempt,
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is False
        _begin_countdown(schedule_once)

    # FAILED is shown for exactly one scheduled step, then "Retrying in 15s"
    assert screen.calls == [
        ServiceStatus.STARTING,
        ServiceStatus.ATTEMPT_FAILED,
        ServiceStatus.RETRYING,
    ]
    assert screen.ticks == [(1, 4, 15)]


def test_start_with_retry_cancel_during_the_failure_flash():
    screen = _Rec()
    svc = _retrying_service([False] * 3, on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        pending_flash = schedule_once.return_value
        svc.cancel_retry()

    # the pending event is the flash handoff; cancelling it skips the countdown
    assert pending_flash.cancel.called
    assert svc._retry_event is None
    assert screen.ticks == []
    assert screen.calls == [ServiceStatus.ATTEMPT_FAILED]
    assert svc.start.call_count == 1


def test_start_with_retry_cancel_mid_countdown():
    screen = _Rec()
    svc = _retrying_service([False] * 3, on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        _run_attempt(schedule_once, screen)
        # countdown is mid-flight, 14 ticks left
        assert len(screen.ticks) == 15
        pending_tick = schedule_once.return_value
        svc.cancel_retry()

    assert pending_tick.cancel.called
    assert svc._retry_event is None
    assert svc.start.call_count == 2


def test_start_with_retry_countdown_ticks_down_then_retries():
    screen = _Rec()
    svc = _retrying_service([False, False], on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is False
        _run_attempt(schedule_once, screen)

    # one tick per second, second attempt only fires at 0
    assert screen.ticks == [
        (1, 4, 15), (1, 4, 14), (1, 4, 13), (1, 4, 12), (1, 4, 11),
        (1, 4, 10), (1, 4, 9), (1, 4, 8), (1, 4, 7), (1, 4, 6),
        (1, 4, 5), (1, 4, 4), (1, 4, 3), (1, 4, 2), (1, 4, 1),
    ]
    assert svc.start.call_count == 2
    assert ServiceStatus.FAILED not in screen.calls

    # the second refusal flashes before its own countdown restarts at 15
    _begin_countdown(schedule_once)
    assert screen.ticks[-1] == (2, 4, 15)


def test_start_with_retry_succeeds_on_retry_and_stops():
    screen = _Rec()
    svc = _retrying_service([False, True], on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        _run_attempt(schedule_once, screen)

    assert svc.start.call_count == 2
    assert len(screen.ticks) == 15
    assert ServiceStatus.FAILED not in screen.calls
    assert svc._retry_event is None


def test_start_with_retry_gives_up_after_four_retries():
    screen = _Rec()
    svc = _retrying_service([False] * 6, on_start_attempt=screen.on_service_start_attempt,
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        for _ in range(4):
            _run_attempt(schedule_once, screen)

    # first attempt plus four retries
    assert svc.start.call_count == 5
    assert screen.calls.count(ServiceStatus.STARTING) == 5
    # one failure flash per refusal that is actually retried (4, not 5): the
    # last refusal goes straight to the give-up, so the status is FAILED
    assert screen.calls.count(ServiceStatus.ATTEMPT_FAILED) == 4
    assert screen.calls[-1] == ServiceStatus.FAILED
    # the 5th (final) refusal does not flash: it goes straight to the give-up
    assert screen.calls[-2] == ServiceStatus.STARTING
    assert screen.calls[-3] == ServiceStatus.RETRYING
    assert [tick[0] for tick in screen.ticks[::15]] == [1, 2, 3, 4]
    assert svc._retry_event is None


def test_start_with_retry_cancel_stops_the_countdown():
    screen = _Rec()
    svc = _retrying_service([False] * 3, on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        svc.cancel_retry()

    assert schedule_once.return_value.cancel.called
    assert svc._retry_event is None
    assert svc.start.call_count == 1


def test_start_with_retry_none_result_is_not_a_refusal():
    # no mActivity (Pydroid / service-less context) must not spin the retry loop
    screen = _Rec()
    svc = _retrying_service([None], on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        assert svc.start_with_retry() is None

    assert not schedule_once.called
    assert screen.ticks == []
    assert ServiceStatus.FAILED not in screen.calls


def test_retry_logs_every_refusal_with_its_cause():
    screen = _Rec()
    svc = _retrying_service([False, False],
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick)
    svc.start_error = "java.lang.SecurityException: process is bad"
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once, \
         mock.patch("utils.logger.app_logger") as app_logger:
        svc.start_with_retry()
        _run_attempt(schedule_once, screen)

    warnings = [str(call.args[0]) for call in app_logger.warning.call_args_list]
    assert len(warnings) == 2
    assert "attempt 1/4 refused" in warnings[0]
    assert "process is bad" in warnings[0]
    assert "Retrying in 15s" in warnings[0]
    assert "attempt 2/4 refused" in warnings[1]


def test_give_up_log_carries_the_last_error():
    screen = _Rec()
    svc = _retrying_service([False] * 6,
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick,
                            on_give_up=screen.on_service_start_gave_up)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once, \
         mock.patch("utils.logger.app_logger") as app_logger:
        svc.start_with_retry()
        for _ in range(4):
            _run_attempt(schedule_once, screen)

    errors = [str(call.args[0]) for call in app_logger.error.call_args_list]
    assert any("giving up" in line and "Last error:" in line for line in errors)


def test_recovery_is_logged_when_a_retry_succeeds():
    screen = _Rec()
    svc = _retrying_service([False, True],
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick)
    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once, \
         mock.patch("utils.logger.app_logger") as app_logger:
        svc.start_with_retry()
        _run_attempt(schedule_once, screen)

    infos = [str(call.args[0]) for call in app_logger.info.call_args_list]
    assert any("started on attempt 2 after earlier refusals" in line
               for line in infos)


def test_no_recovery_log_when_the_first_attempt_succeeds():
    svc = _retrying_service([True])
    with mock.patch("kivy.clock.Clock.schedule_once"), \
         mock.patch("utils.logger.app_logger") as app_logger:
        assert svc.start_with_retry() is True

    assert not app_logger.info.called


def test_start_service_wires_screen_callbacks():
    screen = _Rec()
    app_obj = _make_app(screen)
    with mock.patch.object(main, "Service") as fake_cls:
        fake_cls.return_value.start_with_retry.return_value = False

        assert main.WallpaperCarouselApp.start_service(app_obj) is False

    _, kwargs = fake_cls.call_args
    assert kwargs["on_start_attempt"] == screen.on_service_start_attempt
    assert kwargs["on_attempt_failed"] == screen.on_service_attempt_failed
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


def test_service_retry_pending_delegates_to_service():
    app_obj = _make_app(_Rec())
    app_obj._carousel_service = mock.Mock(retry_pending=True)

    assert main.WallpaperCarouselApp.service_retry_pending(app_obj) is True


def test_service_retry_pending_without_service_is_false():
    app_obj = _make_app(_Rec())
    app_obj._carousel_service = None

    assert main.WallpaperCarouselApp.service_retry_pending(app_obj) is False


def test_set_service_status_label_override():
    screen = _make_screen()

    screen.set_service_status(ServiceStatus.RETRYING, "Retrying in 15s (2/4)")

    assert screen._carousel_status_label.text == "Retrying in 15s (2/4)"


def test_attempt_failed_status_shows_failed():
    screen = _make_screen()

    screen.on_service_attempt_failed()

    assert screen._carousel_status_label.text == "Failed"


def test_restart_button_is_disabled_while_busy():
    screen = _make_screen()
    tools = _CarouselToolsRecorder()
    screen.carousel_tools = tools

    for status in (ServiceStatus.STARTING, ServiceStatus.RESTARTING,
                   ServiceStatus.RETRYING, ServiceStatus.ATTEMPT_FAILED,
                   ServiceStatus.STOPPING):
        screen.set_service_status(status)

    assert tools.restart_enabled == [False] * 5


def test_restart_button_is_enabled_when_idle():
    screen = _make_screen()
    tools = _CarouselToolsRecorder()
    screen.carousel_tools = tools

    for status in (ServiceStatus.RUNNING, ServiceStatus.STOPPED,
                   ServiceStatus.FAILED):
        screen.set_service_status(status)

    assert tools.restart_enabled == [True] * 3


def test_set_restart_enabled_toggles_disabled_and_dims_both_colours():
    tools = settings_module.CarouselTools.__new__(settings_module.CarouselTools)
    tools.app = SimpleNamespace(device_theme="dark")
    tools.restart_btn = _StrictColorButton()
    tools._restart_enabled = True
    background = list(settings_module.theme_colors.BUTTON_BG)

    tools.set_restart_enabled(False)

    assert tools.restart_btn.disabled is True
    assert tools.restart_btn.md_bg_color == [background[0], background[1], background[2], 0.4]
    assert tools.restart_btn.txt.text_color_disabled == [1, 1, 1, 0.4]

    tools.set_restart_enabled(True)

    assert tools.restart_btn.disabled is False
    assert list(tools.restart_btn.md_bg_color) == background
    # never reset to None: ColorProperty(None) has allownone=False
    assert tools.restart_btn.txt.text_color_disabled == "white"


def test_set_restart_enabled_survives_a_theme_switch():
    tools = settings_module.CarouselTools.__new__(settings_module.CarouselTools)
    tools.app = SimpleNamespace(device_theme="light")
    tools.restart_btn = _StrictColorButton()
    tools._restart_enabled = False
    tools.stop_btn = SimpleNamespace(
        txt=SimpleNamespace(text_color=None),
    )

    tools.set_restart_enabled(False)
    # a theme change while disabled must not restore the enabled colours
    tools.app.device_theme = "dark"
    tools._set_theme_color()

    assert tools.restart_btn.disabled is True
    assert tools.restart_btn.txt.text_color_disabled == [1, 1, 1, 0.4]
    assert tools.restart_btn.txt.text_color == "white"


def test_restart_button_stays_disabled_across_the_failure_flash():
    # STARTING -> ATTEMPT_FAILED -> RETRYING must not hand the button back
    screen = _make_screen()
    tools = _CarouselToolsRecorder()
    screen.carousel_tools = tools

    screen.on_service_start_attempt()
    screen.on_service_attempt_failed()
    screen.on_service_retry_tick(1, 4, 15)

    assert tools.restart_enabled == [False, False, False]
    assert tools.restart_btn.text == "Starting..."


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


def test_stop_while_retries_pending_skips_the_popup():
    screen = _make_screen()
    screen.app.service_retry_pending.return_value = True

    with mock.patch.object(settings_module, "CarouselConfirmPopup", _PopupRecorder), \
         mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "toast") as toast:
        _PopupRecorder.shown = []
        screen.terminate_carousel()

    # nothing to stop, so no confirmation and no Service is even built
    assert _PopupRecorder.shown == []
    assert not fake_cls.called
    screen.app.cancel_service_start_retry.assert_called_once()
    assert screen._carousel_status_label.text == "Stopped"
    toast.assert_called_once_with("Retries cancelled")


def test_stop_without_a_pending_retry_still_asks_for_confirmation():
    screen = _make_screen()
    screen.app.service_retry_pending.return_value = False

    with mock.patch.object(settings_module, "CarouselConfirmPopup", _PopupRecorder), \
         mock.patch.object(settings_module, "Service") as fake_cls:
        _PopupRecorder.shown = []
        screen.terminate_carousel()

    # asking is the whole point here: the service is up and stopping it matters
    assert len(_PopupRecorder.shown) == 1
    assert not fake_cls.called
    screen.app.cancel_service_start_retry.assert_not_called()


def test_stop_label_is_cancel_retries_only_while_a_retry_is_pending():
    screen = _make_screen()
    tools = _CarouselToolsRecorder()
    screen.carousel_tools = tools

    screen.set_service_status(ServiceStatus.STARTING)
    assert tools.stop_btn.text == "Stop Carousel"

    screen.set_service_status(ServiceStatus.ATTEMPT_FAILED)
    assert tools.stop_btn.text == "Cancel Retries"

    screen.set_service_status(ServiceStatus.RETRYING)
    assert tools.stop_btn.text == "Cancel Retries"

    screen.set_service_status(ServiceStatus.RUNNING)
    assert tools.stop_btn.text == "Stop Carousel"


def test_restart_also_cancels_a_pending_retry():
    screen = _make_screen()

    with mock.patch.object(settings_module, "Service") as fake_cls, \
         mock.patch.object(settings_module, "Clock"):
        fake_cls.return_value.stop.return_value = True
        screen._restart_service_confirm()

    screen.app.cancel_service_start_retry.assert_called_once()


def test_retry_pending_is_true_during_every_callback():
    """retry_pending must already be True *inside* on_retry/on_attempt_failed.

    Both countdown callbacks clear `_retry_event` before notifying, so a
    property derived from that event reads False exactly when the UI is told a
    retry is in progress — which is what the Stop button asks about.
    """
    seen = {"flash": [], "tick": [], "give_up": []}
    svc = _retrying_service(
        [False, False, False, False, False, False],
        on_attempt_failed=lambda: seen["flash"].append(svc.retry_pending),
        on_retry=lambda *a: seen["tick"].append(svc.retry_pending),
        on_give_up=lambda: seen["give_up"].append(svc.retry_pending),
    )

    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        assert seen["flash"] == [True]
        for _ in range(4):
            _run_attempt(schedule_once, _Rec())

    assert seen["tick"] and all(seen["tick"]), "a countdown tick saw no pending retry"
    assert len(seen["tick"]) == 4 * helper.Service.START_RETRY_DELAY_SECONDS
    # the chain is over, so the give-up callback must not claim a pending retry
    assert seen["give_up"] == [False]


def test_retry_pending_tracks_the_live_state():
    screen = _Rec()
    svc = _retrying_service([False, True],
                            on_attempt_failed=screen.on_service_attempt_failed,
                            on_retry=screen.on_service_retry_tick)
    assert svc.retry_pending is False

    with mock.patch("kivy.clock.Clock.schedule_once") as schedule_once:
        svc.start_with_retry()
        # pending during the failure flash
        assert svc.retry_pending is True
        _begin_countdown(schedule_once)
        # and still pending partway through the countdown
        assert svc.retry_pending is True
        _tick(schedule_once)
        _tick(schedule_once)
        assert svc.retry_pending is True

        # run the rest; the second attempt succeeds and calls cancel_retry()
        for _ in range(helper.Service.START_RETRY_DELAY_SECONDS - 2):
            _tick(schedule_once)

    assert svc.retry_pending is False


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


class _ToggleRowLabel(EventDispatcher):
    text = StringProperty("")
    color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        for name in ("text", "color"):
            if name in kwargs:
                setattr(self, name, kwargs[name])
        super().__init__()


class _ToggleRowBox(EventDispatcher):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def add_widget(self, widget, *args, **kwargs):
        pass

    def bind(self, **kwargs):
        for name, callback in kwargs.items():
            self.fbind(name, callback)


class _ToggleRowSwitch(EventDispatcher):
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.title_text = None


def _build_toggle_row(app):
    with mock.patch.object(settings_module, "get_app", return_value=app), \
         mock.patch.object(settings_module, "Column", _ToggleRowBox), \
         mock.patch.object(settings_module, "AdaptiveLabel", _ToggleRowLabel), \
         mock.patch.object(layouts.Row, "__init__", lambda self, **kwargs: None), \
         mock.patch.object(layouts.Row, "add_widget", lambda self, w, *a, **kw: None), \
         mock.patch("kivymd.uix.selectioncontrol.MDSwitch", _ToggleRowSwitch):
        return settings_module.ToggleSliderRow()


@contextmanager
def _row_theme(theme):
    previous = settings_module.theme_colors.theme
    settings_module.theme_colors.theme = theme
    try:
        yield settings_module.theme_colors
    finally:
        settings_module.theme_colors.theme = previous


def test_toggle_row_titles_are_not_white_when_the_ui_builds_in_light_mode():
    app = SimpleNamespace(device_theme="light", bind=lambda **kwargs: None)
    with _row_theme("light") as colors:
        row = _build_toggle_row(app)
        row.title_text = "Use On-wake"
        row.sub_title_text = "Get a new wallpaper each time you turn on screen."

        assert list(row.title_widget_ref.color) == list(colors.TEXT_PRIMARY)
        assert list(row.title_widget_ref.color) != [1, 1, 1, 1]
        assert list(row.sub_text_widget.color) == list(colors.TEXT_SECONDARY)


def test_toggle_row_recolors_title_and_subtitle_on_a_theme_change():
    app = SimpleNamespace(device_theme="light", bind=lambda **kwargs: None)
    with _row_theme("light"):
        row = _build_toggle_row(app)
        row.sub_title_text = "Automatically start the carousel when you open the app."

        settings_module.theme_colors.theme = "dark"
        row._set_theme_color()
        assert list(row.title_widget_ref.color) == list(settings_module.theme_colors.TEXT_PRIMARY)
        assert list(row.sub_text_widget.color) == list(settings_module.theme_colors.TEXT_SECONDARY)

        settings_module.theme_colors.theme = "light"
        row._set_theme_color()
        assert list(row.title_widget_ref.color) == list(settings_module.theme_colors.TEXT_PRIMARY)
        assert list(row.title_widget_ref.color) != [1, 1, 1, 1]


def test_toggle_row_survives_a_theme_change_before_the_subtitle_exists():
    app = SimpleNamespace(device_theme="dark", bind=lambda **kwargs: None)
    with _row_theme("dark") as colors:
        row = _build_toggle_row(app)
        assert row.sub_text_widget is None

        settings_module.theme_colors.theme = "light"
        row._set_theme_color()
        assert list(row.title_widget_ref.color) == list(colors.TEXT_PRIMARY)

        row.sub_title_text = "Automatically start the carousel when your phone restarts."
        assert list(row.sub_text_widget.color) == list(settings_module.theme_colors.TEXT_SECONDARY)


def test_invalid_device_theme_falls_back_to_the_last_valid_one():
    app = main.WallpaperCarouselApp.__new__(main.WallpaperCarouselApp)
    app.device_theme = "light"

    assert app._coerce_device_theme("dark") == "dark"
    assert app._coerce_device_theme("light") == "light"
    assert app._coerce_device_theme("unknown") == "light"
    assert app._coerce_device_theme(None) == "light"

    app.device_theme = "unknown"
    assert app._coerce_device_theme("unknown") == "dark"


def test_monitor_never_propagates_an_unresolvable_device_theme():
    app = main.WallpaperCarouselApp.__new__(main.WallpaperCarouselApp)
    app.device_theme = "light"
    app.theme_preference = "adaptive"

    with mock.patch.object(main, "is_device_on_light_mode", return_value="unknown"):
        assert app.monitor_dark_and_light_device_change() == "light"

    with mock.patch.object(main, "is_device_on_light_mode", return_value="dark"):
        assert app.monitor_dark_and_light_device_change() == "dark"

    # ThemeColors.on_theme indexes _COLORS[value] and would raise KeyError otherwise
    settings_module.theme_colors.theme = app.monitor_dark_and_light_device_change()

# --- set-as wallpaper menu -------------------------------------------------
#
# The rows used to carry `on_release=print`, so tapping either one only printed its text.

def _make_fullscreen_screen(current_image="/data/user/0/app/wall.jpg"):
    screen = fullscreen_module.FullscreenScreen.__new__(fullscreen_module.FullscreenScreen)
    screen.app = SimpleNamespace(device_theme="dark")
    screen.set_wallpaper_btn = SimpleNamespace()
    if current_image is not None:
        screen.current_image = current_image
    return screen


def _capture_dropdown_menu(monkeypatch):
    """Stands in for the real DropdownMenu, so the menu can be built without a Window."""
    captured = {}

    class FakeDropdownMenu:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(fullscreen_module, "DropdownMenu", FakeDropdownMenu)
    return captured


def _patch_set_as_side(monkeypatch, on_android=True):
    """Records what the set-as path hands to change_wallpaper, without running it."""
    config = sys.modules["android_notify.config"]
    monkeypatch.setattr(config, "on_android_platform", lambda: on_android)
    monkeypatch.setattr(fullscreen_module, "LoadingLayout", lambda: SimpleNamespace(remove=lambda *_a: None))

    calls = []
    threads = []

    def fake_change_wallpaper(*args, **kwargs):
        calls.append((args, kwargs))

    class FakeThread:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            threads.append(kwargs)

        def start(self):
            # What the real thread does, just inline.
            self.kwargs["target"](
                *self.kwargs.get("args", ()), **self.kwargs.get("kwargs", {})
            )

    monkeypatch.setattr(helper, "change_wallpaper", fake_change_wallpaper)
    monkeypatch.setattr(threading, "Thread", FakeThread)
    return calls, threads


@pytest.mark.parametrize(
    "row, target",
    [(0, helper.WALLPAPER_TARGET_HOME), (1, helper.WALLPAPER_TARGET_LOCK)],
)
def test_set_as_row_sets_that_screen(monkeypatch, row, target):
    screen = _make_fullscreen_screen()
    captured = _capture_dropdown_menu(monkeypatch)
    calls, threads = _patch_set_as_side(monkeypatch)

    screen._build_dropdown_menu_wallpaper_setter()
    assert [item.text for item in captured["items"]] == ["Home Screen", "Lock Screen"]
    assert captured["header_text"] == "Set as"
    assert captured["caller"] is screen.set_wallpaper_btn

    captured["items"][row].on_release()

    assert len(calls) == 1
    args, kwargs = calls[0]
    # The wallpapers on screen, not the lower-resolution carousel texture.
    assert list(args) == ["/data/user/0/app/wall.jpg"]
    assert kwargs["target"] == target
    # do_ui_thing tears the LoadingLayout down, so a set that never finishes would otherwise
    # leave a spinner on screen.
    assert callable(kwargs["do_ui_thing"])
    # setBitmap decodes and hands the bitmap to the system, so it cannot run on the frame the
    # tap was handled on.
    assert threads[0]["target"] is helper.change_wallpaper
    assert threads[0]["args"] == ["/data/user/0/app/wall.jpg"]
    assert threads[0]["kwargs"] == kwargs
    assert threads[0]["daemon"] is True


def test_set_as_row_without_a_wallpaper_does_nothing(monkeypatch):
    # current_image is only assigned by on_current_slide, so it can be absent entirely.
    screen = _make_fullscreen_screen(current_image=None)
    captured = _capture_dropdown_menu(monkeypatch)
    calls, threads = _patch_set_as_side(monkeypatch)

    screen._build_dropdown_menu_wallpaper_setter()
    captured["items"][0].on_release()

    assert calls == []
    assert threads == []


def test_set_as_row_off_android_does_nothing(monkeypatch):
    screen = _make_fullscreen_screen()
    captured = _capture_dropdown_menu(monkeypatch)
    calls, threads = _patch_set_as_side(monkeypatch, on_android=False)

    screen._build_dropdown_menu_wallpaper_setter()
    captured["items"][1].on_release()

    assert calls == []
    assert threads == []
