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

import androidx.core.app.NotificationCompat;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;

public class UpdateNotifier {

    private static final String TAG = "UpdateNotifier";
    private static final String PREFS_NAME = "update_checker_prefs";
    private static final String KEY_LAST_NOTIFIED = "last_notified_timestamp";
    private static final long SEVEN_DAYS_MS = 7L * 24 * 60 * 60 * 1000;
    private static final String CHANNEL_ID = "update_channel";
    private static final String CHANNEL_NAME = "App Updates";
    private static final int NOTIFICATION_ID = 999;
    private static final String API_URL = "https://api.github.com/repos/Fector101/wallpaper-carousel/releases/latest";

    public static boolean isCooldownActive(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        long lastNotified = prefs.getLong(KEY_LAST_NOTIFIED, 0);
        long now = System.currentTimeMillis();
        Log.d(TAG, "elapsed=" + (now - lastNotified) + "ms, cooldown=" + SEVEN_DAYS_MS + "ms");
        return now - lastNotified < SEVEN_DAYS_MS;
    }

    public static boolean isNetworkAvailable(Context context) {
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

    /**
     * Full check: version compare + notes fetch + notification.
     * Returns true if the check should be retried later (fetch failed), false otherwise.
     */
    public static boolean checkAndNotify(Context context) {
        try {
            String currentVersion = getCurrentVersion(context);
            Log.d(TAG, "Current version: " + currentVersion);

            String latestVersion = fetchLatestVersion();
            if (latestVersion == null) {
                Log.e(TAG, "Failed to fetch latest version");
                return true;
            }
            Log.d(TAG, "Latest version: " + latestVersion);

            if (latestVersion.equals(currentVersion)) {
                Log.d(TAG, "Already on latest version");
                return false;
            }

            Log.d(TAG, "New version available: " + latestVersion);
            String releaseNotes = fetchReleaseNotes(latestVersion);
            boolean posted = sendNotification(context, latestVersion, releaseNotes);
            if (!posted) {
                Log.w(TAG, "Notification not eligible to post, cooldown timestamp NOT saved");
                return true;
            }

            context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
                    .edit().putLong(KEY_LAST_NOTIFIED, System.currentTimeMillis()).apply();
            Log.d(TAG, "Timestamp saved, notification sent");

        } catch (Exception e) {
            Log.e(TAG, "Update check failed", e);
            return true;
        }
        return false;
    }

    public static String getCurrentVersion(Context context) {
        try {
            PackageInfo pInfo = context.getPackageManager().getPackageInfo(context.getPackageName(), 0);
            return pInfo.versionName;
        } catch (PackageManager.NameNotFoundException e) {
            Log.e(TAG, "Could not get package version", e);
            return "";
        }
    }

    private static String fetchLatestVersion() {
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

    private static String fetchReleaseNotes(String version) {
        try {
            String fileUrl = "https://github.com/Fector101/wallpaper-carousel/releases/download/v"
                    + version + "/update-note-v" + version + ".txt";
            URL url = new URL(fileUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(10000);

            int responseCode = conn.getResponseCode();
            if (responseCode != 200) {
                Log.e(TAG, "Release notes HTTP " + responseCode);
                return null;
            }

            BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
                sb.append("\n");
            }
            reader.close();
            conn.disconnect();
            return sb.toString().trim();

        } catch (Exception e) {
            Log.e(TAG, "Failed to fetch release notes", e);
            return null;
        }
    }

    private static boolean canPostNotification(Context context) {
        try {
            NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) {
                Log.w(TAG, "NotificationManager unavailable, cannot post");
                return false;
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                if (!nm.canPostNotifications()) {
                    Log.w(TAG, "POST_NOTIFICATIONS permission not granted");
                    return false;
                }
            } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                if (!nm.areNotificationsEnabled()) {
                    Log.w(TAG, "Notifications disabled for app");
                    return false;
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID, CHANNEL_NAME, NotificationManager.IMPORTANCE_HIGH);
                channel.setDescription("Notifications for app updates");
                nm.createNotificationChannel(channel);

                NotificationChannel created = nm.getNotificationChannel(CHANNEL_ID);
                if (created == null || created.getImportance() == NotificationManager.IMPORTANCE_NONE) {
                    Log.w(TAG, "Update channel disabled, cannot post");
                    return false;
                }
            }
            return true;
        } catch (Exception e) {
            Log.e(TAG, "Notification eligibility check failed", e);
            return false;
        }
    }

    private static boolean sendNotification(Context context, String version, String releaseNotes) {
        if (!canPostNotification(context)) {
            return false;
        }

        NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return false;

        Intent launchIntent = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launchIntent == null) return false;
        launchIntent.putExtra("action", "open_update");
        launchIntent.putExtra("version", version);
        launchIntent.putExtra("release_notes", releaseNotes);
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
        return true;
    }
}