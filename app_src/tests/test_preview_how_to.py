"""Guards for the preview screen's "How To" card.

Two things are easy to get wrong and invisible until the app is on a device in the
other theme: the card was hardcoded to the old dark greys, and the "Don't show again"
checkbox did nothing at all. These tests pin the colours to `theme_colors` (light mode
included), the show-once-per-session / opt-out-persisted behaviour, and - because a
programmatic `active = True` passes even when the widget ignores real taps - that
toggling it by touch is what actually flips the checkbox.
"""

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

from kivy.properties import StringProperty  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402

from ui.screens import preview_screen as preview_module  # noqa: E402
from ui.widgets.modals import HowToPopUpModal  # noqa: E402
from utils.config_manager import ConfigManager  # noqa: E402
from utils.constants import theme_colors  # noqa: E402

FONT_DIR = APP_SRC / "assets" / "fonts" / "Roboto_Mono" / "static"


@pytest.fixture(scope="module", autouse=True)
def _kivymd_app():
    """KivyMD refuses to instantiate any widget without a running MDApp, and the card's
    labels use the custom font, which main.py registers at import time.

    `device_theme` mirrors the real app: it is the property the modal binds, and
    `_sync_theme_colors` pushes it into the `theme_colors` singleton before any widget
    handler runs (see the theme priming note in `.opencode/facts`).
    """
    from kivy.app import App
    from kivy.core.text import LabelBase
    from kivymd.app import MDApp

    if "RobotoMono" not in LabelBase._fonts:
        LabelBase.register(
            name="RobotoMono",
            fn_regular=str(FONT_DIR / "RobotoMono-Regular.ttf"),
            fn_italic=str(FONT_DIR / "RobotoMono-Italic.ttf"),
            fn_bold=str(FONT_DIR / "RobotoMono-Bold.ttf"),
        )

    class _App(MDApp):
        device_theme = StringProperty("dark")

        def _sync_theme_colors(self, *_args):
            theme_colors.theme = self.device_theme

        def build(self):
            return None

    app = _App()
    previous = App._running_app
    App._running_app = app
    app.bind(device_theme=app._sync_theme_colors)
    app._sync_theme_colors()
    yield app
    App._running_app = previous


