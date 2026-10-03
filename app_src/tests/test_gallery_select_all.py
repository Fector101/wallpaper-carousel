"""The multi-select top bar's select all button derives its state from the selection.

It used to flip a stored `select_all_` flag and nothing else, so the flag went
stale the moment anything was selected outside that button -- by tapping tiles, or
by a date group's own "Select all". A stale flag does not fail loudly, it inverts:
tap the button after hand-deselecting one tile and it cleared the whole selection
instead of re-selecting everything, which is the opposite of what the icon implies.

These tests run the real method bodies against a stand-in. `MultiselectTop` cannot be
built under pytest -- its `__init__` needs a live MDApp/window -- so the widget is
replaced by an object carrying only the attributes these methods read and write, and
the `isinstance` filters are satisfied with MagicMock stand-ins whose `__class__` is
the real widget class.

Only the tab on screen is compared. `select_all()` selects the visible tab, so a
total taken across every tab could never be reached and the button would report
"all selected" never.

The button signals state through its colour alone -- the glyph is always
playlist-check -- so these tests assert on `icon_color` and hold the icon still.
"""

import sys
from pathlib import Path
from unittest import mock

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

from ui.screens.gallery_screen import (  # noqa: E402
    MultiselectTop,
    DateGroupLayout,
    PreviewImage,
)
from utils.constants import theme_colors  # noqa: E402


class _Group(mock.MagicMock):
    """A DateGroupLayout stand-in whose unselected counter is read live.

    In the app the counter is a cache kept current by the tile's `selected` binding.
    That binding cannot fire without real widgets, so deriving the counter on read
    keeps it correct whichever path changed a tile -- a finger, `select_all()`, or
    `clear_selection()` -- instead of only the paths a test remembers to notify.
    """

    _preview_children = ()

    def __getattr__(self, name):
        if name == "count_of_items_not_selected":
            return sum(1 for child in self._preview_children if not child.selected)
        return super().__getattr__(name)

    def _clear_selection(self):
        for child in self._preview_children:
            child.selected = False


class _Button:
    """Stand-in for the MDIconButton: only holds the two props being written."""

    def __init__(self):
        self.icon = "playlist-check"
        self.icon_color = None


class _Label:
    text = ""


class _FakeTop:
    """Carries exactly what MultiselectTop's selection methods read and write."""

    _current_tab_selection = MultiselectTop._current_tab_selection
    refresh_select_all_state = MultiselectTop.refresh_select_all_state
    toggle_select_all = MultiselectTop.toggle_select_all
    update_selection_count = MultiselectTop.update_selection_count
    get_selected_items_count = MultiselectTop.get_selected_items_count
    select_all = MultiselectTop.select_all
    deselect_all = MultiselectTop.deselect_all

    def __init__(self, tabs, current_tab):
        self.gallery_screen = mock.MagicMock(current_tab=current_tab, tab_instances=tabs)
        self.toggle_select_all_btn = _Button()
        self.title_widget = _Label()
        self.inactive_icon_color = [.5, .5, .5, 1]
        self.all_selected = False


def _preview(selected=False):
    preview = mock.MagicMock()
    preview.__class__ = PreviewImage
    preview.selected = selected
    return preview


def _group(*children, stray=False):
    if stray:
        children = children + (mock.MagicMock(),)
    group = _Group()
    group.__class__ = DateGroupLayout
    group._preview_children = children
    group.images_container.children = list(children)
    group.clear_selection.side_effect = group._clear_selection
    return group


def _top_with_group(*children, stray=False, other_tab=None):
    group = _group(*children, stray=stray)
    tabs = {"Day": {"g1": group, "title": "day", "widget": None, "wallpapers": []}}
    if other_tab is not None:
        tabs["Noon"] = other_tab
    return _FakeTop(tabs, "Day"), group


def test_a_partially_selected_tab_is_not_reported_as_all_selected():
    top, _ = _top_with_group(_preview(), _preview(), _preview())

    top.refresh_select_all_state()

    assert top.all_selected is False
    assert top.toggle_select_all_btn.icon_color == top.inactive_icon_color
    assert top.toggle_select_all_btn.icon_color != theme_colors.CHECKBOX_SELECTED


