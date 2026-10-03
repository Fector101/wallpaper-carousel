"""Guards for canvas state that must not escape its widget.

A Kivy canvas is a flat instruction stream, not a tree with per-widget scoping. `Color`,
`Rotate`, `Scale` and friends change GL state for **everything drawn after them in the
frame**, and Kivy only brackets a widget's own canvas with `PushMatrix`/`PopMatrix` when
that widget class has a kv rule saying so - true for `<Scatter>` and `<RelativeLayout>`
(`kivy/data/style.kv`), false for plain `Widget`s and for anything built purely in Python.

The symptom that made this file necessary: the preview's "Loading HD" spinner drew its arc
with a bare `Rotate`, so the badge's own label and - because the how-to card is drawn later
in the frame - the card itself visibly rotated along with the spinner. `LoadingLayout` uses
the same widget, so the full-screen loading overlay had been tilting the whole UI too.

Hence the rule these tests enforce: **if you add a state-changing instruction to a canvas,
you push/pop it yourself.** The pattern already in the app is `canvas.before: PushMatrix()` …
`canvas.after: PopMatrix()` (`camera_screen.CameraScreen._apply_transform`,
`welcome_screen.RotatedLayout`); `SpinningArcWidget` now does the same.

Colour has to be restored by hand because this vendored Kivy 3.0 has no `PushColor`/
`PopColor` at all (not exported from `kivy.graphics`, and absent from the whole of
`app_src/kivy`) - the arc, the scatter's background and the border layout each leave an
explicit `Color(1, 1, 1, 1)` behind, which is Kivy's default ambient colour and what
`kivy/uix/effectwidget.py` does after its own transform.

Rendering cannot be asserted here: `kivy.graphics.fbo` only exports `Fbo` (not `FBO`), and
`Fbo.pixels` reads back all zeros in this environment, so there is no pixel-level test. The
instruction order is the proxy, and it is enough to prove containment - a `Rotate` that is
pushed and popped cannot rotate anything drawn after it.
"""

import sys
from pathlib import Path

import pytest

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

from kivy.properties import StringProperty  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402

from ui.screens import preview_screen as preview_module  # noqa: E402
from ui.widgets import layouts as layouts_module  # noqa: E402
from ui.widgets.layouts import (  # noqa: E402
    BorderMDRelativeLayout, LoadingLayout, SpinningArcWidget,
)
from utils.constants import theme_colors  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _kivymd_app():
    """KivyMD refuses to instantiate any widget without a running MDApp."""
    from kivy.app import App
    from kivymd.app import MDApp

    class _App(MDApp):
        device_theme = StringProperty("dark")

        def build(self):
            return None

    app = _App()
    previous = App._running_app
    App._running_app = app
    yield app
    App._running_app = previous


def _types(group):
    return [type(instruction).__name__ for instruction in group.children]


def _first_index(names, name):
    assert name in names, f"{name} missing from {names}"
    return names.index(name)


def _last_color(group):
    colors = [i for i in group.children if type(i).__name__ == "Color"]
    assert colors, "expected a Color instruction"
    return colors[-1]


# --- the spinner: the rotation must stay inside the spinner -------------------------

def test_the_spinner_pushes_a_matrix_before_it_rotates():
    """`PushMatrix` has to come before both the `Rotate` and the `Line`, otherwise the
    arc itself is drawn rotated by whatever the matrix already was."""
    before = _types(SpinningArcWidget().canvas.before)

    assert _first_index(before, "PushMatrix") < _first_index(before, "Rotate")
    assert _first_index(before, "PushMatrix") < _first_index(before, "Line")


def test_the_spinner_pops_the_matrix_after_the_arc():
    """Without this `PopMatrix` the rotation stays active for the rest of the frame, which
    is what made the badge's label and the how-to card spin with the arc."""
    after = _types(SpinningArcWidget().canvas.after)

    assert "PopMatrix" in after


def test_the_spinner_still_rotates():
    """The bracket must not have broken the thing it was added for."""
    arc = SpinningArcWidget()
    host = Widget()
    host.add_widget(arc)

    arc.update_arc(0.016)

    assert arc.rotation.angle == 5


def test_the_spinner_restores_the_colour_it_sets():
    """There is no PushColor/PopColor in this kivy, so the arc's colour would stay ambient
    for everything drawn after it. Kivy's default is opaque white."""
    arc = SpinningArcWidget()

    assert list(arc.color_instr.rgba) == list(theme_colors.PRIMARY)
    assert list(_last_color(arc.canvas.after).rgba) == [1.0, 1.0, 1.0, 1.0]
    assert _first_index(_types(arc.canvas.after), "PopMatrix") < _types(arc.canvas.after).index(
        "Color"
    )


def test_the_spinner_keeps_its_instructions_in_the_bracketed_groups():
    """The bare `canvas` has no scoping of its own, so anything added there leaks. This is
    the regression that started all of it."""
    arc = SpinningArcWidget()

    managed = {"PushMatrix", "PopMatrix", "Color", "Rotate", "Line"}
    assert not managed & set(_types(arc.canvas))


def test_the_loading_overlay_uses_the_same_bracketed_spinner():
    """`LoadingLayout` is the other consumer, and it used to tilt the entire UI for the same
    reason. It must not be able to go back to a second, unbracketed spinner."""
    layout = LoadingLayout()

    assert isinstance(layout.spinner, SpinningArcWidget)
    assert "PopMatrix" in _types(layout.spinner.canvas.after)


def test_repainting_the_arc_still_works_after_the_move():
    """`set_color` reaches into the instruction that moved into `canvas.before`."""
    arc = SpinningArcWidget()

    arc.set_color([1, 0, 0, 1])

    assert list(arc.color_instr.rgba) == [1, 0, 0, 1]
    assert arc.color_instr in arc.canvas.before.children


def test_moving_the_arc_still_follows_the_widget():
    """`_update_origin` rewrites the rotation origin and the circle geometry; that has to
    keep working against the instructions in their new group."""
    arc = SpinningArcWidget(size=(40, 40))
    arc.pos = (10, 20)

    # `Rotate.origin` is a 3-tuple, `center` a 2-tuple.
    assert tuple(arc.rotation.origin[:2]) == tuple(arc.center)
    assert arc._arc_tuple == (arc.center_x, arc.center_y, arc.radius, 0, 270)


# --- other colour leaks ---------------------------------------------------------------

def test_the_scatter_background_does_not_stay_the_active_colour():
    """`MyScatter` paints an opaque #1A1B1B backdrop in `canvas.before` with nothing to put
    the colour back, so it stayed ambient for the rest of the frame."""
    scatter = preview_module.MyScatter()

    assert list(_last_color(scatter.canvas.before).rgba) == [1.0, 1.0, 1.0, 1.0]


def test_the_border_layout_does_not_stay_the_active_colour():
    """Same leak in `canvas.after`, which is drawn after this widget's children - so it hit
    whatever the next widget drew. (The widget has no users yet; this keeps it from being a
    trap.)"""
    border = BorderMDRelativeLayout()

    assert list(_last_color(border.canvas.after).rgba) == [1.0, 1.0, 1.0, 1.0]


def test_the_arc_module_still_exports_what_it_draws_with():
    """A cheap guard against someone "simplifying" the imports back to a bare canvas."""
    for name in ("Color", "Line", "Rotate", "PushMatrix", "PopMatrix"):
        assert hasattr(layouts_module, name), name