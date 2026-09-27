import inspect

from kivymd.uix.selectioncontrol import MDSwitch

from utils import helper


def test_switch_press_handlers_tolerate_missing_touch():
    # KivyMD re-dispatches on_press/on_release from the switch thumb without a
    # touch, which Kivy 3.0's ButtonBehavior rejects.
    helper.patch_kivymd_switch_press_events()

    for handler in (MDSwitch.on_press, MDSwitch.on_release):
        inspect.signature(handler).bind(MDSwitch)
