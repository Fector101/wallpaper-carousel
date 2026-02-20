package org.wally.waller;


import android.app.KeyguardManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

// import android.widget.Toast;
// import android.os.Build;
// import android.app.NotificationChannel;
// import android.app.NotificationManager;
// import androidx.core.app.NotificationCompat;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.InetAddress;

public class DetectReceiver extends BroadcastReceiver {

    private static final String TAG = "DetectReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || intent.getAction() == null) {
            Log.i(TAG, "No intent");
            return;
        }

        String action = intent.getAction();
        Log.w(TAG, "Received action: " + action);

        KeyguardManager km =
                (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);

        boolean isLocked = km != null && km.isKeyguardLocked();

        if (Intent.ACTION_SCREEN_OFF.equals(action)) {
            Log.i(TAG, "ACTION_SCREEN_OFF");

            if (isLocked) {
                Log.i(TAG, "screen is locked");
                Integer servicePort = getServicePort(context, intent);
                final int finalPort = servicePort;
                final String finalAddress = "/apply_next_wallpaper";
                final String finalArg = "oscArg";

                new Thread(() -> {
                    try {
                        sendOscMessage("127.0.0.1", finalPort, finalAddress, finalArg);
                        Log.d(TAG, "OSC message sent to python: " + "127.0.0.1:" + finalPort + finalAddress + " " + finalArg);
                    } catch (Exception e) {
                        Log.e(TAG, "Failed to send OSC message to python", e);
                    }
                }).start();
            } else {
                Log.i(TAG, "screen is unlocked (rare but possible)");
            }

        } else if (Intent.ACTION_SCREEN_ON.equals(action)) {
            Log.i(TAG, "ACTION_SCREEN_ON");

            if (isLocked) {
                Log.i(TAG, "screen is on but locked");

//                 Toast.makeText(context, "screen is on and locked", Toast.LENGTH_LONG).show();
//                 NotificationManager nm =
//                     (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
//                 String channelId = "detect_lockscreen";
//
//                 if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
//                     NotificationChannel channel =
//                         new NotificationChannel(channelId, "detect_lockscreen Channel",
//                                                 NotificationManager.IMPORTANCE_DEFAULT);
//                     nm.createNotificationChannel(channel);
//                 }
//
//                 NotificationCompat.Builder builder =
//                     new NotificationCompat.Builder(context, channelId)
//                         .setSmallIcon(android.R.drawable.ic_dialog_info)
//                         .setContentTitle("On Lock Screen")
//                         .setPriority(NotificationCompat.PRIORITY_DEFAULT);
//
//                 nm.notify((int) System.currentTimeMillis(), builder.build());

            } else {
                Log.i(TAG, "screen is on and unlocked");
            }

        } else if (Intent.ACTION_USER_PRESENT.equals(action)) {
            Log.i(TAG, "USER_PRESENT → screen on and unlocked");
        }
    }

    private void sendOscMessage(String host, int port, String address, String arg) throws Exception {
        InetAddress serverAddr = InetAddress.getByName(host);
        DatagramSocket socket = new DatagramSocket();

        byte[] addrBytes = (address + "\0").getBytes("US-ASCII");
        // OSC messages are padded to 4 bytes, simple approach:
        int padding = 4 - (addrBytes.length % 4);
        byte[] paddedAddr = new byte[addrBytes.length + padding];
        System.arraycopy(addrBytes, 0, paddedAddr, 0, addrBytes.length);

        // Arguments
        String typeTag = ",s\0\0"; // string argument
        byte[] typeBytes = typeTag.getBytes("US-ASCII");

        byte[] argBytes = (arg + "\0").getBytes("US-ASCII");
        int argPadding = 4 - (argBytes.length % 4);
        byte[] paddedArg = new byte[argBytes.length + argPadding];
        System.arraycopy(argBytes, 0, paddedArg, 0, argBytes.length);

        // Combine all
        byte[] message = new byte[paddedAddr.length + typeBytes.length + paddedArg.length];
        System.arraycopy(paddedAddr, 0, message, 0, paddedAddr.length);
        System.arraycopy(typeBytes, 0, message, paddedAddr.length, typeBytes.length);
        System.arraycopy(paddedArg, 0, message, paddedAddr.length + typeBytes.length, paddedArg.length);

        DatagramPacket packet = new DatagramPacket(message, message.length, serverAddr, port);
        socket.send(packet);
        socket.close();
    }

    private int getServicePort(Context context, Intent intent) {
        final int DEFAULT_PORT = 5006;

        // Fallback: read from port.txt
        File portFile = new File(context.getFilesDir(), "port.txt");
        if (portFile.exists()) {
            try (BufferedReader br = new BufferedReader(new FileReader(portFile))) {
                String line = br.readLine();
                if (line != null && !line.isEmpty()) {
                    int port = Integer.parseInt(line.trim());
                    Log.d(TAG, "Service port obtained from port.txt: " + port);
                    return port;
                } else {
                    Log.e(TAG, "port.txt is empty, using default port: " + DEFAULT_PORT);
                }
            } catch (Exception e) {
                Log.e(TAG, "Error reading port.txt, using default port: " + DEFAULT_PORT, e);
            }
        } else {
            Log.w(TAG, "port.txt not found, using default port: " + DEFAULT_PORT);
        }

        // If it fails, return default
        Log.d(TAG, "Using default service port: " + DEFAULT_PORT);
        return DEFAULT_PORT;
    }

}
