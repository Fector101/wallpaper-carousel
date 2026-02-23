import traceback
from android_notify.config import get_python_activity_context,autoclass, on_android_platform
from android_notify.internal.java_classes import PendingIntent,Intent
# from utils.config_manager import ConfigManager


def add_home_screen_widget(button=None):
    try:
        # cm = ConfigManager()
        # cm.set_on_wake_state(not cm.get_on_wake_state())
        # return
        from android_widgets import get_package_name

        # Android classes
        AppWidgetManager = autoclass('android.appwidget.AppWidgetManager')
        ComponentName = autoclass('android.content.ComponentName')


        # Your widget provider class (Java side)
        CarouselWidgetProvider = autoclass(
            f'{get_package_name()}.CarouselWidgetProvider'
        )

        # # Get current Android activity context
        # PythonActivity = autoclass('org.kivy.android.PythonActivity')
        # context = PythonActivity.mActivity
        context = get_python_activity_context()

        # AppWidgetManager instance
        appWidgetManager = AppWidgetManager.getInstance(context)

        # ComponentName for your widget provider
        myProvider = ComponentName(context, CarouselWidgetProvider)

        # Check if pinning is supported
        if appWidgetManager.isRequestPinAppWidgetSupported():
            # Optional: callback when widget is pinned
            intent = Intent(context, CarouselWidgetProvider)

            successCallback = PendingIntent.getBroadcast(
                context,
                0,
                intent,
            PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT # type: ignore

            )

            # Request widget pin
            appWidgetManager.requestPinAppWidget(
                myProvider,
                None,
                successCallback
            )
    except Exception as error_adding_home_screen_widget:
        print("error_adding_home_screen_widget",error_adding_home_screen_widget)
        traceback.print_exc()



def is_device_on_light_mode():
    try:
        Configuration = autoclass("android.content.res.Configuration")
        activity = get_python_activity_context()
        config = activity.getResources().getConfiguration()

        ui_mode = config.uiMode & Configuration.UI_MODE_NIGHT_MASK

        if ui_mode == Configuration.UI_MODE_NIGHT_YES:
            theme = "dark"
        elif ui_mode == Configuration.UI_MODE_NIGHT_NO:
            theme = "light"
        else:
            theme = "unknown"
        return theme
    except Exception as error_getting_device_in_light_or_dark_mode:
        if on_android_platform():
            print("error_getting_device_in_light_or_dark_mode:", error_getting_device_in_light_or_dark_mode)
            traceback.print_exc()
        else:
            pass
            # print("error_getting_device_in_light_or_dark_mode:", error_getting_device_in_light_or_dark_mode)
            # TODO get dark/light theme from PC
        return "dark"



