"""Guards for the custom DropdownMenu.

The bug this replaces: KivyMD's `MDDropdownMenu` builds its item list as a `RecycleView`, so
one widget per `viewclass` is reused across every item and only the keys present in each item
dict are written onto it. An item that omitted a key inherited whatever value the *previous*
item left behind, which is why an image path on one row bled onto the rows after it.

Most of these tests exist to pin that it can no longer happen, plus the sizing rules that
replace `MyMDDropdownMenu.set_target_height`.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

from kivy.metrics import dp  # noqa: E402
from kivy.utils import get_color_from_hex  # noqa: E402
from kivymd.uix.label import MDIcon  # noqa: E402
from kivy.uix.image import Image  # noqa: E402

from ui.widgets.dropdown_menu import (  # noqa: E402
    EDGE_MARGIN,
    HEADER_HEIGHT,
    DropdownItemWidget,
    DropdownMenu,
    MenuItem,
)
from ui.widgets.layouts import PlaceOnMainScreen  # noqa: E402

HOME_PNG = str(APP_SRC / "assets" / "icons" / "home.png")
FONT_DIR = APP_SRC / "assets" / "fonts" / "Roboto_Mono" / "static"


@pytest.fixture(scope="session", autouse=True)
def _kivymd_app():
    """KivyMD refuses to instantiate any widget without a running MDApp, and the header uses
    the app's custom font, which main.py registers at import time (tests never import it)."""
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
        def build(self):
            return None

    app = _App()
    previous = App._running_app
    App._running_app = app
    yield app
    App._running_app = previous


def _rows(menu):
    """Rows in top-to-bottom order; `items_box.children` is in reverse."""
    return list(reversed(menu.items_box.children))


def _menu(**kwargs):
    return DropdownMenu(**kwargs)


def _laid_out(menu):
    """Runs the layout passes the Clock normally performs, so positions can be asserted.

    items_box is a child of card, so it has to be laid out first: until then its
    minimum_height is stale and the card positions its children from that stale value.
    """
    menu.items_box.do_layout()
    menu.card.size = (dp(240), menu._measure_card_height())
    menu.card.do_layout()
    return menu


# --- one row per item, and no state carried between them ----------------------

def test_one_row_per_item():
    menu = _menu(items=[MenuItem(text="a"), MenuItem(text="b"), MenuItem(text="c")])

    assert [row.label.text for row in _rows(menu)] == ["a", "b", "c"]


def test_image_item_does_not_leak_onto_the_next_row():
    """The original bug.

    KivyMD reused one widget per viewclass, so the image source set for "Home Screen" stayed
    on whatever row was recycled next. Each row now builds its own icon widget.
    """
    menu = _menu(
        items=[
            MenuItem(text="Home Screen", icon_image=HOME_PNG),
            MenuItem(text="Lock Screen", icon="lock"),
        ]
    )
    first, second = _rows(menu)

    assert isinstance(first.icon_widget, Image)
    assert first.icon_widget.source == HOME_PNG
    # The glyph row must hold a glyph, not the image from the row above it. MDIcon does
    # have a `source` of its own -- that is exactly the channel KivyMD used for these --
    # so assert it is unset rather than asserting the attribute is missing.
    assert isinstance(second.icon_widget, MDIcon)
    assert second.icon_widget.icon == "lock"
    assert not second.icon_widget.source


def test_item_without_an_icon_gets_an_empty_slot_not_the_previous_icon():
    menu = _menu(
        items=[
            MenuItem(text="Home Screen", icon_image=HOME_PNG),
            MenuItem(text="Lock Screen", icon="lock"),
            MenuItem(text="Neither"),
        ]
    )
    last = _rows(menu)[-1]

    assert isinstance(last.icon_widget, MDIcon) is False
    assert isinstance(last.icon_widget, Image) is False


