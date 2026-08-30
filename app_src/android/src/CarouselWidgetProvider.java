// package app.vercel.androidnotify;
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
import android.view.View;
import android.util.TypedValue;
import android.graphics.Color;

import android.content.ComponentName;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

// import app.vercel.androidnotify.R;
import org.wally.waller.R;

public class CarouselWidgetProvider extends AppWidgetProvider {

    private static final String TAG = "CarouselWidgetProvider";

    private static final String DB_NAME = "image_history.db";
    private static final String TABLE_WIDGET_IMAGES = "widget_images";

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

            // Per-widget image assigned from the app's file chooser takes
            // priority; otherwise fall back to the shared wallpaper.txt.
            String imagePath = getWidgetImagePath(context, appWidgetId);
            if (imagePath == null) {
                File txtFile = new File(
                        context.getFilesDir().getAbsolutePath() + "/wallpaper.txt"
                );
                if (txtFile.exists()) {
                    try (BufferedReader br = new BufferedReader(new FileReader(txtFile))) {
                        imagePath = br.readLine();
                    } catch (IOException e) {
                        Log.e(TAG, "Failed to read wallpaper.txt", e);
                    }
                } else {
                    Log.e(TAG, "wallpaper.txt does not exist");
                }
            }

            // WIDGET CLICK → APP LAUNCH (explicit intent works even when app is force-stopped)
            // If we have a valid image, open it in the app's fullscreen viewer.
            // Widgets added from outside the app (long-press app icon → Widgets)
            // have no image yet, so open the file chooser instead.
            File resolvedImageFile = (imagePath != null && !imagePath.trim().isEmpty())
                    ? new File(imagePath.trim())
                    : null;

            Intent intent = new Intent(Intent.ACTION_MAIN);
            intent.setComponent(new ComponentName(context, "org.kivy.android.PythonActivity"));
            intent.addCategory(Intent.CATEGORY_LAUNCHER);
            intent.setFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK |
                    Intent.FLAG_ACTIVITY_CLEAR_TOP
            );
            intent.putExtra("from_widget", true);
            intent.putExtra("app_widget_id", appWidgetId);
            intent.putExtra("widget_provider", "CarouselWidgetProvider");
            if (resolvedImageFile != null && resolvedImageFile.exists()) {
                intent.putExtra("action", "open_widget_image");
                intent.putExtra("image_path", imagePath.trim());
            } else {
                intent.putExtra("action", "open_widget_picker");
            }

            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
                flags |= PendingIntent.FLAG_IMMUTABLE;
            }
            PendingIntent pendingIntent = PendingIntent.getActivity(context, appWidgetId, intent, flags);

            views.setOnClickPendingIntent(R.id.widget_root, pendingIntent);
            views.setOnClickPendingIntent(R.id.test_image, pendingIntent);
            Log.d(TAG, "PendingIntent set for widgetId=" + appWidgetId);

            if (resolvedImageFile == null) {
                Log.e(TAG, "Image path is empty");
                // Show placeholder text, hide image
                views.setViewVisibility(R.id.test_image, View.GONE);
                views.setViewVisibility(R.id.placeholder_text, View.VISIBLE);
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

            File imageFile = resolvedImageFile;

            Log.d(TAG, "Resolved image path: " + imageFile.getAbsolutePath());

            if (!imageFile.exists()) {
                Log.e(TAG, "Image file does not exist");
                views.setViewVisibility(R.id.test_image, View.GONE);
                views.setViewVisibility(R.id.placeholder_text, View.VISIBLE);
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
            // Show image, hide placeholder
            views.setViewVisibility(R.id.test_image, View.VISIBLE);
            views.setViewVisibility(R.id.placeholder_text, View.GONE);

            // UPDATE WIDGET
            appWidgetManager.updateAppWidget(appWidgetId, views);
            Log.d(TAG, "Widget update pushed");
        }
    }

    @Override
    public void onDeleted(Context context, int[] appWidgetIds) {
        File dbFile = new File(context.getFilesDir(), DB_NAME);
        if (!dbFile.exists()) {
            return;
        }
        SQLiteDatabase db = null;
        try {
            db = SQLiteDatabase.openDatabase(
                    dbFile.getAbsolutePath(), null, SQLiteDatabase.OPEN_READWRITE
            );
            for (int appWidgetId : appWidgetIds) {
                db.delete(TABLE_WIDGET_IMAGES, "app_widget_id = ?",
                        new String[]{String.valueOf(appWidgetId)});
            }
            Log.d(TAG, "Cleaned up widget_images for deleted carousel widgets");
        } catch (Exception e) {
            Log.e(TAG, "Failed to clean up widget_images", e);
        } finally {
            if (db != null && db.isOpen()) {
                db.close();
            }
        }
        super.onDeleted(context, appWidgetIds);
    }

    /**
     * Resolves a per-widget image assigned via the app's file chooser:
     * 1. Existing mapping in the widget_images DB table.
     * 2. Otherwise null (caller falls back to wallpaper.txt).
     */
    private String getWidgetImagePath(Context context, int appWidgetId) {
        File dbFile = new File(context.getFilesDir(), DB_NAME);
        if (!dbFile.exists()) {
            return null;
        }
        SQLiteDatabase db = null;
        try {
            db = SQLiteDatabase.openDatabase(
                    dbFile.getAbsolutePath(), null, SQLiteDatabase.OPEN_READWRITE
            );
            db.execSQL("CREATE TABLE IF NOT EXISTS " + TABLE_WIDGET_IMAGES +
                    " (app_widget_id INTEGER PRIMARY KEY, image_path TEXT NOT NULL)");
            Cursor cursor = null;
            try {
                cursor = db.rawQuery(
                        "SELECT image_path FROM widget_images WHERE app_widget_id = ?",
                        new String[]{String.valueOf(appWidgetId)}
                );
                if (cursor.moveToFirst()) {
                    return cursor.getString(0);
                }
            } finally {
                if (cursor != null) {
                    cursor.close();
                }
            }
            return null;
        } catch (Exception e) {
            Log.e(TAG, "Error resolving widget image", e);
            return null;
        } finally {
            if (db != null && db.isOpen()) {
                db.close();
            }
        }
    }
}
