package org.wally.waller;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.util.Log;

public class ConnectivityReceiver extends BroadcastReceiver {

    private static final String TAG = "ConnectivityReceiver";
    private static final String PREFS_NAME = "update_checker_prefs";
    private static final String KEY_LAST_NOTIFIED = "last_notified_timestamp";
    private static final long SEVEN_DAYS_MS = 7L * 24 * 60 * 60 * 1000;

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!isNetworkAvailable(context)) {
            return;
        }

        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        long lastNotified = prefs.getLong(KEY_LAST_NOTIFIED, 0);
        long now = System.currentTimeMillis();

        if (now - lastNotified < SEVEN_DAYS_MS) {
            Log.d(TAG, "Less than 7 days since last notification, skipping");
            return;
        }

        Log.d(TAG, "Network available, 7-day cooldown passed, starting update check");
        launchActivityForUpdateCheck(context);
    }

    private boolean isNetworkAvailable(Context context) {
        try {
            ConnectivityManager cm = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            NetworkInfo info = cm.getActiveNetworkInfo();
            return info != null && info.isConnected();
        } catch (Exception e) {
            Log.e(TAG, "Error checking network", e);
            return false;
        }
    }

    private void launchActivityForUpdateCheck(Context context) {
        try {
            Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
            if (launchIntent == null) {
                Log.e(TAG, "No launch intent found");
                return;
            }
            launchIntent.putExtra("check_for_update", true);
            launchIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            context.startActivity(launchIntent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to start activity", e);
        }
    }
}
