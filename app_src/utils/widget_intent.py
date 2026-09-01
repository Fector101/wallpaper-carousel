import os

from android_notify.config import on_android_platform

from utils.logger import app_logger


def handle_widget_intent(app, intent=None):
    """Read activity intent extras and react to home-screen widget clicks."""
    if not on_android_platform():
        return
    from android_notify.internal.intents import get_data_object_added_to_intent
    print(f"ane {get_data_object_added_to_intent(intent)}")

    try:
        from android_notify.internal.java_classes import autoclass

        if intent is None:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            intent = activity.getIntent()

        if intent is None:
            return

        extras = intent.getExtras()
        if extras is None:
            return

        action = extras.getString("action")
        if action == "open_widget_image":
            image_path = extras.getString("image_path", "")
            intent.removeExtra("action")
            intent.removeExtra("image_path")
            app_logger.info(f"handle_widget_intent: open image widget -> {image_path}")
            _open_image_from_widget(app, image_path)
        elif action == "open_widget_picker":
            app_widget_id = extras.getInt("app_widget_id", -1)
            widget_provider = extras.getString("widget_provider", "ImageWidgetProvider")
            intent.removeExtra("action")
            intent.removeExtra("app_widget_id")
            intent.removeExtra("widget_provider")
            app_logger.info("handle_widget_intent: open file chooser from widget")
            remember_widget_pick(app, app_widget_id, widget_provider)
            _open_file_chooser_from_widget(app)
    except Exception:
        app_logger.exception("Failed to handle widget intent")


def remember_widget_pick(app, app_widget_id, widget_provider):
    """Remember which widget opened the file chooser so its picked image is
    assigned to that widget once the import finishes."""
    if app_widget_id is None or app_widget_id < 0:
        return
    app._widget_pick_pending = {
        "app_widget_id": int(app_widget_id),
        "widget_provider": widget_provider,
    }


def clear_pending_widget_pick(app):
    app._widget_pick_pending = None


def assign_picked_images_to_widget(app, new_images):
    """Assign the first image picked through a widget-opened chooser to that
    widget, then refresh it so it renders the new image."""
    pending = getattr(app, "_widget_pick_pending", None)
    if not pending:
        return
    app._widget_pick_pending = None
    if not new_images:
        return
    image_path = str(new_images[0])
    try:
        from utils.database import ImageDatabase
        ImageDatabase().set_widget_image(pending["app_widget_id"], image_path)
        app_logger.info(
            f"widget pick: assigned {image_path} to widget "
            f"{pending['app_widget_id']} ({pending['widget_provider']})"
        )
        from utils.android import refresh_widget
        refresh_widget(pending["widget_provider"], pending["app_widget_id"])
    except Exception:
        app_logger.exception("Failed to assign picked image to widget")


def _open_file_chooser_from_widget(app):
    from kivy.clock import Clock

    def _go(dt, _attempts=0):
        if getattr(app, "image_operation_ready", False) and getattr(app, "sm", None) is not None:
            try:
                app.sm.current = "thumbs"
                app.sm.gallery_screen.open_file_chooser()
            except Exception:
                app_logger.exception("Failed to open file chooser from widget")
            return
        if _attempts < 30:
            next_attempt = _attempts + 1
            Clock.schedule_once(lambda dt, a=next_attempt: _go(dt, a), 0.3)

    Clock.schedule_once(_go, 0.5)


def _open_image_from_widget(app, image_path):
    from kivy.clock import Clock

    def _go(dt, _attempts=0):
        gallery = getattr(getattr(app, "sm", None), "gallery_screen", None)
        if gallery is None or not getattr(gallery, "wallpapers", None):
            if _attempts < 30:
                next_attempt = _attempts + 1
                Clock.schedule_once(lambda dt, a=next_attempt: _go(dt, a), 0.3)
            return
        try:
            if not image_path or not os.path.exists(image_path):
                app_logger.info("handle_widget_intent: widget image no longer exists, skipping")
                return
            _open_image_in_matching_tab(gallery, image_path)
        except Exception:
            app_logger.exception("Failed to open image from widget")

    Clock.schedule_once(_go, 0.5)


def _open_image_in_matching_tab(gallery, image_path):
    from utils.model import GalleryTabs

    preferred = [GalleryTabs.BOTH.value, GalleryTabs.DAY.value, GalleryTabs.NOON.value]
    order = [gallery.current_tab] + [t for t in preferred if t != gallery.current_tab]

    for tab_name in order:
        tab_data = gallery.tab_instances.get(tab_name)
        if not isinstance(tab_data, dict):
            continue
        wallpapers = tab_data.get("wallpapers") or []
        if image_path in wallpapers:
            app_logger.info(f"handle_widget_intent: found widget image in {tab_name} tab")
            if gallery.current_tab != tab_name:
                gallery.current_tab = tab_name
            gallery.open_fullscreen_for_image(wallpaper_path=image_path)
            return

    app_logger.info("handle_widget_intent: widget image not found in any tab")