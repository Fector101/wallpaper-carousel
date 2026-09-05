package org.wally.waller;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.app.PendingIntent;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
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

import android.content.ComponentName;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;

import org.wally.waller.R;

/**
 * A widget that shows one fixed image pinned by the user from the app.
 * The image per widget instance is stored in the widget_images table of the
 * app's image_history.db (app_widget_id -> image_path).
 */
public class ImageWidgetProvider extends AppWidgetProvider {

    private static final String TAG = "ImageWidgetProvider";

    private static final Object LOG_LOCK = new Object();

    private static final String DB_NAME = "image_history.db";
    private static final String TABLE_WIDGET_IMAGES = "widget_images";
    private static final String PENDING_WIDGET_IMAGE = "pending_widget_image.txt";

    /**
     * Append a diagnostic line to the app's on-device log file
     * (external files dir /logs/all_output1.txt), the same file the in-app
     * Logs screen tails, so widget reversion events surface there too.
     */
    private void appendAppLog(Context context, String message) {
        synchronized (LOG_LOCK) {
            FileOutputStream fos = null;
            try {
                File logsDir = new File(context.getExternalFilesDir(null), "logs");
                if (!logsDir.exists()) {
                    logsDir.mkdirs();
                }
                fos = new FileOutputStream(new File(logsDir, "all_output1.txt"), true);
                String ts = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
                        .format(new java.util.Date());
                fos.write((ts + " [ImageWidgetProvider] " + message + "\n")
                        .getBytes("UTF-8"));
            } catch (Exception e) {
                Log.e(TAG, "appendAppLog failed", e);
            } finally {
                if (fos != null) {
                    try {
                        fos.close();
                    } catch (IOException ignored) {
                    }
                }
            }
        }
    }

