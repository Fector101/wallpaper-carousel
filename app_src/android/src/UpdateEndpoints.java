package org.wally.waller;

import android.content.Context;
import android.util.Log;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;

/**
 * Where the update checker looks for the latest release.
 *
 * Defaults to the real GitHub release, but honours {@code <filesDir>/update_endpoint.json}
 * when that file exists, which points the checker at a laptop-hosted release server so
 * the download path can be tested without GitHub. The Python side reads the same file
 * (see get_update_endpoint_config in ui/screens/download_apk_screen.py).
 */
public final class UpdateEndpoints {

    private static final String TAG = "UpdateEndpoints";
    private static final String ENDPOINT_FILE = "update_endpoint.json";
    static final String DEFAULT_API_URL =
            "https://api.github.com/repos/Fector101/wallpaper-carousel/releases/latest";
    static final String DEFAULT_BASE_URL =
            "https://github.com/Fector101/wallpaper-carousel/releases/download";

    private UpdateEndpoints() {
    }

    static String endpointFilePath(Context context) {
        return new File(context.getFilesDir(), ENDPOINT_FILE).getAbsolutePath();
    }

    private static JSONObject readOverride(Context context) {
        if (context == null) {
            return null;
        }
        File file = new File(context.getFilesDir(), ENDPOINT_FILE);
        if (!file.exists()) {
            return null;
        }
        try (InputStream in = new FileInputStream(file)) {
            byte[] buffer = new byte[(int) file.length()];
            int read = 0;
            while (read < buffer.length) {
                int n = in.read(buffer, read, buffer.length - read);
                if (n < 0) {
                    break;
                }
                read += n;
            }
            JSONObject json = new JSONObject(new String(buffer, 0, read, "UTF-8"));
            Log.i(TAG, "Using update endpoint override at " + file.getAbsolutePath());
            return json;
        } catch (Exception e) {
            Log.e(TAG, "Ignoring unreadable " + ENDPOINT_FILE, e);
            return null;
        }
    }

    static String getApiUrl(Context context) {
        try {
            JSONObject override = readOverride(context);
            if (override != null) {
                String url = override.optString("api_url", "");
                if (!url.isEmpty()) {
                    return url;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to read api_url override", e);
        }
        return DEFAULT_API_URL;
    }

    static String getBaseUrl(Context context) {
        try {
            JSONObject override = readOverride(context);
            if (override != null) {
                String url = override.optString("base_url", "");
                if (!url.isEmpty()) {
                    return url;
                }
            }
        } catch (Exception e) {
            Log.e(TAG, "Failed to read base_url override", e);
        }
        return DEFAULT_BASE_URL;
    }

    public static boolean hasOverride(Context context) {
        return context != null && new File(context.getFilesDir(), ENDPOINT_FILE).exists();
    }

    static String releaseNotesUrl(Context context, String version) {
        return getBaseUrl(context) + "/v" + version + "/update-note-v" + version + ".txt";
    }
}