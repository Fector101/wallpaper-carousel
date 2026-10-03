from kivy.metrics import dp
from kivy.properties import AliasProperty, StringProperty
from kivy.uix.behaviors import ToggleButtonBehavior

from kivymd.uix.label import MDIcon

from utils.constants import theme_colors


class MyCheckbox(ToggleButtonBehavior, MDIcon):
    """A tappable "Don't show again" style checkbox.

    Kivy 3 replaced ``ToggleButtonBehavior.state`` (``"normal"``/``"down"``)
    with ``activated``, but KivyMD's ``MDCheckbox`` still drives everything off
    ``state``: its ``on_state`` sets ``active``, ``on_active`` writes ``state``
    back and ``update_icon()`` reads ``state``. A tap therefore flips
    ``activated``, which nothing consumes, and the widget looks inert. Since
    ``state`` no longer exists at all, ``MDCheckbox`` also raises an
    ``AttributeError`` on construction unless ``helper.patch_kivymd_switch_press_events()``
    stubs it out with a no-op - and that stub then swallows the writes too.

    This drives the same glyphs off ``activated`` instead, which is what Kivy 3
    actually toggles, and exposes ``active`` so call sites can read/set a
    selection without caring which Kivy version is underneath.
    """

    unchecked_icon = StringProperty("checkbox-blank-outline")
    checked_icon = StringProperty("checkbox-marked")

    def _get_active(self):
        return self.activated

    def _set_active(self, value):
        self.activated = bool(value)

    active = AliasProperty(
        _get_active, _set_active, bind=("activated",), cache=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Touch target stays at the 44dp Android minimum while the glyph keeps
        # its own size, so the box is easy to hit without looking oversized.
        self.size_hint = (None, None)
        self.size = (dp(44), dp(44))
        self.font_size = dp(22)
        self.theme_text_color = "Custom"
        self.bind(activated=self._sync_state)
        self._sync_state()

    def refresh_theme(self):
        """Re-reads ``theme_colors``, for callers bound to ``device_theme``."""
        self._sync_state()

    def _sync_state(self, *_):
        self.icon = self.checked_icon if self.activated else self.unchecked_icon
        self.text_color = (
            theme_colors.CHECKBOX_SELECTED
            if self.activated
            else theme_colors.CHECKBOX_UNSELECTED
        )