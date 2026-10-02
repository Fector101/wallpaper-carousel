# TODO: Remove this on new kivyMD version, also check if list item can set custom icon or just remove custom path icon and add font awesome ttf
"""Hand-rolled dropdown menu.

Replaces KivyMD's `MDDropdownMenu` in this app. KivyMD builds its item list out of a
`RecycleView` (`MDMenu`, declared in `kivymd/uix/menu/menu.kv`, defined as
`class MDMenu(RecycleView)` in `menu.py`), which means item widgets get *reused* across
items and the adapter only ever writes the keys present in each item's dict
(`kivy/uix/recycleview/views.py:292-294`). A key a later item omits therefore keeps whatever
value the previous item left behind, and the view cache is a process-wide global keyed by
widget class alone (`views.py:33`), so two unrelated menus share one pool of widgets.

Nothing here recycles, so every row is built once and keeps only its own state. Item data is
a `MenuItem` instance rather than a dict, so there is no dict/widget key syncing at all.

Everything is constructed in Python, so there is no companion .kv file.

Usage:

    menu = DropdownMenu(
        caller=self.some_button,
        items=[
            MenuItem(text="Home Screen", icon_image="/path/home.png", on_release=cb),
            MenuItem(text="Lock Screen", icon="lock", on_release=cb),
        ],
        header_text="Set as",
    )
    menu.open()
"""

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.behaviors import RectangularRippleBehavior
from kivymd.uix.divider import MDDivider
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel, MDIcon

from ui.widgets.layouts import PlaceOnMainScreen
from utils.logger import app_logger

# Icon slot is a fixed width so rows stay aligned whether they carry a glyph, an image, or
# nothing at all.
ICON_SLOT_WIDTH = dp(32)
ICON_SIZE = sp(22)
DIVIDER_HEIGHT = dp(1)
DIVIDER_COLOR = [1, 1, 1, .12]
ITEM_PADDING = (dp(12), dp(4), dp(12), dp(4))
HEADER_HEIGHT = dp(40)
# Dark enough to read as a header band against the themed card, and it stays legible against
# both the light and the dark card colour.
HEADER_BG_COLOR = get_color_from_hex("#1D1C1C")
# The card's own width. Independent of the caller, which is only a positioning anchor.
CARD_WIDTH = dp(240)
CARD_RADIUS = dp(12)
SCRIM_COLOR = [0, 0, 0, 0.6]
SCRIM_FADE_DURATION = 0.15
# Gap kept between the card and the edge of the window when the card has to be pushed in.
EDGE_MARGIN = dp(8)
# Gap between the caller and the card.
CALLER_GAP = dp(4)


class MenuItem:
    """A single dropdown row.

    Not a dict on purpose: a dict has to be copied key-by-key onto a widget, and that copy is
    exactly how values leaked between recycled rows. The widget is constructed from this once
    and never rebuilt, so `icon` (a Material Design Icons *name*) and `icon_image` (a file
    path) can be separate fields instead of overloading one.

    `divider=None` means "use the menu's `show_dividers`"; True/False override it.
    """

    def __init__(
        self,
        text,
        on_release=None,
        icon=None,
        icon_image=None,
        icon_image_light=None,
        divider=None,
        height=dp(56),
        text_color=None,
        icon_color=None,
    ):
        self.text = text
        self.on_release = on_release
        self.icon = icon
        self.icon_image = icon_image
        # Image files are not tinted, so a dark glyph vanishes on the light card. Give the
        # row the light-theme variant and it is swapped when the theme changes.
        self.icon_image_light = icon_image_light
        self.divider = divider
        self.height = height
        self.text_color = text_color
        self.icon_color = icon_color


