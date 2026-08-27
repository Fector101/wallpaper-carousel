package org.wally.waller;

import android.content.Context;

import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;

import java.util.concurrent.TimeUnit;

public class WorkScheduler {

    public static final String WORK_TAG = "update_check_work";

    public static void scheduleUpdateCheck(Context context) {
        Constraints constraints = new Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build();

        // PeriodicWorkRequest workRequest = new PeriodicWorkRequest.Builder(
        //         UpdateCheckWorker.class, 15, TimeUnit.MINUTES)  // TODO: testing interval
        //         .setConstraints(constraints)
        //         .addTag(WORK_TAG)
        //         .build();

        PeriodicWorkRequest workRequest = new PeriodicWorkRequest.Builder(
                UpdateCheckWorker.class, 7, TimeUnit.DAYS)
                .setConstraints(constraints)
                .addTag(WORK_TAG)
                .build();

        WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                        WORK_TAG,
                        ExistingPeriodicWorkPolicy.KEEP,
                        workRequest);
    }
}