    @Override
    public void onUpdate(
            Context context,
            AppWidgetManager appWidgetManager,
            int[] appWidgetIds
    ) {
        Log.d(TAG, "onUpdate() called, widget count=" + appWidgetIds.length);

        for (int appWidgetId : appWidgetIds) {

            Log.d(TAG, "Updating image widgetId=" + appWidgetId);

            RemoteViews views = new RemoteViews(
                    context.getPackageName(),
                    R.layout.carousel_widget
            );

            String imagePath = getWidgetImagePath(context, appWidgetId);
            File imageFile = (imagePath == null || imagePath.trim().isEmpty())
                    ? null
                    : new File(imagePath.trim());
            boolean hasValidImage = imageFile != null && imageFile.exists();

            Intent intent = new Intent(Intent.ACTION_MAIN);
            intent.setComponent(new ComponentName(context, "org.kivy.android.PythonActivity"));
            intent.addCategory(Intent.CATEGORY_LAUNCHER);
            intent.setFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK |
                    Intent.FLAG_ACTIVITY_CLEAR_TOP
            );
            intent.putExtra("from_widget", true);
            intent.putExtra("app_widget_id", appWidgetId);
            intent.putExtra("widget_provider", "ImageWidgetProvider");
            if (hasValidImage) {
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

            if (!hasValidImage) {
                String why = (imagePath == null || imagePath.trim().isEmpty())
                        ? "no_db_mapping"
                        : ("mapped_file_missing path=" + imagePath.trim());
                Log.e(TAG, "No image for widgetId=" + appWidgetId + " (" + why + ")");
                appendAppLog(context, "RENDER->PLACEHOLDER widgetId=" + appWidgetId + " " + why);
                views.setViewVisibility(R.id.test_image, View.GONE);
                views.setViewVisibility(R.id.placeholder_text, View.VISIBLE);
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

            appendAppLog(context, "RENDER->image widgetId=" + appWidgetId + " path=" + imagePath.trim());

            Log.d(TAG, "Resolved image path: " + imageFile.getAbsolutePath());

            BitmapFactory.Options opts = new BitmapFactory.Options();
            opts.inSampleSize = 4; // reduce memory usage
            Bitmap bitmap = BitmapFactory.decodeFile(imageFile.getAbsolutePath(), opts);

            if (bitmap == null) {
                Log.e(TAG, "Bitmap decode failed");
                appendAppLog(context, "RENDER->PLACEHOLDER widgetId=" + appWidgetId
                        + " bitmap_decode_failed path=" + imageFile.getAbsolutePath());
                appWidgetManager.updateAppWidget(appWidgetId, views);
                continue;
            }

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
            Log.d(TAG, "Bitmap rendered and set on image widget");
            views.setViewVisibility(R.id.test_image, View.VISIBLE);
            views.setViewVisibility(R.id.placeholder_text, View.GONE);

            appWidgetManager.updateAppWidget(appWidgetId, views);
            Log.d(TAG, "Image widget pushed");
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
            Log.d(TAG, "Cleaned up widget_images for deleted widgets");
        } catch (Exception e) {
            Log.e(TAG, "Failed to clean up widget_images", e);
        } finally {
            if (db != null && db.isOpen()) {
                db.close();
            }
        }
        super.onDeleted(context, appWidgetIds);
    }

    private String readText(File file) {
        if (!file.exists()) {
            return null;
        }
        try (BufferedReader br = new BufferedReader(new FileReader(file))) {
            String line = br.readLine();
            return line == null ? null : line.trim();
        } catch (IOException e) {
            Log.e(TAG, "Failed to read " + file.getName(), e);
            return null;
        }
    }

    /**
     * Resolves the fixed image for a widget:
     * 1. Existing mapping in the widget_images DB table.
     * 2. A pending image written by the app right before pinning (claimed once).
     * 3. Otherwise null (widget shows placeholder).
     */
    private String getWidgetImagePath(Context context, int appWidgetId) {
        File dbFile = new File(context.getFilesDir(), DB_NAME);
        Log.d(TAG, "getWidgetImagePath widgetId=" + appWidgetId
                + " db=" + dbFile.getAbsolutePath() + " dbExists=" + dbFile.exists());
        if (!dbFile.exists()) {
            Log.e(TAG, "DB_MISSING for widgetId=" + appWidgetId + " -> placeholder");
            appendAppLog(context, "DB_MISSING widgetId=" + appWidgetId + " -> placeholder");
            return null;
        }

        String resolved = null;
        Exception lastError = null;
        for (int attempt = 1; attempt <= 3 && resolved == null; attempt++) {
            try {
                resolved = resolveWidgetImagePath(context, appWidgetId);
            } catch (Exception e) {
                lastError = e;
                Log.e(TAG, "resolve attempt " + attempt + "/3 failed for widgetId="
                        + appWidgetId, e);
                if (attempt < 3) {
                    try {
                        Thread.sleep(150L * attempt);
                    } catch (InterruptedException ie) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            }
        }
        if (resolved == null && lastError != null) {
            appendAppLog(context, "DB_EXCEPTION widgetId=" + appWidgetId + " "
                    + lastError.toString() + " after 3 attempts");
        }
        return resolved;
    }

    /**
     * Single DB round-trip for the widget mapping; transient busy/lock errors
     * are retried by getWidgetImagePath.
     */
    private String resolveWidgetImagePath(Context context, int appWidgetId) throws Exception {
        SQLiteDatabase db = null;
        try {
            db = SQLiteDatabase.openDatabase(
                    new File(context.getFilesDir(), DB_NAME).getAbsolutePath(),
                    null, SQLiteDatabase.OPEN_READWRITE
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
                    String found = cursor.getString(0);
                    Log.d(TAG, "ROW_FOUND widgetId=" + appWidgetId + " path=" + found);
                    return found;
                }
                Log.e(TAG, "ROW_NOT_FOUND for widgetId=" + appWidgetId + " -> pending fallback");
            } finally {
                if (cursor != null) {
                    cursor.close();
                }
            }
            File pendingFile = new File(context.getFilesDir(), PENDING_WIDGET_IMAGE);
            if (!pendingFile.exists()) {
                Log.e(TAG, "NO_PENDING_FILE for widgetId=" + appWidgetId + " -> placeholder");
                appendAppLog(context, "ROW_NOT_FOUND+NO_PENDING widgetId=" + appWidgetId + " -> placeholder");
                return null;
            }
            String pending = readText(pendingFile);
            if (pending == null || pending.trim().isEmpty()) {
                Log.e(TAG, "PENDING_EMPTY for widgetId=" + appWidgetId + " -> placeholder");
                appendAppLog(context, "PENDING_EMPTY widgetId=" + appWidgetId + " -> placeholder");
                return null;
            }
            ContentValues values = new ContentValues();
            values.put("app_widget_id", appWidgetId);
            values.put("image_path", pending);
            db.insertWithOnConflict(
                    TABLE_WIDGET_IMAGES, null, values, SQLiteDatabase.CONFLICT_REPLACE
            );
            pendingFile.delete();
            Log.d(TAG, "Claimed pending image for widgetId=" + appWidgetId + " -> " + pending);
            appendAppLog(context, "PENDING_CLAIMED widgetId=" + appWidgetId + " -> " + pending);
            return pending;
        } finally {
            if (db != null && db.isOpen()) {
                db.close();
            }
        }
    }
}