class DropdownItemWidget(RectangularRippleBehavior, ButtonBehavior, MDBoxLayout):
    """One row: optional icon, label, and a divider underneath only if wanted.

    Vertical, because the divider belongs under the whole row rather than between the icon and
    the label; the icon and label live together in an inner horizontal box.

    The icon slot is built once in `__init__` -- an `MDIcon` for a glyph name, an `Image` for
    a file path -- so there is no runtime switching between the two and no property that has
    to be re-read when this widget is handed to a different row.
    """

    def __init__(self, item, show_dividers=False, on_release_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self._on_release_callback = on_release_callback
        self.orientation = "vertical"
        self.size_hint_y = None
        self.md_bg_color = [0, 0, 0, 0]

        self.wants_divider = item.divider is True or (
            item.divider is None and show_dividers
        )
        self.height = item.height + (DIVIDER_HEIGHT if self.wants_divider else 0)

        content = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=item.height,
        )
        self.icon_widget = self._build_icon(item)
        content.add_widget(
            MDBoxLayout(
                self.icon_widget,
                size_hint_x=None,
                width=ICON_SLOT_WIDTH,
                pos_hint={"center_y": .5},
            )
        )
        self.label = MDLabel(
            text=item.text,
            shorten=True,
            shorten_from="right",
            pos_hint={"center_y": .44},
            theme_text_color="Custom",
            text_color=item.text_color or [1, 1, 1, 1],
            theme_font_size="Custom",
            font_size=sp(15),
        )
        content.add_widget(self.label)
        # Added first, so in this vertical box it lands at the top and the divider added
        # after it ends up underneath -- see _add_header for the ordering rule.
        self.add_widget(content)

        # A divider that is not wanted is never created, rather than created and then found
        # again by walking the children list to zero its height.
        if self.wants_divider:
            self.add_widget(
                MDDivider(
                    # MDDivider takes a plain `color`, not `md_bg_color`; `color` is only
                    # honoured when theme_divider_color is "Custom".
                    color=DIVIDER_COLOR,
                    theme_divider_color="Custom",
                    size_hint_y=None,
                    height=DIVIDER_HEIGHT,
                )
            )

    def _build_icon(self, item):
        """Picks the icon slot widget once, from the item."""
        common = dict(
            size_hint_x=None,
            width=ICON_SIZE,
            size_hint_y=None,
            height=ICON_SIZE,
            pos_hint={"center_x": .5, "center_y": .5},
        )
        if item.icon_image:
            # fit_mode rather than the deprecated keep_ratio/allow_stretch pair.
            return Image(source=item.icon_image, fit_mode="contain", **common)
        if item.icon:
            return MDIcon(
                icon=item.icon,
                theme_text_color="Custom",
                text_color=item.icon_color or item.text_color or [1, 1, 1, 1],
                **common,
            )
        # Keeps the row's layout identical whether or not it has an icon.
        return MDBoxLayout()

    def on_release(self, *_args):
        # ButtonBehavior.on_touch_up dispatches this with the touch
        # (kivy/uix/behaviors/button.py:409), so the handler has to take it.
        # Dismiss first, so a callback that navigates somewhere does not race the teardown.
        if self._on_release_callback:
            self._on_release_callback()
        if self.item.on_release:
            self.item.on_release()

    def recolor(self, text_color, icon_color=None, theme=None):
        self.label.text_color = text_color
        if isinstance(self.icon_widget, MDIcon):
            self.icon_widget.text_color = icon_color or text_color
        elif isinstance(self.icon_widget, Image) and theme is not None:
            src = self.item.icon_image_light if theme == "light" and self.item.icon_image_light else self.item.icon_image
            if src and self.icon_widget.source != src:
                self.icon_widget.source = src


