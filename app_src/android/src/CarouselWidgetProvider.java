package org.wally.waller;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.app.PendingIntent;
import android.content.Intent;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.PorterDuff;
import android.graphics.PorterDuffXfermode;
import android.util.Log;
import android.widget.RemoteViews;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

import org.wally.waller.R;

public class CarouselWidgetProvider extends AppWidgetProvider {

    private static final String TAG = "CarouselWidgetProvider";

    @Override
    public void onUpdate(
            Context context,
            AppWidgetManager appWidgetManager,
            int[] appWidgetIds
    ) {

        Log.d(TAG, "onUpdate() called, widget count=" + appWidgetIds.length);

        for (int appWidgetId : appWidgetIds) {

            Log.d(TAG, "Updating widgetId=" + appWidgetId);

            RemoteViews views = new RemoteViews(
                    context.getPackageName(),
                    R.layout.carousel_widget
            );

            // WIDGET CLICK → APP LAUNCH
            Log.d(TAG, "Resolving launch intent");

            Intent intent = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());

            if (intent == null) {
                Log.e(TAG, "Launch intent is NULL – app has no LAUNCHER activity");
            } else {
                Log.d(TAG, "Launch intent resolved: " + intent.getComponent());

                intent.setFlags(
                        Intent.FLAG_ACTIVITY_NEW_TASK |
                        Intent.FLAG_ACTIVITY_CLEAR_TOP
                );

                intent.putExtra("from_widget", true);
                Log.d(TAG, "Extra 'from_widget' added");

                PendingIntent pendingIntent = PendingIntent.getActivity(
                        context,
                        appWidgetId,
                        intent,
                        PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
                );

                Log.d(TAG, "PendingIntent created");

                views.setOnClickPendingIntent(R.id.widget_root, pendingIntent);
                views.setOnClickPendingIntent(R.id.test_image, pendingIntent);
                Log.d(TAG, "PendingIntent attached to R.id.test_image and widget");
            }

            File txtFile = new File(
                    context.getFilesDir().getAbsolutePath() + "/app/wallpaper.txt"
            );

            Log.d(TAG, "TXT file path: " + txtFile.getAbsolutePath());

            if (!txtFile.exists()) {
                Log.e(TAG, "wallpaper.txt does not exist");
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

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
            Bitmap bitmap = BitmapFactory.decodeFile(imageFile.getAbsolutePath(), opts);

            if (bitmap == null) {
                Log.e(TAG, "Bitmap decode failed");
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

            Log.d(TAG, "Bitmap decoded: " + bitmap.getWidth() + "x" + bitmap.getHeight());

            int size = Math.min(bitmap.getWidth(), bitmap.getHeight());
            int x = (bitmap.getWidth() - size) / 2;
            int y = (bitmap.getHeight() - size) / 2;

            Bitmap squareBitmap = Bitmap.createBitmap(bitmap, x, y, size, size);

            int widgetPx = (int) (120 * context.getResources().getDisplayMetrics().density);
            Bitmap scaledBitmap = Bitmap.createScaledBitmap(
                    squareBitmap,
                    widgetPx,
                    widgetPx,
                    true
            );

            Bitmap output = Bitmap.createBitmap(
                    widgetPx,
                    widgetPx,
                    Bitmap.Config.ARGB_8888
            );

            Canvas canvas = new Canvas(output);

            Paint paint = new Paint();
            paint.setAntiAlias(true);

            Rect rect = new Rect(0, 0, widgetPx, widgetPx);
            RectF rectF = new RectF(rect);

            float cornerRadius =
                    16 * context.getResources().getDisplayMetrics().density;

            canvas.drawARGB(0, 0, 0, 0);
            canvas.drawRoundRect(rectF, cornerRadius, cornerRadius, paint);

            paint.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.SRC_IN));
            canvas.drawBitmap(scaledBitmap, rect, rect, paint);

            views.setImageViewBitmap(R.id.test_image, output);

            Log.d(TAG, "Bitmap rendered and set on widget");

            // -----------------------------
            // UPDATE WIDGET
            // -----------------------------
            appWidgetManager.updateAppWidget(appWidgetId, views);
            Log.d(TAG, "Widget update pushed");
        }
    }
}