@pytest.fixture(autouse=True)
def _reset_theme(_kivymd_app):
    """Other test files flip the shared `theme_colors` singleton, so start from dark every
    time and leave it there, otherwise these tests depend on the file order."""
    _kivymd_app.device_theme = "dark"
    theme_colors.theme = "dark"
    yield
    _kivymd_app.device_theme = "dark"


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Points ConfigManager at a temp dir so the tests never touch the real config.json."""
    monkeypatch.setattr(ConfigManager, "_cached_config_dir", str(tmp_path))
    monkeypatch.setattr(ConfigManager, "_cached_config_path", tmp_path / "config.json")
    ConfigManager.write_default_data()
    return ConfigManager()


def _modal():
    return HowToPopUpModal()


def _host():
    return Widget()


def _preview(**attrs):
    """A PreviewScreen without running __init__ (see test_full_screen_carousel._bare_screen)."""
    screen = preview_module.PreviewScreen.__new__(preview_module.PreviewScreen)
    screen._how_to_shown_this_session = False
    screen.how_to_modal = mock.MagicMock()
    screen.how_to_modal.parent = None
    screen.image_widget = mock.MagicMock()
    screen.proxy = mock.MagicMock()
    for key, value in attrs.items():
        setattr(screen, key, value)
    return screen


# --- persisted opt-out --------------------------------------------------------

def test_opt_out_defaults_to_false(isolated_config):
    assert ConfigManager.get_hide_preview_how_to() is False


def test_opt_out_round_trips(isolated_config):
    ConfigManager.set_hide_preview_how_to(True)
    assert ConfigManager.get_hide_preview_how_to() is True

    ConfigManager.set_hide_preview_how_to(False)
    assert ConfigManager.get_hide_preview_how_to() is False


def test_config_written_before_the_key_existed_still_shows_the_card(isolated_config, tmp_path):
    """An install upgrading to this build has no `hide_preview_how_to` key at all."""
    (tmp_path / "config.json").write_text(json.dumps({"interval_mins": 2.0}), encoding="utf-8")

    assert ConfigManager.get_hide_preview_how_to() is False


# --- theming ------------------------------------------------------------------

def test_card_colours_come_from_the_theme(isolated_config):
    modal = _modal()

    assert list(modal.card.md_bg_color) == list(theme_colors.BG_CARD)
    assert list(modal.title_label.md_bg_color) == list(theme_colors.BG_CARD_SUBTLE)
    assert list(modal.title_label.text_color) == list(theme_colors.TEXT_PRIMARY)
    assert list(modal.content_label.text_color) == list(theme_colors.TEXT_PRIMARY)
    assert list(modal.checkbox_label.text_color) == list(theme_colors.TEXT_SECONDARY)
    assert list(modal.button.md_bg_color) == list(theme_colors.BUTTON_ACCENT_BG)
    assert list(modal.checkbox.text_color) == list(theme_colors.CHECKBOX_UNSELECTED)
    assert modal.checkbox.icon == "checkbox-blank-outline"


def test_checking_the_box_recolours_it(isolated_config):
    modal = _modal()

    modal.checkbox.active = True

    assert list(modal.checkbox.text_color) == list(theme_colors.CHECKBOX_SELECTED)
    assert modal.checkbox.icon == "checkbox-marked"


# --- the checkbox responds to touch ---------------------------------------------
#
# KivyMD's MDCheckbox is inert under Kivy 3 (it toggles the removed
# ToggleButtonBehavior.state instead of `activated`), which is why this is MyCheckbox
# now. A programmatic `active = True` would pass even against the old widget, so the
# tap itself has to be what is exercised here.

def _tap(widget):
    """The press/release pair ButtonBehavior hands a real touch through."""
    widget._do_press(None)
    widget._do_release(None)


def test_tapping_the_box_ticks_it(isolated_config):
    modal = _modal()

    _tap(modal.checkbox)

    assert modal.checkbox.active is True
    assert modal.checkbox.icon == "checkbox-marked"
    assert list(modal.checkbox.text_color) == list(theme_colors.CHECKBOX_SELECTED)


def test_tapping_a_ticked_box_unticks_it(isolated_config):
    modal = _modal()

    _tap(modal.checkbox)
    _tap(modal.checkbox)

    assert modal.checkbox.active is False
    assert modal.checkbox.icon == "checkbox-blank-outline"


def test_tapping_the_box_stops_the_card_coming_back(isolated_config):
    host = _host()
    modal = _modal()

    _tap(modal.checkbox)
    modal.show(host)
    modal.hide()

    assert ConfigManager.get_hide_preview_how_to() is True


def test_leaving_the_box_untapped_keeps_the_card_scheduled(isolated_config):
    host = _host()
    modal = _modal()

    _tap(modal.checkbox)
    _tap(modal.checkbox)
    modal.show(host)
    modal.hide()

    assert ConfigManager.get_hide_preview_how_to() is False


def test_the_box_is_a_finger_sized_target(isolated_config):
    """A 22dp box is hard to hit on a phone, and the row it sits in has to be at least
    as tall, or the target overlaps the labels above and below and steals their touches."""
    from kivy.metrics import dp

    modal = _modal()

    assert modal.checkbox.height >= dp(44)
    assert modal.checkbox.height <= modal.checkbox_layout.height


def test_light_mode_recolours_the_card_in_place(isolated_config, _kivymd_app):
    """The old card was hardcoded #151515/#1D1C1C with white text, so light mode was
    unreadable. Toggling the app's theme must repaint the same widgets, not rebuild them."""
    modal = _modal()
    widgets = (modal.card, modal.title_label, modal.content_label, modal.checkbox_label)

    _kivymd_app.device_theme = "light"
    try:
        assert (modal.card, modal.title_label, modal.content_label, modal.checkbox_label) == widgets
        assert list(modal.card.md_bg_color) == [1.0, 1.0, 1.0, 1.0]
        assert list(modal.title_label.text_color) == [0.0, 0.0, 0.0, 1.0]
        assert list(modal.content_label.text_color) == [0.0, 0.0, 0.0, 1.0]
    finally:
        _kivymd_app.device_theme = "dark"


def test_theming_is_applied_at_construction(isolated_config):
    """device_theme is still "dark" when the screens are built and only changes at the
    first 1s theme poll, so a widget that only binds would stay on its construction colours."""
    modal = _modal()

    assert list(modal.card.md_bg_color) == list(theme_colors.BG_CARD)
    assert list(modal.title_label.text_color) == list(theme_colors.TEXT_PRIMARY)


def test_the_card_lays_out_inside_itself(isolated_config):
    """`adaptive_height` with a `size_hint_x` needs the box to re-run `do_layout` after the
    card is centred; mid-pass the button sits below the card's bottom edge.

    The layout passes are driven directly rather than through `Clock.tick()`, which would
    also run the loader callbacks other tests leave behind.
    """
    from kivy.core.window import Window

    modal = _modal()
    modal.size = Window.size
    modal.do_layout()
    modal.card.do_layout()

    assert modal.card.y >= 0
    assert modal.card.top <= Window.height
    for name in ("title_label", "content_label", "checkbox_layout", "button"):
        widget = getattr(modal, name)
        assert widget.y >= modal.card.y, name
        assert widget.top <= modal.card.top, name


# --- dismissal ----------------------------------------------------------------

def test_show_adds_the_card_to_the_host_and_hide_takes_it_away(isolated_config):
    host = _host()
    modal = _modal()

    modal.show(host)
    assert modal.parent is host

    modal.hide()
    assert modal.parent is None


