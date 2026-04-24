package org.wally.waller;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.graphics.drawable.RippleDrawable;
import android.content.res.ColorStateList;
import android.os.Bundle;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageButton;
import android.widget.LinearLayout;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.activity.ComponentActivity;
import androidx.camera.core.Camera;
import androidx.camera.core.CameraControl;
import androidx.camera.core.CameraInfo;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.common.util.concurrent.ListenableFuture;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Locale;
import java.util.concurrent.Executor;

public class CameraActivity extends ComponentActivity {

    private static final String TAG = "CAMERA_DBG";

    public static final String EXTRA_PHOTO_PATH = "photo_path";
    private static final int REQ_CAMERA = 10;

    private PreviewView previewView;
    private ImageCapture imageCapture;
    private ProcessCameraProvider cameraProvider;
    private Executor mainExecutor;

    private Camera camera;
    private CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;

    private boolean torchOn = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.d(TAG, "onCreate");

        mainExecutor = ContextCompat.getMainExecutor(this);

        // ===== ROOT =====
        FrameLayout root = new FrameLayout(this);

        // ===== PREVIEW =====
        previewView = new PreviewView(this);
        previewView.setLayoutParams(new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
        ));
        previewView.setScaleType(PreviewView.ScaleType.FILL_CENTER);
        root.addView(previewView);

        // ===== BOTTOM BAR =====
        LinearLayout bar = new LinearLayout(this);
        bar.setOrientation(LinearLayout.HORIZONTAL);
        bar.setGravity(Gravity.CENTER);
        bar.setPadding(dp(18), dp(12), dp(18), dp(24));

        FrameLayout.LayoutParams barParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        barParams.gravity = Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
        bar.setLayoutParams(barParams);

        GradientDrawable barBg = new GradientDrawable();
        barBg.setColor(Color.parseColor("#66000000"));
        barBg.setCornerRadius(dp(28));
        bar.setBackground(barBg);

        ImageButton btnFlip = makeRoundIconButton(android.R.drawable.ic_menu_rotate, dp(44));
        ImageButton btnShoot = makeRoundIconButton(android.R.drawable.ic_menu_camera, dp(72));
        ImageButton btnTorch = makeRoundIconButton(android.R.drawable.btn_star_big_off, dp(44));

        LinearLayout.LayoutParams smallLp = new LinearLayout.LayoutParams(dp(48), dp(48));
        smallLp.leftMargin = dp(10);
        smallLp.rightMargin = dp(10);

        LinearLayout.LayoutParams bigLp = new LinearLayout.LayoutParams(dp(76), dp(76));
        bigLp.leftMargin = dp(14);
        bigLp.rightMargin = dp(14);

        bar.addView(btnFlip, smallLp);
        bar.addView(btnShoot, bigLp);
        bar.addView(btnTorch, smallLp);

        root.addView(bar);

        // ===== CLOSE =====
        ImageButton btnClose = makeRoundIconButton(android.R.drawable.ic_menu_close_clear_cancel, dp(40));
        FrameLayout.LayoutParams closeLp = new FrameLayout.LayoutParams(dp(44), dp(44));
        closeLp.gravity = Gravity.TOP | Gravity.START;
        closeLp.leftMargin = dp(12);
        closeLp.topMargin = dp(12);
        root.addView(btnClose, closeLp);

        setContentView(root);

        // ===== BUTTONS =====
        btnClose.setOnClickListener(v -> {
            Log.d(TAG, "Close clicked");
            setResult(RESULT_CANCELED);
            finish();
        });

        btnShoot.setOnClickListener(v -> {
            Log.d(TAG, "Shoot clicked");
            takePhoto();
        });

        btnFlip.setOnClickListener(v -> {
            Log.d(TAG, "Flip clicked");
            cameraSelector = (cameraSelector == CameraSelector.DEFAULT_BACK_CAMERA)
                    ? CameraSelector.DEFAULT_FRONT_CAMERA
                    : CameraSelector.DEFAULT_BACK_CAMERA;
            Log.d(TAG, "Camera switched");
            bindCameraUseCases();
        });

        btnTorch.setOnClickListener(v -> {
            Log.d(TAG, "Torch clicked");
            toggleTorch(btnTorch);
        });

        // ===== PERMISSION =====
        Log.d(TAG, "Checking permission");

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED) {
            Log.d(TAG, "Permission granted");
            startCamera();
        } else {
            Log.d(TAG, "Requesting permission");
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.CAMERA},
                    REQ_CAMERA);
        }
    }

    // ---------- Camera ----------
    private void startCamera() {
        Log.d(TAG, "startCamera");

        ListenableFuture<ProcessCameraProvider> future =
                ProcessCameraProvider.getInstance(this);

        future.addListener(() -> {
            try {
                Log.d(TAG, "CameraProvider ready");
                cameraProvider = future.get();

                previewView.post(() -> {
                    Log.d(TAG, "Binding camera");
                    bindCameraUseCases();
                });

            } catch (Exception e) {
                Log.e(TAG, "CameraProvider error", e);
                finish();
            }
        }, mainExecutor);
    }

    private void bindCameraUseCases() {
        Log.d(TAG, "bindCameraUseCases");

        if (cameraProvider == null) {
            Log.w(TAG, "cameraProvider NULL");
            return;
        }

        cameraProvider.unbindAll();

        Preview preview = new Preview.Builder().build();
        preview.setSurfaceProvider(previewView.getSurfaceProvider());

        imageCapture = new ImageCapture.Builder().build();

        try {
            camera = cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageCapture);
            Log.d(TAG, "Camera bound OK");
        } catch (Exception e) {
            Log.e(TAG, "Bind failed", e);
        }
    }

    private void takePhoto() {
        Log.d(TAG, "takePhoto");

        if (imageCapture == null) {
            Log.w(TAG, "imageCapture NULL");
            return;
        }

        File dir = new File(getCacheDir(), "captures");
        if (!dir.exists()) dir.mkdirs();

        String ts = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US)
                .format(System.currentTimeMillis());

        File file = new File(dir, "IMG_" + ts + ".jpg");
        Log.d(TAG, "Saving: " + file.getAbsolutePath());

        ImageCapture.OutputFileOptions options =
                new ImageCapture.OutputFileOptions.Builder(file).build();

        imageCapture.takePicture(options, mainExecutor, new ImageCapture.OnImageSavedCallback() {
            @Override
            public void onImageSaved(@NonNull ImageCapture.OutputFileResults output) {
                Log.d(TAG, "Photo saved");

                Intent data = new Intent();
                data.putExtra(EXTRA_PHOTO_PATH, file.getAbsolutePath());
                setResult(RESULT_OK, data);
                finish();
            }

            @Override
            public void onError(@NonNull ImageCaptureException exception) {
                Log.e(TAG, "Photo error", exception);
            }
        });
    }

    // ---------- Torch ----------
    private void toggleTorch(ImageButton btnTorch) {
        torchOn = !torchOn;
        Log.d(TAG, "Torch: " + torchOn);
        applyTorchState(btnTorch);
    }

    private void applyTorchState(ImageButton btnTorch) {
        if (camera == null) {
            Log.w(TAG, "Camera NULL for torch");
            return;
        }

        CameraInfo info = camera.getCameraInfo();
        CameraControl control = camera.getCameraControl();

        if (!info.hasFlashUnit()) {
            Log.w(TAG, "No flash");
            return;
        }

        control.enableTorch(torchOn);
    }

    // ---------- Helpers ----------
    private ImageButton makeRoundIconButton(int iconRes, int sizePx) {
        ImageButton b = new ImageButton(this);
        b.setImageResource(iconRes);
        b.setBackground(makeRoundRippleBackground());
        b.setColorFilter(Color.WHITE);
        b.setLayoutParams(new ViewGroup.LayoutParams(sizePx, sizePx));
        return b;
    }

    private Drawable makeRoundRippleBackground() {
        GradientDrawable circle = new GradientDrawable();
        circle.setShape(GradientDrawable.OVAL);
        circle.setColor(Color.parseColor("#66000000"));

        return new RippleDrawable(
                ColorStateList.valueOf(Color.parseColor("#55FFFFFF")),
                circle,
                null
        );
    }

    private int dp(int dp) {
        return (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP,
                dp,
                getResources().getDisplayMetrics()
        );
    }

    // ---------- Permission ----------
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        Log.d(TAG, "Permission result");

        if (requestCode == REQ_CAMERA) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Log.d(TAG, "Permission OK");
                startCamera();
            } else {
                Log.d(TAG, "Permission denied");
                finish();
            }
        }
    }

    // ---------- Lifecycle ----------
    @Override protected void onStart() { super.onStart(); Log.d(TAG, "onStart"); }
    @Override protected void onResume() { super.onResume(); Log.d(TAG, "onResume"); }
    @Override protected void onPause() { super.onPause(); Log.d(TAG, "onPause"); }
    @Override protected void onStop() { super.onStop(); Log.d(TAG, "onStop"); }
    @Override protected void onDestroy() { super.onDestroy(); Log.d(TAG, "onDestroy"); }
}