def test_the_icon_is_accented_when_everything_in_the_tab_is_selected():
    top, _ = _top_with_group(_preview(True), _preview(True))

    top.refresh_select_all_state()

    assert top.all_selected is True
    assert top.toggle_select_all_btn.icon_color == theme_colors.CHECKBOX_SELECTED


def test_tapping_a_partially_selected_tab_selects_the_rest():
    tiles = [_preview(), _preview(), _preview(), _preview()]
    top, _ = _top_with_group(*tiles)
    tiles[0].selected = True
    tiles[1].selected = True
    top.update_selection_count()

    top.toggle_select_all()

    assert [tile.selected for tile in tiles] == [True] * 4
    assert top.all_selected is True
    assert top.toggle_select_all_btn.icon_color == theme_colors.CHECKBOX_SELECTED
    assert top.title_widget.text == "4 items selected"


def test_tapping_a_fully_selected_tab_deselects_everything():
    tiles = [_preview(), _preview()]
    top, _ = _top_with_group(*tiles)

    top.toggle_select_all()
    assert all(tile.selected for tile in tiles)

    top.toggle_select_all()

    assert [tile.selected for tile in tiles] == [False] * 2
    assert top.all_selected is False
    assert top.toggle_select_all_btn.icon_color == top.inactive_icon_color
    assert top.title_widget.text == "0 items selected"


def test_hand_deselecting_one_tile_makes_the_next_tap_select_all_again():
    """The regression. With a stored flag, deselecting one tile by hand left the
    flag True, so this tap cleared everything instead of re-selecting."""
    tiles = [_preview(), _preview(), _preview()]
    group = _group(*tiles)
    top = _FakeTop({"Day": {"g1": group, "title": "day", "widget": None, "wallpapers": []}}, "Day")
    top.toggle_select_all()
    assert all(tile.selected for tile in tiles)

    tiles[2].selected = False
    top.update_selection_count()
    assert top.all_selected is False
    assert top.toggle_select_all_btn.icon_color == top.inactive_icon_color

    top.toggle_select_all()

    assert [tile.selected for tile in tiles] == [True] * 3
    assert top.all_selected is True


def test_a_group_level_select_all_updates_the_top_button():
    tiles = [_preview(), _preview()]
    group = _group(*tiles)
    top = _FakeTop({"Day": {"g1": group, "title": "day", "widget": None, "wallpapers": []}}, "Day")

    # DateGroupLayout._toggle_select_all_group, then the header count refresh
    for tile in tiles:
        tile.selected = True
    top.update_selection_count()

    assert top.all_selected is True
    assert top.toggle_select_all_btn.icon_color == theme_colors.CHECKBOX_SELECTED


def test_the_icon_never_changes_only_its_colour_does():
    """The affordance is the colour alone, so swapping the glyph would be a
    second, unrelated state signal."""
    top, _ = _top_with_group(_preview())
    top.refresh_select_all_state()
    assert top.toggle_select_all_btn.icon == "playlist-check"

    tiles = [_preview()]
    top, _ = _top_with_group(*tiles)
    tiles[0].selected = True
    top.refresh_select_all_state()
    assert top.all_selected is True
    assert top.toggle_select_all_btn.icon == "playlist-check"


def test_an_empty_group_is_not_reported_as_all_selected():
    top, _ = _top_with_group()

    top.refresh_select_all_state()

    assert top.all_selected is False
    assert top.toggle_select_all_btn.icon_color == top.inactive_icon_color


def test_only_the_tab_on_screen_is_compared():
    """Select all is tab scoped, so an untouched tab must not hold the button in
    its 'select' state forever."""
    visible = _group(_preview(True), _preview(True))
    other = _group(_preview(), _preview())
    top = _FakeTop({"Day": {"g1": visible}, "Noon": {"g1": other}}, "Day")

    top.refresh_select_all_state()

    assert top.all_selected is True


def test_a_stray_non_preview_child_does_not_hold_the_button_in_select_state():
    top, _ = _top_with_group(_preview(True), stray=True)

    top.refresh_select_all_state()

    assert top.all_selected is True


def test_no_gallery_screen_yet_is_not_reported_as_all_selected():
    top = _FakeTop({}, "Day")
    top.gallery_screen = None

    top.refresh_select_all_state()

    assert top.all_selected is False
    assert top.toggle_select_all_btn.icon_color == top.inactive_icon_color