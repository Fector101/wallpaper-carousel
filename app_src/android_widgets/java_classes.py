from .config import is_platform_android

if is_platform_android():
    from jnius import autoclass
    String = autoclass("java.lang.String")
    RemoteViews_ = autoclass('android.widget.RemoteViews')
    AppWidgetManager_ = autoclass('android.appwidget.AppWidgetManager')
    ComponentName = autoclass('android.content.ComponentName')

else:
    raise ImportError("Not on Android, Unable to import Java classes")