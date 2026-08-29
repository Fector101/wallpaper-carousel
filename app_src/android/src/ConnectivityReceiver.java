package org.wally.waller;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

public class ConnectivityReceiver extends BroadcastReceiver {

    private static final String TAG = "ConnectivityReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        Log.d(TAG, "onReceive called, action=" + intent.getAction());

        if (UpdateNotifier.isCooldownActive(context)) {
            Log.d(TAG, "Cooldown active, skipping");
            return;
        }

        Log.d(TAG, "Cooldown passed, checking for update in background");
        new Thread(() -> UpdateNotifier.checkAndNotify(context)).start();
    }
}