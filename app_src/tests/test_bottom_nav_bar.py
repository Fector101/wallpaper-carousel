"""BottomNavigationBar hide/show ownership and its one-frame deferral.

`show()` checks the ownership token immediately but only re-opens the drawer a frame later,
because the drawer is still mid-hide when it is called. That deferral used to be unowned: any
`hide()` landing in the same frame was silently undone by the queued callback, leaving the
navbar on screen while `self.hidden` said it was gone.

The deferral only applies to the animated path. With `animation=False` nothing is in flight
(`set_state` cancels any running open/close first), so the restore is applied inline -- see
`test_unanimated_restore_is_applied_inline_*` below.

The concrete symptom this fixes: in the gallery, tapping "enter multi-select mode" runs
DropdownMenu.dismiss() -> bottom_bar.show(hidden_by=menu) and then, in the same frame,
MultiSelectManager.show() -> bottom_bar.hide(hidden_by=manager). The queued show then landed
and the navbar reappeared over multi-select mode.

BottomNavigationBar cannot be instantiated under pytest -- MDApp aborts with "Unable to get a
Window, abort" when there is no window provider -- so these tests run the real hide()/show()
bodies against a stand-in that records the drawer state, with the module Clock swapped for a
fake scheduler. Ticking the real Clock is not an option either: other tests leave deferred
callbacks queued (DropdownMenu.open() schedules _place_and_fade) and they would all fire.
"""

import sys
from pathlib import Path

import pytest

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

from ui.widgets import buttons  # noqa: E402
from ui.widgets.buttons import BottomNavigationBar  # noqa: E402


class _FakeEvent:
    def __init__(self, callback):
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def run(self):
        if not self.cancelled:
            self.callback()


class _FakeClock:
    def __init__(self):
        self.events = []

    def schedule_once(self, callback, timeout=0):
        event = _FakeEvent(callback)
        self.events.append(event)
        return event

    def run_all(self):
        for event in list(self.events):
            event.run()


class _FakeButtonBox:
    pos_hint = {"center_x": .5, "center_y": .5}


class _Bar:
    """Carries exactly the state BottomNavigationBar.hide()/show() read and write."""

    def __init__(self):
        self.hidden = False
        self.hidden_by = None
        self.pending_show = None
        self.states = []
        self.button_box = _FakeButtonBox()

    def set_state(self, state, animation=True):
        self.states.append((state, animation))


@pytest.fixture
def bar(monkeypatch):
    """A stand-in navbar wired to a fake scheduler, plus the real hide/show under test."""
    fake_clock = _FakeClock()
    monkeypatch.setattr(buttons, "Clock", fake_clock)
    nav = _Bar()
    nav.hide = lambda *a, **k: BottomNavigationBar.hide(nav, *a, **k)
    nav.show = lambda *a, **k: BottomNavigationBar.show(nav, *a, **k)
    nav.clock = fake_clock
    return nav


# --- the regression -----------------------------------------------------------

def test_hide_cancels_a_restore_that_was_queued_earlier_in_the_same_frame(bar):
    """The gallery bug: dismiss() shows the bar, then the overlay hides it. The queued
    restore must not run, or the navbar lands back on screen in multi-select mode."""
    bar.hide(animation=False, hidden_by="menu")
    bar.show(hidden_by="menu")  # allowed: the menu really did hide it
    bar.hide(animation=False, hidden_by="manager")  # another owner, same frame

    bar.clock.run_all()

    assert bar.states[-1][0] == "close"
    assert bar.button_box.pos_hint == {"center_x": .5, "y": -1}
    assert bar.hidden is True


def test_a_cancelled_restore_never_touches_the_drawer(bar):
    bar.hide(animation=False, hidden_by="menu")
    bar.show(hidden_by="menu")
    queued = bar.clock.events[-1]
    bar.hide(animation=False, hidden_by="manager")

    assert queued.cancelled is True
    assert bar.pending_show is None


