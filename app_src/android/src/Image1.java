package org.wally.waller;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.Log;
import android.widget.RemoteViews;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

import org.wally.waller.R;

public class Image1 extends AppWidgetProvider {

    private static final String TAG = "Image1";

    @Override
    public void onUpdate(
            Context context,
            AppWidgetManager appWidgetManager,
            int[] appWidgetIds
    ) {

        for (int appWidgetId : appWidgetIds) {

            RemoteViews views = new RemoteViews(
                    context.getPackageName(),
                    R.layout.image_test_widget
            );

            // Path to wallpaper.txt
            File txtFile = new File(
                    context.getFilesDir().getAbsolutePath() + "/app/wallpaper.txt"
            );

            Log.d(TAG, "TXT file path: " + txtFile.getAbsolutePath());

            if (!txtFile.exists()) {
                Log.e(TAG, "wallpaper.txt does not exist");
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

            // Read image path from text file
            String imagePath = null;

            try (BufferedReader br = new BufferedReader(new FileReader(txtFile))) {
                imagePath = br.readLine();
            } catch (IOException e) {
                Log.e(TAG, "Failed to read wallpaper.txt", e);
            }

            if (imagePath == null || imagePath.trim().isEmpty()) {
                Log.e(TAG, "Image path is empty");
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

            File imageFile = new File(imagePath.trim());

            Log.d(TAG, "Resolved image path: " + imageFile.getAbsolutePath());

            if (!imageFile.exists()) {
                Log.e(TAG, "Image file does not exist");
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

            // Decode bitmap safely (widgets are memory-sensitive)
            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inSampleSize = 4; // reduce memory usage

            Bitmap bitmap = BitmapFactory.decodeFile(
                    imageFile.getAbsolutePath(),
                    opts
            );

            if (bitmap != null) {
                views.setImageViewBitmap(
                        R.id.test_image,
                        bitmap
                );
            } else {
                Log.e(TAG, "Bitmap decode failed");
            }

            appWidgetManager.updateAppWidget(
                    appWidgetId,
                    views
            );
        }
    }
}
