package org.wally.waller;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.widget.RemoteViews;

import org.wally.waller.R;
import android.app.PendingIntent;
import android.content.Intent;

public class SimpleWidget extends AppWidgetProvider {

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        for (int appWidgetId : appWidgetIds) {

            RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.simple_widget);

            // Example: Set text
            views.setTextViewText(R.id.widget_text, "Hello Widget!");

            // Update widget
            appWidgetManager.updateAppWidget(appWidgetId, views);
        }
    }
}
