package org.wally.waller;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;
// import android.os.Build;
// import android.app.NotificationChannel;
// import android.app.NotificationManager;
// import androidx.core.app.NotificationCompat;

import android.app.ActivityManager;
import java.util.List;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.File;
import org.wally.waller.ServiceWallpapercarousel;

public class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) {
            Log.d("BootReceiver", "Device rebooted");

            try {
                File bootFlag = new File(context.getFilesDir(), "start_on_boot.txt");
                if (bootFlag.exists()) {
                    try (BufferedReader br = new BufferedReader(new FileReader(bootFlag))) {
                        String line = br.readLine();
                        if (line != null && line.trim().equals("false")) {
                            Log.d("BootReceiver", "start_on_boot is disabled, skipping");
                            return;
                        }
                    }
                }

                ActivityManager am = (ActivityManager) context.getSystemService(Context.ACTIVITY_SERVICE);
                List<ActivityManager.RunningServiceInfo> services = am.getRunningServices(100);
                String serviceName = "org.wally.waller.ServiceWallpapercarousel";

                boolean alreadyRunning = false;
                for (ActivityManager.RunningServiceInfo info : services) {
                    if (info.service.getClassName().equals(serviceName)) {
                        alreadyRunning = true;
                        break;
                    }
                }

                if (!alreadyRunning) {
                    String args = "{\"service_port\":5006,\"ui_port\":5007}";
                    ServiceWallpapercarousel.start(context, args);
                    Log.d("BootReceiver", "ServiceWallpapercarousel restart requested");
                } else {
                    Log.d("BootReceiver", "Service already running, skipping start");
                }
            } catch (Exception e) {
                Log.e("BootReceiver", "Failed to restart", e);
            }
        }



        // NotificationManager nm =
        //     (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        // String channelId = "boot_channel";

        // if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
        //     NotificationChannel channel =
        //         new NotificationChannel(channelId, "Boot Channel",
        //                                 NotificationManager.IMPORTANCE_DEFAULT);
        //     nm.createNotificationChannel(channel);
        // }

        // NotificationCompat.Builder builder =
        //     new NotificationCompat.Builder(context, channelId)
        //         .setSmallIcon(android.R.drawable.ic_dialog_info)
        //         .setContentTitle("Boot Triggered")
        //         .setContentText("test for on restart")
        //         .setPriority(NotificationCompat.PRIORITY_DEFAULT);

        // nm.notify((int) System.currentTimeMillis(), builder.build());
    }
}
