package org.wally.waller;

import android.content.Context;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

public class UpdateCheckWorker extends Worker {

    private static final String TAG = "UpdateCheckWorker";

    public UpdateCheckWorker(@NonNull Context context, @NonNull WorkerParameters params) {
        super(context, params);
    }

    @NonNull
    @Override
    public Result doWork() {
        Log.d(TAG, "doWork called");

        Context ctx = getApplicationContext();

        if (!UpdateNotifier.isNetworkAvailable(ctx)) {
            Log.d(TAG, "No network, retrying later");
            return Result.retry();
        }

        if (UpdateNotifier.isCooldownActive(ctx)) {
            Log.d(TAG, "Cooldown active, skipping");
            return Result.success();
        }

        return UpdateNotifier.checkAndNotify(ctx) ? Result.retry() : Result.success();
    }
}