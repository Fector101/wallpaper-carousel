package org.wally.waller;

import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

/**
 * Helper to request an AppWidgetProvider onUpdate via an APPWIDGET_UPDATE
 * broadcast. Used from Python after assigning a picked image to a widget.
 */
public class WidgetUpdater {

    private static final String TAG = "WidgetUpdater";

    public static void requestUpdate(Context context, String providerName, int appWidgetId) {
        try {
            Intent intent = new Intent(AppWidgetManager.ACTION_APPWIDGET_UPDATE);
            String className = context.getPackageName() + "." + providerName;
            intent.setComponent(new ComponentName(context.getPackageName(), className));
            intent.putExtra(AppWidgetManager.EXTRA_APPWIDGET_IDS, new int[]{appWidgetId});
            context.sendBroadcast(intent);
            Log.d(TAG, "Requested update for " + className + " id=" + appWidgetId);
        } catch (Exception e) {
            Log.e(TAG, "requestUpdate failed", e);
        }
    }
}