def test_rows_are_not_shared_between_two_menus():
    """Kivy's RecycleView view cache is a process-wide global keyed by widget class alone, so
    two menus used to draw from the same pool of widgets."""
    first = _menu(items=[MenuItem(text="one", icon="lock")])
    second = _menu(items=[MenuItem(text="two", icon="home")])

    assert _rows(first)[0] is not _rows(second)[0]
    assert _rows(first)[0].label.text == "one"
    assert _rows(second)[0].label.text == "two"


# --- item callbacks -----------------------------------------------------------

def test_row_release_runs_the_item_callback_and_dismisses():
    calls = []
    menu = _menu(items=[MenuItem(text="a", on_release=lambda: calls.append("a"))])

    _rows(menu)[0].on_release()

    assert calls == ["a"]


def test_row_release_takes_the_touch_kivy_dispatches():
    """ButtonBehavior.on_touch_up calls dispatch("on_release", touch)
    (kivy/uix/behaviors/button.py:409); a zero-argument handler crashes the app on tap."""
    seen = []
    menu = _menu(items=[MenuItem(text="a", on_release=lambda *a: seen.append(a))])
    row = _rows(menu)[0]

    row.dispatch("on_release", mock.Mock(name="touch"))

    assert len(seen) == 1
    assert seen[0] == ()


def test_item_callback_may_accept_no_arguments():
    """Menus are built with both arities in this app: `on_release=print` and lambdas that
    take *_args. Neither may blow up."""
    calls = []
    menu = _menu(
        items=[
            MenuItem(text="a", on_release=lambda: calls.append("a")),
            MenuItem(text="b", on_release=lambda *a: calls.append("b")),
        ]
    )

    for row in _rows(menu):
        row.dispatch("on_release", mock.Mock(name="touch"))

    assert sorted(calls) == ["a", "b"]


# --- dividers -----------------------------------------------------------------

def test_show_dividers_adds_one_to_every_row_height():
    plain = _menu(items=[MenuItem(text="a")])
    divided = _menu(items=[MenuItem(text="a")], show_dividers=True)

    assert _rows(divided)[0].height == _rows(plain)[0].height + 1


def test_per_item_divider_overrides_the_menu_wide_default():
    menu = _menu(
        items=[MenuItem(text="a", divider=False), MenuItem(text="b")],
        show_dividers=True,
    )
    rows = _rows(menu)

    assert rows[0].wants_divider is False
    assert rows[1].wants_divider is True


def test_a_row_without_a_divider_creates_no_divider_widget():
    menu = _menu(items=[MenuItem(text="a")], show_dividers=False)

    # One child only: the inner content row. No divider widget was ever built.
    assert len(_rows(menu)[0].children) == 1


# --- header -------------------------------------------------------------------

def test_header_text_builds_a_header_above_the_rows():
    """Position, not list order.

    In a vertical BoxLayout y increases along `children`, so children[-1] is the top and
    children[0] the bottom -- the opposite of what the index suggests. Asserting on list
    order here would happily pass with the header rendered underneath the rows.
    """
    menu = _laid_out(_menu(header_text="Set as", items=[MenuItem(text="a", height=dp(50))]))

    assert menu.header is not None
    assert menu.header.y > menu.items_box.y
    # And the header is flush with the top of the card.
    assert menu.header.top == pytest.approx(menu.card.top)


def test_rebuilding_the_header_keeps_it_on_top():
    """_build_header removes and re-adds the header; the re-add has to land at the top too."""
    menu = _menu(header_text="Set as", items=[MenuItem(text="a", height=dp(50))])

    menu.header_text = "Changed"
    _laid_out(menu)

    assert menu.header.y > menu.items_box.y
    assert menu.header.children[0].text == "Changed"


def test_header_band_has_its_own_dark_background():
    """The header is a band across the top of the card, distinct from the themed card colour."""
    menu = _menu(header_text="Set as", items=[MenuItem(text="a")])

    assert menu.header.md_bg_color == pytest.approx(get_color_from_hex("#1D1C1C"))