def test_java_action():
    from jnius import autoclass, cast
    # from android import python_act

    # Get current activity and context
    # mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
    context = get_python_activity_context()#mActivity.getApplicationContext()

    # Autoclass necessary Java classes
    RingtoneManager = autoclass("android.media.RingtoneManager")
    Uri = autoclass("android.net.Uri")
    AudioAttributesBuilder = autoclass("android.media.AudioAttributes$Builder")
    AudioAttributes = autoclass("android.media.AudioAttributes")
    AndroidString = autoclass("java.lang.String")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationChannel = autoclass("android.app.NotificationChannel")
    NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
    NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
    NotificationManagerCompat = autoclass("androidx.core.app.NotificationManagerCompat")
    NotificationCompatActionBuilder = autoclass("androidx.core.app.NotificationCompat$Action$Builder")

    func_from = getattr(NotificationManagerCompat, "from")
    Intent = autoclass("android.content.Intent")
    PendingIntent = autoclass("android.app.PendingIntent")

    # Autoclass your own Java class
    action1 = autoclass("org.wally.waller.Action1")

    # Variables
    channel_id = "channel_id"
    notification_id = 101
    _id = 1  # action id

    # === CREATE CHANNEL ===
    sound = cast(Uri, RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))
    att = AudioAttributesBuilder()
    att.setUsage(AudioAttributes.USAGE_NOTIFICATION)
    att.setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
    att = cast(AudioAttributes, att.build())

    name = cast("java.lang.CharSequence", AndroidString("Channel Name"))
    description = AndroidString("Channel Description")
    importance = NotificationManager.IMPORTANCE_HIGH

    channel = NotificationChannel(channel_id, name, importance)
    channel.setDescription(description)
    channel.enableLights(True)
    channel.enableVibration(True)
    channel.setSound(sound, att)

    notificationManager = context.getSystemService(NotificationManager)
    notificationManager.createNotificationChannel(channel)

    # === CREATE NOTIFICATION ===
    builder = NotificationCompatBuilder(context, channel_id)
    builder.setSmallIcon(context.getApplicationInfo().icon)
    builder.setContentTitle(cast("java.lang.CharSequence", AndroidString("Notification Title")))
    builder.setContentText(cast("java.lang.CharSequence", AndroidString("Notification Text")))
    builder.setSound(sound)
    builder.setPriority(NotificationCompat.PRIORITY_HIGH)
    builder.setVisibility(NotificationCompat.VISIBILITY_PUBLIC)

    # Intent for action button
    intent = Intent(context, action1)
    pending_intent = PendingIntent.getBroadcast(
        context, _id, intent, PendingIntent.FLAG_CANCEL_CURRENT | PendingIntent.FLAG_IMMUTABLE
    )
    title = cast("java.lang.CharSequence", AndroidString("Action 1"))

    action1_button = NotificationCompatActionBuilder(
        _id, title, pending_intent
    ).build()
    builder.addAction(action1_button)

    # Send the notification
    compat_manager = func_from(context)
    compat_manager.notify(notification_id, builder.build())



    # def fetch_recovered_images(self, dt=0):
    #     MediaStoreImages = autoclass('android.provider.MediaStore$Images$Media')
    #     ContentUris = autoclass('android.content.ContentUris')
    #     BuildVersion = autoclass("android.os.Build$VERSION")
    #
    #     context = get_python_activity_context()
    #     resolver = context.getContentResolver()
    #
    #     folder_name = "Waller/wallpapers"
    #     image_uris = []
    #
    #     projection = [MediaStoreImages._ID]
    #     query_uri = MediaStoreImages.EXTERNAL_CONTENT_URI
    #     sort_order = MediaStoreImages.DATE_ADDED + " DESC"
    #
    #     sdk = BuildVersion.SDK_INT
    #     log.warning(f"SDK VERSION = {sdk}")
    #
    #     # ----------------------------
    #     # ANDROID 10+ (API 29+)
    #     # ----------------------------
    #     if sdk >= 29:
    #         selection = MediaStoreImages.RELATIVE_PATH + " LIKE ?"
    #         selection_args = [f"%Pictures/{folder_name}/%"]
    #
    #         cursor = resolver.query(
    #             query_uri,
    #             projection,
    #             selection,
    #             selection_args,
    #             sort_order
    #         )
    #
    #         if cursor:
    #             try:
    #                 id_col = cursor.getColumnIndexOrThrow(MediaStoreImages._ID)
    #                 while cursor.moveToNext():
    #                     image_id = cursor.getLong(id_col)
    #                     uri = ContentUris.withAppendedId(query_uri, image_id)
    #                     image_uris.append(str(uri))
    #             finally:
    #                 cursor.close()
    #
    #     # ----------------------------
    #     # FALLBACK (Android 9 and below OR empty)
    #     # ----------------------------
    #     if not image_uris:
    #         log.warning("Falling back to DATA path query")
    #
    #         selection = MediaStoreImages.DATA + " LIKE ?"
    #         selection_args = [f"%/Pictures/{folder_name}/%"]
    #
    #         cursor = resolver.query(
    #             query_uri,
    #             projection,
    #             selection,
    #             selection_args,
    #             sort_order
    #         )
    #
    #         if cursor:
    #             try:
    #                 id_col = cursor.getColumnIndexOrThrow(MediaStoreImages._ID)
    #                 while cursor.moveToNext():
    #                     image_id = cursor.getLong(id_col)
    #                     uri = ContentUris.withAppendedId(query_uri, image_id)
    #                     image_uris.append(str(uri))
    #             finally:
    #                 cursor.close()
    #
    #     log.warning(f"FOUND {len(image_uris)} IMAGES")
    #     return image_uris