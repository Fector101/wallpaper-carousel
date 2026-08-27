package org.wally.waller;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Build;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class UpdateCheckWorker extends Worker {

    private static final String TAG = "UpdateCheckWorker";
    private static final String PREFS_NAME = "update_checker_prefs";
    private static final String KEY_LAST_NOTIFIED = "last_notified_timestamp";
    private static final long SEVEN_DAYS_MS = 7L * 24 * 60 * 60 * 1000;
    private static final String CHANNEL_ID = "update_channel";
    private static final String CHANNEL_NAME = "App Updates";
    private static final int NOTIFICATION_ID = 999;
    private static final String API_URL = "https://api.github.com/repos/Fector101/wallpaper-carousel/releases/latest";

    public UpdateCheckWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Log.d(TAG, "doWork called");

        Context ctx = getApplicationContext();

        if (!isNetworkAvailable(ctx)) {
            Log.d(TAG, "No network, retrying later");
            return Result.retry();
        }

        SharedPreferences prefs = ctx.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        long lastNotified = prefs.getLong(KEY_LAST_NOTIFIED, 0);
        long now = System.currentTimeMillis();

        if (now - lastNotified < SEVEN_DAYS_MS) {
            Log.d(TAG, "Cooldown active, skipping");
            return Result.success();
        }

        try {
            String currentVersion = getCurrentVersion(ctx);
            Log.d(TAG, "Current version: " + currentVersion);

            String latestVersion = fetchLatestVersion();
            if (latestVersion == null) {
                Log.e(TAG, "Failed to fetch latest version");
                return Result.retry();
            }
            Log.d(TAG, "Latest version: " + latestVersion);

            if (latestVersion.equals(currentVersion)) {
                Log.d(TAG, "Already on latest version");
                return Result.success();
            }

            Log.d(TAG, "New version available: " + latestVersion);
            sendNotification(ctx, latestVersion);
            prefs.edit().putLong(KEY_LAST_NOTIFIED, System.currentTimeMillis()).apply();
            Log.d(TAG, "Timestamp saved, notification sent");

        } catch (Exception e) {
            Log.e(TAG, "Update check failed", e);
            return Result.retry();
        }

        return Result.success();
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

    private String getCurrentVersion(Context context) {
        try {
            PackageInfo pInfo = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            return pInfo.versionName;
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "Could not get package version", e);
            return "";
        }
    }

    private String fetchLatestVersion() {
        try {
            URL url = new URL(API_URL);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("Accept", "application/vnd.github.v3+json");
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            int responseCode = conn.getResponseCode();
            if (responseCode != 200) {
                Log.e(TAG, "HTTP " + responseCode);
                return null;
            }

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            reader.close();
            conn.disconnect();

            JSONObject json = new JSONObject(sb.toString());
            String tag = json.getString("tag_name");
            return tag.startsWith("v") ? tag.substring(1) : tag;

        } catch (Exception e) {
            Log.e(TAG, "Failed to fetch latest version", e);
            return null;
        }
    }

    private void sendNotification(Context context, String version) {
        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_HIGH);
            channel.setDescription("Notifications for app updates");
            nm.createNotificationChannel(channel);
        }

        Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launchIntent == null) return;
        launchIntent.putExtra("action", "open_update");
        launchIntent.putExtra("version", version);
        launchIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, NOTIFICATION_ID, launchIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("New version available")
                .setContentText("v" + version + " is ready. Tap to update.")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(pendingIntent)
                .setAutoCancel(true);

        nm.notify(NOTIFICATION_ID, builder.build());
        Log.d(TAG, "Notification sent for v" + version);
    }
}
