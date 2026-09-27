import pytest
from kivy.properties import NumericProperty
from kivy.uix.widget import Widget
from kivymd.uix.behaviors.hover_behavior import HoverBehavior
from kivymd.uix.behaviors.state_layer_behavior import StateLayerBehavior

from utils import helper


class HoverRestoreRepro(StateLayerBehavior, Widget):
    # KivyMD's state layer stores the shadow backup on StateLayerBehavior, so
    # a widget that resolves the backup there while owning the
    # `shadow_softness` NumericProperty hits the broken restore path.
    shadow_softness = NumericProperty(0.0)


@pytest.fixture(autouse=True)
def restore_kivymd_hover_state():
    shadow_softness_backup = StateLayerBehavior._shadow_softness
    allow_hover = HoverBehavior.allow_hover
    yield
    StateLayerBehavior._shadow_softness = shadow_softness_backup
    HoverBehavior.allow_hover = allow_hover


def test_bare_on_leave_raises_with_list_backup(monkeypatch):
    # HoverBehavior sets `hovering = True` before the visibility check, so
    # on_enter can be skipped and the next motion event dispatches a bare
    # on_leave. The backup then still is StateLayerBehavior's [0, 0] default
    # and lands in the shadow_softness NumericProperty.
    monkeypatch.setattr("kivy.utils.platform", "linux")
    StateLayerBehavior._shadow_softness = [0, 0]
    widget = HoverRestoreRepro()

    with pytest.raises(TypeError, match="Expected str, got int"):
        widget.dispatch("on_leave")


def test_hover_patch_normalizes_shadow_softness_backup(monkeypatch):
    monkeypatch.setattr("kivy.utils.platform", "android")
    helper.patch_kivymd_hover_on_touch()

    assert StateLayerBehavior._shadow_softness == 0

    # The frame from the device log: the restore has to put a number into the
    # shadow_softness NumericProperty, not the [0, 0] backup.
    widget = HoverRestoreRepro()
    widget._restore_properties()

    assert widget.shadow_softness == 0


@pytest.mark.parametrize("touch_platform", ["android", "ios"])
def test_hover_disabled_on_touch_platforms(monkeypatch, touch_platform):
    monkeypatch.setattr("kivy.utils.platform", touch_platform)
    helper.patch_kivymd_hover_on_touch()

    assert HoverRestoreRepro().allow_hover is False


def test_hover_untouched_on_desktop(monkeypatch):
    monkeypatch.setattr("kivy.utils.platform", "linux")
    helper.patch_kivymd_hover_on_touch()

    assert StateLayerBehavior._shadow_softness == [0, 0]
    assert HoverRestoreRepro().allow_hover is True
