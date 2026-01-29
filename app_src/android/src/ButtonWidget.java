// package app.vercel.androidnotify;
package org.wally.waller;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.widget.RemoteViews;

// import app.vercel.androidnotify.R;
import org.wally.waller.R;

public class ButtonWidget extends AppWidgetProvider {

    private static final String ACTION_INCREMENT =
//             "app.vercel.androidnotify.ACTION_INCREMENT";
            "org.wally.waller.ACTION_INCREMENT";

    @Override
    public void onUpdate(Context context,
                         AppWidgetManager appWidgetManager,
                         int[] appWidgetIds) {

        for (int widgetId : appWidgetIds) {

            RemoteViews views = new RemoteViews(
                    context.getPackageName(),
                    R.layout.button_widget
            );

            Intent intent = new Intent(context, ButtonWidget.class);
            intent.setAction(ACTION_INCREMENT);
            intent.putExtra(
                    AppWidgetManager.EXTRA_APPWIDGET_ID,
                    widgetId
            );

            PendingIntent pendingIntent = PendingIntent.getBroadcast(
                    context,
                    widgetId, // unique per widget instance
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT
                            | PendingIntent.FLAG_IMMUTABLE
            );

            views.setOnClickPendingIntent(
                    R.id.widget_button,
                    pendingIntent
            );

            appWidgetManager.updateAppWidget(widgetId, views);
        }
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);

        if (ACTION_INCREMENT.equals(intent.getAction())) {

            int widgetId = intent.getIntExtra(
                    AppWidgetManager.EXTRA_APPWIDGET_ID,
                    AppWidgetManager.INVALID_APPWIDGET_ID
            );

            if (widgetId == AppWidgetManager.INVALID_APPWIDGET_ID) return;

            SharedPreferences prefs = context.getSharedPreferences(
                    "widget_prefs",
                    Context.MODE_PRIVATE
            );

            int count = prefs.getInt(
                    "count_" + widgetId,
                    0
            );

            count++;

            prefs.edit()
                    .putInt("count_" + widgetId, count)
                    .apply();

            RemoteViews views = new RemoteViews(
                    context.getPackageName(),
                    R.layout.button_widget
            );

            views.setTextViewText(
                    R.id.widget_text,
                    "Count: " + count
            );

            AppWidgetManager.getInstance(context)
                    .updateAppWidget(widgetId, views);
        }
    }
}
