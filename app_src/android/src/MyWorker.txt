package org.wally.waller;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

public class MyWorker extends Worker {

    private static final String TAG = "MyWorker";
    private static final String CHANNEL_ID = "workmanager_channel";

    public MyWorker(
            @NonNull Context context,
            @NonNull WorkerParameters params
    ) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {

        String message = getInputData().getString("message");
        if (message == null) {
            message = "WorkManager executed successfully";
        }

        Log.i(TAG, "Worker running: " + message);

        showNotification(message);

        return Result.success();
    }

    private void showNotification(String message) {
        Context context = getApplicationContext();

        NotificationManager notificationManager =
                (NotificationManager) context.getSystemService(
                        Context.NOTIFICATION_SERVICE
                );

        // Android 8+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "WorkManager Notifications",
                    NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("Notifications from WorkManager");
            notificationManager.createNotificationChannel(channel);
        }

        Notification notification =
                new Notification.Builder(context, CHANNEL_ID)
                        .setSmallIcon(android.R.drawable.ic_dialog_info)
                        .setContentTitle("WorkManager")
                        .setContentText(message)
                        .setAutoCancel(true)
                        .build();

        notificationManager.notify(
                (int) System.currentTimeMillis(),
                notification
        );
    }
}