def test_back_key_dismissal_is_recorded_too(isolated_config):
    """PlaceOnMainScreen turns a short back press into hide(), which is the other way out."""
    host = _host()
    modal = _modal()
    modal.checkbox.active = True
    modal.show(host)

    modal._on_key_down(None, 27)
    modal._on_key_up(None, 27)

    assert modal.parent is None
    assert ConfigManager.get_hide_preview_how_to() is True


def test_a_stray_second_hide_does_not_overwrite_the_choice(isolated_config):
    """PreviewScreen.on_leave also calls hide(), on a modal that may already be gone."""
    host = _host()
    modal = _modal()
    modal.show(host)
    modal.hide()
    ConfigManager.set_hide_preview_how_to(True)

    modal.hide()

    assert ConfigManager.get_hide_preview_how_to() is True


def test_showing_again_rearms_the_recording(isolated_config):
    host = _host()
    modal = _modal()
    modal.show(host)
    modal.hide()

    modal.show(host)
    modal.checkbox.active = True
    modal.hide()

    assert ConfigManager.get_hide_preview_how_to() is True


def test_nothing_is_written_before_the_first_showing(isolated_config):
    modal = _modal()
    modal.checkbox.active = True

    modal.hide()

    assert ConfigManager.get_hide_preview_how_to() is False


# --- when it appears ----------------------------------------------------------

def test_the_screen_holds_the_card_without_showing_it(isolated_config):
    """It used to be added as a child in __init__, i.e. permanently on top of the preview."""
    from ui.screens.preview_screen import PreviewScreen

    screen = PreviewScreen()

    assert screen.how_to_modal is not None
    assert screen.how_to_modal.parent is None
    assert screen._how_to_shown_this_session is False


def test_the_card_is_added_above_the_screen_content(isolated_config):
    """`MyMDScreen.add_widget` puts overlays on the screen itself and the rest inside
    `screen_content`. Kivy inserts new children at index 0, so the card has to land there
    to draw over the image."""
    from ui.screens.preview_screen import PreviewScreen

    screen = PreviewScreen()
    screen.add_widget(Widget())  # the same call build_ui makes, which creates screen_content
    screen.how_to_modal.show(screen)
    try:
        assert screen.children[0] is screen.how_to_modal
    finally:
        screen.how_to_modal.hide()


def _run_scheduled(monkeypatch):
    """Returns the list the scheduled callbacks land in."""
    clock = mock.MagicMock()
    monkeypatch.setattr(preview_module, "Clock", clock)
    return clock


def test_shows_on_the_first_entry_only(monkeypatch, isolated_config):
    clock = _run_scheduled(monkeypatch)
    screen = _preview()

    screen._maybe_show_how_to()
    assert clock.schedule_once.call_count == 1
    clock.schedule_once.call_args[0][0]()  # the lambda that actually shows it
    screen.how_to_modal.show.assert_called_once_with(screen)

    # Second visit to the preview screen, later in the same session.
    screen._maybe_show_how_to()
    assert clock.schedule_once.call_count == 1


def test_never_shows_once_the_user_opted_out(monkeypatch, isolated_config):
    clock = _run_scheduled(monkeypatch)
    ConfigManager.set_hide_preview_how_to(True)
    screen = _preview()

    screen._maybe_show_how_to()

    clock.schedule_once.assert_not_called()
    screen.how_to_modal.show.assert_not_called()


def test_a_card_left_open_is_not_scheduled_twice(monkeypatch, isolated_config):
    clock = _run_scheduled(monkeypatch)
    screen = _preview(how_to_modal=mock.MagicMock())
    screen.how_to_modal.parent = object()

    screen._maybe_show_how_to()

    clock.schedule_once.assert_not_called()


def test_leaving_the_preview_screen_takes_a_still_open_card_down(isolated_config):
    screen = _preview()
    screen.how_to_modal.parent = object()

    screen.on_leave()

    screen.how_to_modal.hide.assert_called_once()


def test_leaving_the_preview_screen_ignores_a_dismissed_card(isolated_config):
    screen = _preview()

    screen.on_leave()

    screen.how_to_modal.hide.assert_not_called()


def test_back_key_with_the_card_up_only_closes_the_card(isolated_config):
    """The card binds the back key too, and Kivy runs both handlers, so the screen must
    not navigate on the same press that dismisses the card."""
    screen = _preview()
    screen.how_to_modal.parent = object()
    screen.show_system_ui = mock.MagicMock()
    screen.manager = mock.MagicMock()

    screen.handle_going_back()

    screen.manager.go_to_fullscreen.assert_not_called()


def test_back_key_without_the_card_still_leaves_the_screen(isolated_config):
    screen = _preview()
    screen.show_system_ui = mock.MagicMock()
    screen.manager = mock.MagicMock()

    screen.handle_going_back()

    screen.manager.go_to_fullscreen.assert_called_once()
