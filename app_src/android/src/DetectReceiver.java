package org.wally.waller;


import android.app.KeyguardManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;
import android.widget.Toast;

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
            } else {
                Log.i(TAG, "screen is unlocked (rare but possible)");
            }

        } else if (Intent.ACTION_SCREEN_ON.equals(action)) {
            Log.i(TAG, "ACTION_SCREEN_ON");

            if (isLocked) {
                Log.i(TAG, "screen is on but locked");
                // Toast.makeText(context, "screen is on and locked", Toast.LENGTH_LONG).show();

            } else {
                Log.i(TAG, "screen is on and unlocked");
            }

        } else if (Intent.ACTION_USER_PRESENT.equals(action)) {
            Log.i(TAG, "USER_PRESENT → screen on and unlocked");
        }
    }
}

// Also Worked
// package org.wally.waller;
//
//
// import android.app.KeyguardManager;
// import android.content.BroadcastReceiver;
// import android.content.Context;
// import android.content.Intent;
// import android.util.Log;
//
// public class DetectReceiver extends BroadcastReceiver {
//
//     private static final String TAG = "DetectReceiver";
//
//     @Override
//     public void onReceive(Context context, Intent intent) {
//         if (intent == null || intent.getAction() == null) {
//             Log.i(TAG, "No intent");
//             return;
//         }
//
//         String action = intent.getAction();
//         Log.w(TAG, "Received action: " + action);
//
//         KeyguardManager km =
//                 (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
//
//         boolean isLocked = km != null && km.isKeyguardLocked();
//
//         if (Intent.ACTION_SCREEN_OFF.equals(action)) {
//             Log.i(TAG, "ACTION_SCREEN_OFF");
//
//             if (isLocked) {
//                 Log.i(TAG, "screen is locked");
//             } else {
//                 Log.i(TAG, "screen is unlocked (rare but possible)");
//             }
//
//         } else if (Intent.ACTION_SCREEN_ON.equals(action)) {
//             Log.i(TAG, "ACTION_SCREEN_ON");
//
//             if (isLocked) {
//                 Log.i(TAG, "screen is on but locked");
//             } else {
//                 Log.i(TAG, "screen is on and unlocked");
//             }
//
//         } else if (Intent.ACTION_USER_PRESENT.equals(action)) {
//             Log.i(TAG, "USER_PRESENT → screen on and unlocked");
//         }
//     }
// }
//
