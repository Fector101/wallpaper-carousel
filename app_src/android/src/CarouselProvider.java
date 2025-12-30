package org.wally.waller;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
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

public class CarouselProvider extends AppWidgetProvider {

    private static final String TAG = "CarouselProvider";

    @Override
    public void onUpdate(
            Context context,
            AppWidgetManager appWidgetManager,
            int[] appWidgetIds
    ) {

        for (int appWidgetId : appWidgetIds) {

            RemoteViews views = new RemoteViews(
                    context.getPackageName(),
                    R.layout.carousel_widget
            );

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

            if (bitmap != null) {
                // Crop bitmap to square
                int size = Math.min(bitmap.getWidth(), bitmap.getHeight());
                int x = (bitmap.getWidth() - size) / 2;
                int y = (bitmap.getHeight() - size) / 2;
                Bitmap squareBitmap = Bitmap.createBitmap(bitmap, x, y, size, size);

                // Scale bitmap to widget size
                int widgetPx = (int) (120 * context.getResources().getDisplayMetrics().density); // 120dp
                Bitmap scaledBitmap = Bitmap.createScaledBitmap(squareBitmap, widgetPx, widgetPx, true);

                // Create rounded bitmap
                Bitmap output = Bitmap.createBitmap(widgetPx, widgetPx, Bitmap.Config.ARGB_8888);
                Canvas canvas = new Canvas(output);

                Paint paint = new Paint();
                paint.setAntiAlias(true);

                Rect rect = new Rect(0, 0, widgetPx, widgetPx);
                RectF rectF = new RectF(rect);

                float cornerRadius = 16 * context.getResources().getDisplayMetrics().density; // 16dp corners
                canvas.drawARGB(0, 0, 0, 0);
                canvas.drawRoundRect(rectF, cornerRadius, cornerRadius, paint);

                paint.setXfermode(new PorterDuffXfermode(PorterDuff.Mode.SRC_IN));
                canvas.drawBitmap(scaledBitmap, rect, rect, paint);

                views.setImageViewBitmap(R.id.test_image, output);
            } else {
                Log.e(TAG, "Bitmap decode failed");
            }

            appWidgetManager.updateAppWidget(appWidgetId, views);
        }
    }
}