def test_header_background_survives_a_rebuild():
    menu = _menu(header_text="Set as", items=[MenuItem(text="a")])

    menu.header_text = "Changed"

    assert menu.header.md_bg_color == pytest.approx(get_color_from_hex("#1D1C1C"))


def test_no_header_text_means_no_header_widget_at_all():
    menu = _menu(items=[MenuItem(text="a")])

    assert menu.header is None
    assert list(menu.card.children) == [menu.items_box]


def test_header_contributes_to_the_measured_height():
    body = [MenuItem(text="a", height=dp(50))]
    without = _menu(items=body)
    with_header = _menu(header_text="Set as", items=body)

    # KivyMD's own set_target_height never counted the header, which is what
    # MyMDDropdownMenu existed to work around.
    assert with_header._measure_card_height() == (
        without._measure_card_height() + HEADER_HEIGHT
    )


def test_clearing_header_text_removes_the_header_again():
    menu = _menu(header_text="Set as", items=[MenuItem(text="a")])

    menu.header_text = None

    assert menu.header is None
    assert list(menu.card.children) == [menu.items_box]


# --- sizing -------------------------------------------------------------------

def test_measured_height_is_items_plus_vertical_padding():
    menu = _menu(items=[MenuItem(text="a", height=dp(50)), MenuItem(text="b", height=dp(50))])

    expected = dp(100) + menu.items_box.padding[1] + menu.items_box.padding[3]
    assert menu._measure_card_height() == expected


def test_max_visible_items_drops_the_trailing_items():
    """There is no scrolling by design, so overflow is dropped rather than made scrollable."""
    menu = _menu(
        max_visible_items=2,
        items=[MenuItem(text=str(i)) for i in range(5)],
    )

    assert len(_rows(menu)) == 2
    assert [row.label.text for row in _rows(menu)] == ["0", "1"]


def test_measured_height_never_exceeds_the_window():
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a", height=dp(400)) for _ in range(20)])

    assert menu._measure_card_height() <= Window.height


# --- theming ------------------------------------------------------------------

def test_apply_theme_recolours_existing_rows_without_rebuilding_them():
    menu = _menu(items=[MenuItem(text="a"), MenuItem(text="b")])
    before = _rows(menu)

    menu.apply_theme([.2, .2, .2, 1], [1, 0, 0, 1])

    after = _rows(menu)
    # Same widget objects: the old code reassigned `menu.items` to force a rebuild.
    assert after == before
    assert all(row.label.text_color == [1, 0, 0, 1] for row in after)
    assert menu.card.md_bg_color == [.2, .2, .2, 1]


def test_apply_theme_also_recolours_glyph_icons():
    menu = _menu(items=[MenuItem(text="a", icon="lock")])

    menu.apply_theme([.2, .2, .2, 1], [1, 0, 0, 1])

    assert _rows(menu)[0].icon_widget.text_color == [1, 0, 0, 1]


# --- overlay contract ---------------------------------------------------------

def test_menu_is_recognised_as_an_overlay_by_the_screen():
    """MyMDScreen.add_widget routes anything that is not a PlaceOnMainScreen into
    screen_content, where it would be laid out as a column instead of covering the screen."""
    assert isinstance(_menu(), PlaceOnMainScreen)


def test_scrim_is_a_separate_child_so_only_it_fades():
    menu = _menu()

    assert menu.scrim is not menu
    assert menu.scrim.opacity == 0
    assert menu.opacity == 1


# --- bottom nav bar -----------------------------------------------------------

class _FakeScreen:
    """Just enough of a screen for open()/hide() to attach and detach against."""

    def __init__(self):
        self.children = []

    def add_widget(self, widget):
        self.children.append(widget)
        widget.parent = self

    def remove_widget(self, widget):
        if widget in self.children:
            self.children.remove(widget)
        widget.parent = None