def test_hide_claims_ownership_when_the_bar_was_restored_in_the_same_frame(bar):
    """The bar is visible again by the time the second hide arrives (show() clears self.hidden
    immediately), so the second owner legitimately takes over -- and the queued restore must
    still not fire behind its back."""
    bar.hide(animation=False, hidden_by="menu")
    bar.show(hidden_by="menu")
    queued = bar.clock.events[-1]

    bar.hide(animation=False, hidden_by="pic")

    assert queued.cancelled is True
    assert bar.hidden_by == "pic"
    bar.clock.run_all()
    assert bar.states[-1][0] == "close"


# --- the deferral itself still works ------------------------------------------
# These use the animated path (the default). The un-animated path applies the restore inline,
# so it has no queued callback to cancel -- see the next section.

def test_show_defers_the_animated_restore_instead_of_applying_it_inline(bar):
    bar.hide(animation=False, hidden_by="menu")

    bar.show(hidden_by="menu")

    # Deferred: the drawer was still closing when show() was called.
    assert bar.states[-1][0] == "close"
    assert bar.pending_show is not None
    assert bar.hidden is False


def test_queued_restore_applies_when_nothing_hides_after_it(bar):
    bar.hide(animation=False, hidden_by="menu")
    bar.show(hidden_by="menu")

    bar.clock.run_all()

    assert bar.states[-1][0] == "open"
    assert bar.button_box.pos_hint == {"center_x": .5, "center_y": .5}
    assert bar.hidden is False


def test_pending_handle_is_cleared_once_the_restore_has_run(bar):
    bar.hide(animation=False, hidden_by="menu")
    bar.show(hidden_by="menu")

    bar.clock.run_all()

    assert bar.pending_show is None


def test_restored_bar_can_be_hidden_again_normally(bar):
    """The everyday path, to prove the cancel did not break ordinary use."""
    bar.hide(animation=False, hidden_by="menu")
    bar.show(hidden_by="menu")
    bar.clock.run_all()

    bar.hide(animation=False, hidden_by="manager")

    assert bar.hidden is True
    assert bar.hidden_by == "manager"
    assert bar.button_box.pos_hint == {"center_x": .5, "y": -1}


# --- the un-animated path applies inline --------------------------------------

def test_unanimated_restore_is_applied_inline(bar):
    """Nothing is animating, so there is no transition to wait for.

    Deferring it anyway left the caller (e.g. DropdownMenu.hide(), which removes the scrim in
    the same tick) showing a screen with no nav bar for one frame.
    """
    bar.hide(animation=False, hidden_by="menu")

    bar.show(animation=False, hidden_by="menu")

    assert bar.states[-1] == ("open", False)
    assert bar.button_box.pos_hint == {"center_x": .5, "center_y": .5}
    assert bar.hidden is False


def test_unanimated_restore_queues_nothing(bar):
    bar.hide(animation=False, hidden_by="menu")

    bar.show(animation=False, hidden_by="menu")

    assert bar.pending_show is None
    assert bar.clock.events == []


def test_unanimated_restore_can_still_be_undone_by_a_hide_in_the_same_frame(bar):
    """The gallery case again, on the path the app actually uses.

    dismiss() shows the bar and the overlay hides it in the same frame. With the restore
    already applied there is no queued callback left to fire, so the later hide simply wins.
    """
    bar.hide(animation=False, hidden_by="menu")
    bar.show(animation=False, hidden_by="menu")

    bar.hide(animation=False, hidden_by="manager")
    bar.clock.run_all()

    assert bar.states[-1][0] == "close"
    assert bar.button_box.pos_hint == {"center_x": .5, "y": -1}
    assert bar.hidden is True


# --- ownership rules are untouched --------------------------------------------

def test_show_is_refused_for_a_different_owner_and_queues_nothing(bar):
    bar.hide(animation=False, hidden_by="manager")

    bar.show(animation=False, hidden_by="menu")

    assert bar.pending_show is None
    assert bar.clock.events == []
    assert bar.hidden is True


def test_hide_is_a_no_op_when_the_bar_is_already_hidden(bar):
    bar.hide(animation=False, hidden_by="manager")

    bar.hide(animation=False, hidden_by="menu")

    assert bar.hidden_by == "manager"
    assert bar.hidden is True


def test_show_is_a_no_op_when_the_bar_is_already_visible(bar):
    bar.show(animation=False, hidden_by="menu")

    assert bar.clock.events == []
    assert bar.pending_show is None