class DropdownMenu(MDFloatLayout, PlaceOnMainScreen):
    """A caller-anchored dropdown with a scrim behind it.

    Dismisses on the Android hardware back button, on ESC, on a tap outside the card, and via
    `dismiss()`.

    Inherits `PlaceOnMainScreen` for two reasons. It is how `MyMDScreen.add_widget`
    (`ui/widgets/layouts.py:330-333`) recognises an overlay -- anything else gets pushed into
    `screen_content` and laid out as a column instead of covering the screen. And it already
    implements the back-key handling this app uses everywhere else, including the debounce
    that copes with Android's spurious duplicate key_down events, which a naive handler
    cannot.
    """

    items = ListProperty([])
    """List of `MenuItem` instances."""

    # allownone is explicit on every ObjectProperty below: Kivy only permits assigning
    # None when it is set, so a bare ObjectProperty(None) merely *starts* as None and
    # raises the moment someone assigns None back.
    caller = ObjectProperty(None, allownone=True)
    """Widget the card is positioned against."""

    card_bg_color = ListProperty([.15, .15, .15, 1])
    header_bg_color = ListProperty(HEADER_BG_COLOR)
    text_color = ListProperty([1, 1, 1, 1])
    icon_color = ListProperty([1, 1, 1, 1])
    header_text_color = ListProperty([1, 1, 1, 1])
    scrim_color = ListProperty(SCRIM_COLOR)
    show_dividers = BooleanProperty(False)
    """Menu-wide default; a `MenuItem.divider` of True/False overrides it."""
    card_width = NumericProperty(CARD_WIDTH)
    header_text = ObjectProperty(None, allownone=True)
    """Header label text. None/"" means no header at all."""
    max_visible_items = NumericProperty(0)
    """Optional cap on how many items are shown. 0 means no cap. Content that would push the
    card past the window is dropped from the end rather than made scrollable."""
    header = ObjectProperty(None, allownone=True)
    """The header row widget, or None when there is no header."""

    # Class-level defaults, not set in __init__: Kivy dispatches on_<prop> for keyword
    # arguments during super().__init__(), so these handlers can run before any instance
    # attribute exists.
    _built = False
    _is_open = False
    _fade = None

    def __init__(self, items=None, caller=None, header_text=None, **kwargs):
        # The root itself is transparent: the scrim is a child of its own so the fade can be
        # applied to the scrim alone and the card stays fully opaque.
        kwargs.setdefault("md_bg_color", [0, 0, 0, 0])
        super().__init__(**kwargs)
        PlaceOnMainScreen.__init__(self)
        self.opacity = 1

        self.scrim = MDFloatLayout(
            size_hint=(1, 1),
            md_bg_color=self.scrim_color,
        )
        self.scrim.opacity = 0
        self.add_widget(self.scrim)

        self.card = MDBoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            width=self.card_width,
            md_bg_color=self.card_bg_color,
            radius=CARD_RADIUS,
        )
        self.add_widget(self.card)
        self.items_box = MDBoxLayout(
            orientation="vertical",
            # Without this the box keeps the default height of 100 regardless of how many
            # rows it holds, and the card lays the header out on top of the last row.
            # adaptive_height ties it to minimum_height, which is the same content +
            # padding sum that _measure_card_height() works out by hand.
            adaptive_height=True,
            size_hint_y=None,
            padding=ITEM_PADDING,
        )
        self.card.add_widget(self.items_box)

        # Assigning these triggers on_items / on_header_text / on_caller; all of them bail out
        # until _built is set, so the widget tree is built exactly once below.
        self.caller = caller
        self.header_text = header_text
        self.items = list(items or [])
        self._build_header()
        self._built = True
        self._build_items()

    # --- items ------------------------------------------------------------------

    def _build_items(self):
        """Rebuilds the rows from `self.items`.

        Only ever runs when the item list itself changes -- never on scroll, never on reuse,
        because there is neither.
        """
        self.items_box.clear_widgets()
        for item in self._visible_items():
            self.items_box.add_widget(
                DropdownItemWidget(
                    item,
                    show_dividers=self.show_dividers,
                    on_release_callback=self.dismiss,
                )
            )

    def _visible_items(self):
        items = self.items
        cap = self.max_visible_items
        if cap and len(items) > cap:
            app_logger.warning(
                f"DropdownMenu showing {cap} of {len(items)} items, dropping the rest"
            )
            items = items[:cap]
        return items

    def on_items(self, *_args):
        if self._built:
            self._build_items()

    def on_show_dividers(self, *_args):
        if self._built:
            self._build_items()

    def on_max_visible_items(self, *_args):
        if self._built:
            self._build_items()

    # --- header -----------------------------------------------------------------

    def _add_header(self):
        """Puts the header at the top of the card.

        A vertical BoxLayout lays `children` out in list order with y increasing, so
        children[-1] is the TOP and children[0] is the BOTTOM (see _iterate_layout in
        kivy/uix/boxlayout.py:275-300, which iterates zip(hint, sizes) unreversed). Kivy's
        add_widget defaults to index=0, i.e. the bottom, so the header has to be appended.
        """
        self.card.add_widget(self.header, len(self.card.children))

    def _build_header(self):
        if self.header is not None:
            self.card.remove_widget(self.header)
            self.header = None
        text = self.header_text
        if not text:
            return
        self.header = MDBoxLayout(
            MDLabel(
                text=text,
                bold=True,
                pos_hint={"center_y": .5},
                theme_font_size="Custom",
                font_size=sp(14),
                theme_font_name="Custom",
                font_name="RobotoMono",
                theme_text_color="Custom",
                text_color=self.header_text_color,
            ),
            size_hint_y=None,
            height=HEADER_HEIGHT,
            padding=(dp(16), 0, dp(16), 0),
            md_bg_color=self.header_bg_color,
            radius=[CARD_RADIUS,CARD_RADIUS,0,0],

        )
        self._add_header()

    def on_header_text(self, *_args):
        if self._built:
            self._build_header()
            self._build_items()

    # --- theme ------------------------------------------------------------------

    def apply_theme(self, card_bg_color, text_color, icon_color=None, header_bg_color=None, theme=None):
        """Repaints the live card.

        The previous implementation changed colours by rebuilding the item dicts and
        reassigning `menu.items`; there are no dicts here, so this just walks the rows that
        already exist.
        """
        self.card_bg_color = card_bg_color
        self.card.md_bg_color = card_bg_color
        self.text_color = text_color
        self.icon_color = icon_color or text_color
        if header_bg_color is not None:
            self.header_bg_color = header_bg_color
        self.header_text_color = text_color
        for row in self.items_box.children:
            row.recolor(text_color, self.icon_color, theme=theme)
        if self.header is not None:
            self.header.md_bg_color = self.header_bg_color
            for child in self.header.children:
                if isinstance(child, MDLabel):
                    child.text_color = text_color

    # --- open / close -----------------------------------------------------------

    def open(self):
        if self._is_open:
            return
        screen = self._target_screen()
        if screen is None:
            return
        # Invisible until _place_and_fade has positioned it. open() runs from dispatch_input(),
        # which is *after* Clock.tick(), so the scheduled placement cannot run until the next
        # tick -- but this frame is still drawn. Anything still visible at add time therefore
        # shows up for a frame in its previous state: the scrim left at opacity 1 by the last
        # open flashes full-screen black, and the card sits at its old position (or at its
        # default 100x100/0,0 on the first open) before it jumps to the caller.
        self.opacity = 0
        self.scrim.opacity = 0
        screen.add_widget(self)
        self._is_open = True
        Window.bind(on_resize=self.on_window_resize)
        # Before the positioning pass below: hide() moves the nav bar out synchronously, and
        # the card is placed against the layout on the next frame.
        self._hide_bottom_bar()
        # PlaceOnMainScreen.show() binds the back/ESC keys.
        self.show()
        # A frame of delay: the caller's button is mid-relayout when its on_release fires, so
        # its centre can still be stale for the layout pass that would place the card.
        Clock.schedule_once(self._place_and_fade, 0)

    def dismiss(self, *_args):
        if not self._is_open:
            return
        self.hide()

    def hide(self, *_args):
        """The single teardown path.

        PlaceOnMainScreen's back-key handler calls `hide()` directly, without going through
        `dismiss()`, so the state reset has to live here or a back-press leaves `_is_open`
        True and the menu silently refuses to reopen. The nav bar is restored here for the
        same reason: every dismissal route (back-press, scrim tap, row release) funnels here.
        """
        if self._fade:
            self._fade.cancel(self.scrim)
            self._fade = None
        self._is_open = False
        Window.unbind(on_resize=self.on_window_resize)
        self._show_bottom_bar()
        # PlaceOnMainScreen.hide() unbinds the keys and removes self from its parent.
        return super().hide()

    def _place_and_fade(self, *_args):
        if not self._is_open:
            return
        self._position_card()
        # Placed, so it can be shown. open() left it invisible precisely because the first
        # drawn frame would otherwise be an unplaced one.
        self.opacity = 1
        self.scrim.opacity = 0
        # Only the scrim fades; the card itself never scales, slides, or blinks in.
        self._fade = Animation(
            opacity=1, d=SCRIM_FADE_DURATION, t="out_quad"
        )
        self._fade.start(self.scrim)

    # --- positioning ------------------------------------------------------------

    def _position_card(self):
        """Places the card against the caller, flipping and clamping as needed."""
        caller = self.caller
        width = self.card_width
        height = self._measure_card_height()

        if caller is None:
            self.card.size = (width, height)
            self.card.pos = (
                (Window.width - width) / 2,
                (Window.height - height) / 2,
            )
            return

        cx, cy = caller.to_window(*caller.center)
        half = caller.width / 2
        # Prefer hanging off the caller's left edge; if that runs off screen, hang off the
        # right edge instead.
        x = cx - half
        if x + width > Window.width - EDGE_MARGIN:
            x = cx + half - width
        y = cy - caller.height / 2 - height - CALLER_GAP
        if y < EDGE_MARGIN:
            y = cy + caller.height / 2 + CALLER_GAP
        # Clamp both axes so the card is always fully on screen.
        x = max(EDGE_MARGIN, min(x, Window.width - width - EDGE_MARGIN))
        y = max(EDGE_MARGIN, min(y, Window.height - height - EDGE_MARGIN))

        self.card.size = (width, height)
        self.card.pos = (x, y)

    def _measure_card_height(self):
        """Natural card height, never more than the window can show.

        There is no scrolling by design, so the card is sized to its content and clamped;
        `max_visible_items` is how a caller keeps content short enough.
        """
        content = sum(child.height for child in self.items_box.children)
        height = content + self.items_box.padding[1] + self.items_box.padding[3]
        if self.header is not None:
            height += self.header.height
        return min(height, Window.height - 2 * EDGE_MARGIN)

    def on_window_resize(self, *_args):
        if self._is_open:
            self._position_card()

    # --- dismissal --------------------------------------------------------------

    def on_touch_down(self, touch):
        # Inside the card: let the rows see it, but still consume so the touch does not leak
        # through to whatever the scrim is covering.
        if self.card.collide_point(*touch.pos):
            super().on_touch_down(touch)
            return True
        # Outside the card is a scrim tap.
        self.dismiss()
        return True

    # --- internals --------------------------------------------------------------

    def _bottom_bar(self):
        """The app's nav bar, or None if it does not exist yet.

        `app.bottom_bar` is None until main.py builds it, and is missing entirely under hot
        reload, so this has to tolerate both.
        """
        from utils.model import get_app

        return getattr(get_app(), "bottom_bar", None) or None

    def _hide_bottom_bar(self):
        """Takes the nav bar away while the menu is up.

        The menu is added to the screen, but the nav bar is a sibling of the screen manager in
        the root layout, so the scrim cannot cover it -- it has to be hidden outright. Same
        hidden_by=self ownership token the other overlays use.
        """
        bar = self._bottom_bar()
        if bar is not None:
            bar.hide(animation=False, hidden_by=self)

    def _show_bottom_bar(self):
        bar = self._bottom_bar()
        if bar is not None:
            # Only restores if we were the ones who hid it; when another owner hid the bar
            # first (the screen manager does this on the fullscreen screen) show() logs that
            # it refused and leaves it hidden, which is what we want.
            bar.show(animation=False, hidden_by=self)

    def _target_screen(self):
        from utils.model import get_app

        app = get_app()
        if not hasattr(app, "sm"):
            app_logger.warning("DropdownMenu.open() on hot reload: app.sm is missing")
            return None
        return app.sm.current_screen
