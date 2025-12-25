package org.wally.waller;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.widget.Toast;
import android.util.Log;

public class Action1 extends BroadcastReceiver {

    private static final String TAG = "Action1";

    @Override
    public void onReceive(Context context, Intent intent) {
        // Show a short popup on the screen
        Toast.makeText(context, "Wally Action1 triggered!", Toast.LENGTH_SHORT).show();

        // Log a message to Logcat
        Log.d(TAG, "BroadcastReceiver received an intent!");
    }
}