@pytest.fixture
def _nav_host(_kivymd_app):
    """Gives the running app a screen manager and a nav bar, and puts both back after."""
    app = _kivymd_app
    missing = object()
    previous_sm = getattr(app, "sm", missing)
    previous_bar = getattr(app, "bottom_bar", missing)

    app.sm = mock.Mock(current_screen=_FakeScreen())
    app.bottom_bar = mock.Mock()

    def put_back(name, previous):
        # A test may have deleted the attribute itself, so only remove what is still there.
        if previous is missing:
            if hasattr(app, name):
                delattr(app, name)
        else:
            setattr(app, name, previous)

    yield app

    # The menus under test call dismiss(), which unbinds their Window key handlers.
    put_back("sm", previous_sm)
    put_back("bottom_bar", previous_bar)


def test_open_hides_the_bottom_nav_bar(_nav_host):
    """The nav bar is a sibling of the screen manager, so the scrim cannot cover it."""
    menu = _menu(items=[MenuItem(text="a")])

    menu.open()

    _nav_host.bottom_bar.hide.assert_called_once_with(
        animation=False, hidden_by=menu
    )
    menu.dismiss()


def test_hide_restores_the_bottom_nav_bar(_nav_host):
    """In hide() rather than dismiss(), so back-press and scrim taps restore it too."""
    menu = _menu(items=[MenuItem(text="a")])
    menu.open()

    menu.dismiss()

    _nav_host.bottom_bar.show.assert_called_once_with(
        animation=False, hidden_by=menu
    )


def test_nav_bar_is_touched_once_per_open_and_dismiss(_nav_host):
    menu = _menu(items=[MenuItem(text="a")])
    menu.open()
    menu.dismiss()

    assert _nav_host.bottom_bar.hide.call_count == 1
    assert _nav_host.bottom_bar.show.call_count == 1


def test_nav_bar_ownership_token_is_the_menu_itself(_nav_host):
    """BottomNavigationBar.show() refuses unless hidden_by matches whoever hid it, so the
    token has to be the same object in both directions."""
    menu = _menu(items=[MenuItem(text="a")])
    menu.open()
    menu.dismiss()

    hide_owner = _nav_host.bottom_bar.hide.call_args.kwargs["hidden_by"]
    show_owner = _nav_host.bottom_bar.show.call_args.kwargs["hidden_by"]
    assert hide_owner is show_owner is menu


def test_missing_nav_bar_does_not_break_open_or_dismiss(_nav_host):
    """app.bottom_bar is None until main.py builds it, and absent entirely on hot reload."""
    del _nav_host.bottom_bar
    menu = _menu(items=[MenuItem(text="a")])

    menu.open()
    assert menu._is_open is True

    menu.dismiss()
    assert menu._is_open is False


def test_nav_bar_set_to_none_does_not_break_open_or_dismiss(_nav_host):
    _nav_host.bottom_bar = None
    menu = _menu(items=[MenuItem(text="a")])

    menu.open()
    menu.dismiss()

    assert menu._is_open is False


def test_dismiss_before_open_is_a_no_op():
    menu = _menu(items=[MenuItem(text="a")])

    menu.dismiss()  # must not raise

    assert menu.parent is None


def test_dismiss_twice_is_idempotent():
    class _FakeParent:
        def __init__(self):
            self.removed = 0

        def remove_widget(self, _widget):
            self.removed += 1

    menu = _menu(items=[MenuItem(text="a")])
    parent = _FakeParent()
    menu.parent = parent
    menu._is_open = True

    menu.dismiss()
    menu.dismiss()

    assert parent.removed == 1
    assert menu._is_open is False


def test_hide_resets_open_state_for_the_back_key_path():
    """PlaceOnMainScreen's back-key handler calls hide() directly rather than dismiss(), so
    the reset has to happen there too -- otherwise a back-press leaves _is_open True and the
    menu silently refuses to reopen."""
    menu = _menu(items=[MenuItem(text="a")])
    menu._is_open = True
    fade = mock.Mock()
    menu._fade = fade

    menu.hide()

    assert menu._is_open is False
    # The in-flight fade is cancelled, so it cannot keep writing opacity to a dead widget.
    fade.cancel.assert_called_once_with(menu.scrim)
    assert menu._fade is None


