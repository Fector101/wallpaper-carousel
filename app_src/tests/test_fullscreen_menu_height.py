"""MyMDDropdownMenu sizing guards.

MDDropdownMenu.open() does `self.height = self.target_height`, so any `height`
passed to the constructor is discarded -- only the summed item heights survive.
MyMDDropdownMenu.set_target_height additionally folds header_cls.height into that
sum, because KivyMD's own set_target_height never counts the header.

The widget cannot be instantiated without a live Window (MDDropdownMenu.__init__
binds on_resize and reads self.ids.md_menu), so these tests allocate the instance
bare and drive only the attributes the override touches.
"""

import pytest
from kivy.metrics import dp
from kivymd.uix.menu import MDDropdownMenu

from ui.screens.full_screen import MyMDDropdownMenu


class _FakeMenu:
    """Stands in for the MDMenu RecycleView; only `.data` is read."""

    def __init__(self, data):
        self.data = data


def _make_menu(items, header_height):
    menu = MyMDDropdownMenu.__new__(MyMDDropdownMenu)
    menu._items = items
    menu.min_height = dp(48)
    menu.max_height = 0
    menu.target_height = 0
    # Keep the caller far below the window so the window-bounds clamp in the base
    # implementation is not what these tests are measuring.
    menu._start_coords = [0, 10 ** 6]

    class _Header:
        height = header_height

    menu.header_cls = _Header()
    menu.menu = _FakeMenu(items)
    return menu


def _raw_item_total(items):
    """What KivyMD's set_target_height computes: items only, no header."""
    return sum(item.get("height", dp(48)) for item in items)


# --- header is folded into the total -----------------------------------------

def test_header_height_is_added_to_item_total():
    menu = _make_menu([{"height": dp(56)}, {"height": dp(56)}], header_height=dp(48))

    menu.set_target_height()

    # 56 + 56 items, plus the 48 header KivyMD forgets to count.
    assert menu.target_height == dp(56) * 2 + dp(48)


def test_items_are_left_unmutated_afterwards():
    """The override borrows items[0] to carry the header; it must give it back."""
    items = [{"height": dp(56)}, {"height": dp(56)}]
    menu = _make_menu(items, header_height=dp(48))

    menu.set_target_height()

    assert [item["height"] for item in items] == [dp(56), dp(56)]


def test_raw_item_total_is_short_by_the_header():
    """Pins the bug being fixed: KivyMD's own sum under-counts by the header."""
    items = [{"height": dp(56)}, {"height": dp(56)}]
    menu = _make_menu(items, header_height=dp(48))

    menu.set_target_height()

    assert _raw_item_total(items) == dp(112)
    assert menu.target_height > _raw_item_total(items)


def test_taller_header_grows_the_card():
    items = [{"height": dp(56)}]
    small = _make_menu(list(items), header_height=dp(48))
    large = _make_menu(list(items), header_height=dp(120))

    small.set_target_height()
    large.set_target_height()

    assert large.target_height == small.target_height + (dp(120) - dp(48))


# --- passthrough cases -------------------------------------------------------

def test_without_a_header_the_total_is_just_the_items():
    menu = _make_menu([{"height": dp(56)}, {"height": dp(56)}], header_height=0)

    menu.set_target_height()

    assert menu.target_height == dp(112)


def test_header_of_zero_does_not_mutate_items():
    items = [{"height": dp(56)}]
    menu = _make_menu(items, header_height=0)

    menu.set_target_height()

    assert items[0]["height"] == dp(56)


def test_no_items_does_not_raise():
    menu = _make_menu([], header_height=dp(48))

    menu.set_target_height()

    assert menu.target_height == 0


def test_item_without_height_key_uses_min_height():
    """on_items defaults height to dp(48); the restore must not invent a key."""
    items = [{}]
    menu = _make_menu(items, header_height=dp(48))

    menu.set_target_height()

    # min_height (48) + header (48), and no "height" key left behind.
    assert menu.target_height == dp(48) * 2
    assert "height" not in items[0]


# --- mutation is undone even when the base implementation raises -------------

def test_item_height_restored_when_super_raises(monkeypatch):
    items = [{"height": dp(56)}, {"height": dp(56)}]
    menu = _make_menu(items, header_height=dp(48))

    def boom(_self):
        raise RuntimeError("base set_target_height failed")

    monkeypatch.setattr(MDDropdownMenu, "set_target_height", boom)

    with pytest.raises(RuntimeError):
        menu.set_target_height()

    assert [item["height"] for item in items] == [dp(56), dp(56)]


# --- the header flag that keeps content_header from collapsing ---------------

def test_header_must_have_size_hint_y_none():
    """menu.kv gives content_header `adaptive_size: True`, so its height is its
    minimum_size. Kivy's BoxLayout._get_minimum_size only folds a child's height
    in when size_hint_y is None; with size_hint_y=1 content_header collapses to 0
    and stretches the header to that 0, which silently zeroes header_cls.height.
    """
    import inspect

    from ui.screens import full_screen

    source = inspect.getsource(full_screen.FullscreenScreen.create_menu)
    header_block = source.split("header_cls=")[1]

    assert "size_hint_y=None" in header_block
    # The height that the header is collapsed to when the flag is missing.
    assert "height=dp(48)" in header_block