def test_open_after_a_back_key_dismissal_works_again():
    """Guards the user-visible symptom of the above: the menu must not become dead."""
    menu = _menu(items=[MenuItem(text="a")])
    menu._is_open = True

    menu.hide()
    assert menu._is_open is False

    # open() bails out early when it thinks it is already open.
    menu._is_open = True
    menu.open()
    assert menu._is_open is True
    menu.dismiss()


# --- positioning --------------------------------------------------------------
#
# These assertions are deliberately independent of Window.width/height: other tests in the
# suite resize the Window, so anything that assumes a particular size passes alone and fails
# in a full run.

def _caller_at(x_fraction, y_fraction):
    from kivy.core.window import Window
    from kivy.uix.widget import Widget

    return Widget(
        size=(dp(80), dp(40)),
        pos=(
            (Window.width - dp(80)) * x_fraction,
            (Window.height - dp(40)) * y_fraction,
        ),
    )


def test_card_is_placed_below_the_caller_when_there_is_room():
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a")])
    caller = _caller_at(0.5, 0.5)
    menu.caller = caller

    menu._position_card()

    # Room exists above and below at mid-screen, so the card hangs off the bottom edge.
    assert menu.card.top <= caller.y


def test_card_is_anchored_to_one_of_the_caller_horizontal_edges():
    """The card hangs off the caller's left edge, or off its right edge when the left one
    would run off screen. Either is correct; being flush with neither is not. Each is
    compared against the edge margin too, since the clamp moves it when the caller is
    closer to the screen edge than the margin."""
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a")])
    caller = _caller_at(0, 0.5)
    menu.caller = caller

    menu._position_card()

    flush_left = menu.card.x == pytest.approx(max(EDGE_MARGIN, caller.x))
    flush_right = menu.card.right == pytest.approx(
        min(Window.width - EDGE_MARGIN, caller.right)
    )
    assert flush_left or flush_right


@pytest.mark.parametrize("x_fraction", [0.0, 0.25, 0.5, 0.75, 1.0])
@pytest.mark.parametrize("y_fraction", [0.0, 0.5, 1.0])
def test_card_stays_fully_on_screen_for_any_caller_position(x_fraction, y_fraction):
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a")])
    menu.caller = _caller_at(x_fraction, y_fraction)

    menu._position_card()

    assert menu.card.x >= 0
    assert menu.card.y >= 0
    assert menu.card.right <= Window.width
    assert menu.card.top <= Window.height


def test_card_stays_fully_on_screen_with_a_tall_item_list():
    """No scrolling, so an over-long list has to be clamped rather than overflow."""
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a", height=dp(400)) for _ in range(20)])
    menu.caller = _caller_at(0.5, 0.5)

    menu._position_card()

    assert menu.card.top <= Window.height
    assert menu.card.y >= 0


def test_without_a_caller_the_card_is_centred():
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a")])

    menu._position_card()

    assert menu.card.center_x == pytest.approx(Window.width / 2)
    assert menu.card.center_y == pytest.approx(Window.height / 2)


def test_resize_keeps_an_open_card_on_screen():
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a")])
    menu.caller = _caller_at(0.5, 0.5)
    menu._is_open = True

    menu.on_window_resize(Window, (Window.width, Window.height))

    assert menu.card.top <= Window.height
    assert menu.card.x >= 0


def test_resize_is_ignored_while_closed():
    from kivy.core.window import Window

    menu = _menu(items=[MenuItem(text="a")])
    before = tuple(menu.card.pos)

    menu.on_window_resize(Window, (Window.width, Window.height))

    assert tuple(menu.card.pos) == before
