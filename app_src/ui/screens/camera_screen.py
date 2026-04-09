"""
Front-Facing Camera App - with quality selector + live preview rotation (canvas transform).
Enhanced UI design with modern look & feel.
"""
import traceback

from android_notify.config import on_android_platform
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.camera import Camera
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Scale, Color, RoundedRectangle
from kivy.clock import Clock
from kivy.utils import platform
from kivy.core.text import LabelBase

import os
from datetime import datetime

# Quality presets: (label, camera_resolution, jpeg_quality, active_color)
QUALITY_PRESETS = {
    'Low':    ((320, 240),  50, (0.2, 0.6, 0.9, 1)),    # blue
    'Medium': ((640, 480),  80, (0.3, 0.8, 0.4, 1)),    # green
    'High':   ((1280, 720), 95, (0.9, 0.5, 0.2, 1)),    # orange
}
INACTIVE_COLOR = (0.3, 0.3, 0.3, 1)
BG_COLOR = (0.12, 0.12, 0.12, 1)       # dark background
BUTTON_COLOR = (0.2, 0.2, 0.2, 1)
CAPTURE_COLOR = (0.9, 0.3, 0.2, 1)      # reddish capture
FLIP_COLOR = (0.3, 0.5, 0.8, 1)         # blue flip

# Register a default font (optional, just for consistency)
#LabelBase.register(name='Roboto', fn_regular='Roboto-Regular.ttf')  # falls back to DroidSans


class RotatedCamera(Camera):
    """Camera widget that rotates and optionally mirrors the live preview."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rotation_angle = 0
        self._mirror = False
        self._transform_applied = False

    def set_preview_transform(self, angle, mirror):
        self._rotation_angle = angle
        self._mirror = mirror
        self._apply_transform()

    def _apply_transform(self):

        self.canvas.before.clear()
        self.canvas.after.clear()

        if self._rotation_angle == 0 and not self._mirror:
            return

        with self.canvas.before:
            PushMatrix()
            Rotate(angle=self._rotation_angle, origin=self.center)
            if self._mirror:
                Scale(-1, 1, origin=(self.center_x, self.center_y))

        with self.canvas.after:
            PopMatrix()

        self._transform_applied = True

    def on_size(self, *args):
        if self._transform_applied:
            self._apply_transform()

    def on_pos(self, *args):
        if self._transform_applied:
            self._apply_transform()



class RoundedButton(Button):
    """Button with rounded corners and background color."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)  # transparent
        self.background_normal = ''
        self.bind(pos=self._update_canvas, size=self._update_canvas)
        self._update_canvas()

    def _update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.app import MDApp

class CameraLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self._current_index = 1        # 1 = front on Android
        self._quality = 'Medium'
        try:
            self._build_ui()
        except Exception as e:
            print(e)
            traceback.print_exc()
        Clock.schedule_once(self._start_camera, 1.0)


    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Main background color
        self.canvas.before.add(Color(*BG_COLOR))
        self.canvas.before.add(RoundedRectangle(size=self.size, pos=self.pos))
        self.bind(size=self._update_bg, pos=self._update_bg)

        # Status label at top
        self.status_label = Label(
            text='Starting camera...',
            size_hint=(1, 0.07),
            font_size='14sp',
            color=(0.9, 0.9, 0.9, 1),
            bold=True,
        )
        self.add_widget(self.status_label)

        # Camera preview container (with rounded corners border)
        self.camera_container = MDBoxLayout(
            size_hint=(1, 1),
            padding=[0, 0],
            md_bg_color=[1,0,0,2]
        )
        with self.camera_container.canvas.before:
            Color(0.2, 1, 0.2, 1)
            self.camera_border = RoundedRectangle(size=self.camera_container.size,
                                                  pos=self.camera_container.pos,
                                                  radius=[15])
        self.camera_container.bind(size=self._update_camera_border)#, pos=self._update_camera_border)

        res = QUALITY_PRESETS[self._quality][0]
        self.camera = RotatedCamera(
            index=self._current_index,
            resolution=res,
            play=False,
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=False
        )
        self.camera_container.add_widget(self.camera)
        self.add_widget(self.camera_container)

        # Quality selection row (styled)
        quality_row = BoxLayout(
            size_hint=(1, 0.09),
            spacing=8,
            padding=[12, 4, 12, 4],
        )
        quality_label = Label(
            text='Quality:',
            size_hint_x=0.2,
            font_size='14sp',
            color=(0.9, 0.9, 0.9, 1),
            halign='right',
            valign='middle',
        )
        quality_label.bind(size=quality_label.setter('text_size'))
        quality_row.add_widget(quality_label)

        self._quality_btns = {}
        for name in ('Low', 'Medium', 'High'):
            color = QUALITY_PRESETS[name][2] if name == self._quality else INACTIVE_COLOR
            btn = RoundedButton(
                text=name,
                font_size='13sp',
                background_color=color,
                size_hint_x=0.27,
            )
            btn.bind(on_release=self._on_quality_btn)
            quality_row.add_widget(btn)
            self._quality_btns[name] = btn
        self.add_widget(quality_row)

        # Action buttons row
        btn_row = BoxLayout(
            size_hint=(1, 0.12),
            spacing=12,
            padding=[20, 8, 20, 8],
        )
        self.capture_btn = RoundedButton(
            text='CAPTURE',
            font_size='16sp',
            bold=True,
            background_color=CAPTURE_COLOR,
        )
        self.capture_btn.bind(on_release=self.capture_photo)

        self.flip_btn = RoundedButton(
            text='~FLIP',
            font_size='14sp',
            background_color=FLIP_COLOR,
        )
        self.flip_btn.bind(on_release=self.flip_camera)

        btn_row.add_widget(self.capture_btn)
        btn_row.add_widget(self.flip_btn)
        self.add_widget(btn_row)

        # Path / info label
        self.path_label = Label(
            text='',
            size_hint=(1, 0.07),
            font_size='11sp',
            color=(0.7, 0.9, 0.7, 1),
            halign='center',
            valign='middle',
        )
        self.path_label.bind(size=self.path_label.setter('text_size'))
        self.add_widget(self.path_label)

    def _update_bg(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*BG_COLOR)
            RoundedRectangle(size=self.size, pos=self.pos, radius=[0])

    def _update_camera_border(self, *args):
        self.camera_container.canvas.before.clear()
        with self.camera_container.canvas.before:
            Color(0.2, 0.2, 0.2, 1)
            RoundedRectangle(size=self.camera_container.size,
                             pos=self.camera_container.pos,
                             radius=[15])

    # ------------------------------------------------------------------
    # Quality selection
    # ------------------------------------------------------------------

    def _on_quality_btn(self, btn):
        name = btn.text
        if name == self._quality:
            return
        self._quality = name
        self._refresh_quality_btn_colors()
        self.status_label.text = f'Quality set to {name} - restarting...'
        self._set_buttons_enabled(False)
        self._release_camera()
        Clock.schedule_once(self._reopen_camera, 0.6)

    def _refresh_quality_btn_colors(self):
        for name, btn in self._quality_btns.items():
            btn.background_color = QUALITY_PRESETS[name][2] if name == self._quality else INACTIVE_COLOR

    def _set_buttons_enabled(self, enabled):
        self.capture_btn.disabled = not enabled
        self.flip_btn.disabled = not enabled
        for btn in self._quality_btns.values():
            btn.disabled = not enabled

    # ------------------------------------------------------------------
    # Camera lifecycle
    # ------------------------------------------------------------------

    def _start_camera(self, dt=None):
        try:
            res = QUALITY_PRESETS[self._quality][0]
            self.camera.resolution = res
            self.camera.index = self._current_index
            self.camera.play = True
            self._update_preview_transform()
            side = 'Front' if self._current_index == 1 else 'Back'
            self.status_label.text = f'{side} • {self._quality} ({res[0]}x{res[1]})'
        except Exception as e:
            self.status_label.text = f'Error: {e}'

    def _release_camera(self):
        try:
            self.camera.play = False
            if self.camera._camera is not None:
                self.camera._camera.stop()
                if hasattr(self.camera._camera, '_android_camera'):
                    ac = self.camera._camera._android_camera
                    if ac is not None:
                        try:
                            ac.stopPreview()
                        except Exception:
                            pass
                        try:
                            ac.release()
                        except Exception:
                            pass
                        self.camera._camera._android_camera = None
                self.camera._camera = None
        except Exception as e:
            self.status_label.text = f'Release warning: {e}'

    def _reopen_camera(self, dt):
        try:
            res = QUALITY_PRESETS[self._quality][0]
            self.camera.resolution = res
            self.camera.index = self._current_index
            self.camera.play = True
            self._update_preview_transform()
            side = 'Front' if self._current_index == 1 else 'Back'
            self.status_label.text = f'{side} • {self._quality} ({res[0]}x{res[1]})'
        except Exception as e:
            self.status_label.text = f'Error: {e}'
        finally:
            self._set_buttons_enabled(True)

    # ------------------------------------------------------------------
    # Preview rotation
    # ------------------------------------------------------------------

    def _update_preview_transform(self):
        if self._current_index == 0:   # Back camera
            angle = -90
            mirror = False
        else:                           # Front camera
            angle = 90
            mirror = False
        if on_android_platform():
            self.camera.set_preview_transform(angle, mirror)


    # ------------------------------------------------------------------
    # Flip
    # ------------------------------------------------------------------

    def flip_camera(self, *args):
        self.status_label.text = 'Switching camera...'
        self._set_buttons_enabled(False)
        self._release_camera()
        self._current_index = 0 if self._current_index == 1 else 1
        Clock.schedule_once(self._reopen_camera, 0.6)

    # ------------------------------------------------------------------
    # Capture & Save (original logic unchanged)
    # ------------------------------------------------------------------

    def capture_photo(self, *args):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            quality_name = self._quality.lower()
            png_name = f'capture_{quality_name}_{timestamp}.png'
            png_path = self._save_path(png_name)

            self.camera.export_to_png(png_path)
            final_path = self._fix_rotation_and_compress(png_path, timestamp, quality_name)

            self.status_label.text = f'Saved ({self._quality})'
            self.path_label.text = final_path
            self._scan_gallery(final_path)

        except Exception as e:
            self.status_label.text = f'Capture error: {e}'

    def _fix_rotation_and_compress(self, png_path, timestamp, quality_name):
        jpeg_quality = QUALITY_PRESETS[self._quality][1]
        try:
            from PIL import Image as PILImage
            img = PILImage.open(png_path)
            if platform == 'android':
                if self._current_index == 1:
                    img = img.rotate(90, expand=True)
                    img = img.transpose(PILImage.FLIP_LEFT_RIGHT)
                else:
                    img = img.rotate(-90, expand=True)
            jpg_name = f'capture_{quality_name}_{timestamp}.jpg'
            jpg_path = self._save_path(jpg_name)
            img.convert('RGB').save(jpg_path, 'JPEG', quality=jpeg_quality, optimize=True)
            os.remove(png_path)
            return jpg_path
        except ImportError:
            return self._rotate_png_stdlib(png_path, timestamp, quality_name)

    def _rotate_png_stdlib(self, png_path, timestamp, quality_name):
        import struct, zlib
        with open(png_path, 'rb') as f:
            data = f.read()
        def read_chunks(data):
            pos = 8
            chunks = {}
            while pos < len(data):
                length = struct.unpack('>I', data[pos:pos+4])[0]
                name = data[pos+4:pos+8].decode('ascii')
                chunk_data = data[pos+8:pos+8+length]
                chunks.setdefault(name, []).append(chunk_data)
                pos += 12 + length
            return chunks
        chunks = read_chunks(data)
        ihdr = chunks['IHDR'][0]
        w, h = struct.unpack('>II', ihdr[:8])
        bit_depth, color_type = ihdr[8], ihdr[9]
        if bit_depth != 8 or color_type not in (2, 6):
            return png_path
        channels = 4 if color_type == 6 else 3
        raw = zlib.decompress(b''.join(chunks['IDAT']))
        rows = []
        stride = 1 + w * channels
        for y in range(h):
            row_bytes = raw[y * stride + 1: (y + 1) * stride]
            rows.append([tuple(row_bytes[x*channels:(x+1)*channels]) for x in range(w)])
        if self._current_index == 1:
            new_w, new_h = h, w
            new_rows = [[rows[new_h - 1 - x][y] for x in range(new_h)] for y in range(new_w)]
            new_rows = [row[::-1] for row in new_rows]
        else:
            new_w, new_h = h, w
            new_rows = [[rows[x][new_w - 1 - y] for x in range(new_h)] for y in range(new_w)]
        def make_png(rows, width, height, channels):
            sig = b'\x89PNG\r\n\x1a\n'
            def chunk(name, data):
                c = name.encode() + data
                return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
            ct = 6 if channels == 4 else 2
            ihdr_new = struct.pack('>IIBBBBB', width, height, 8, ct, 0, 0, 0)
            raw_rows = b''
            for row in rows:
                raw_rows += b'\x00'
                for px in row:
                    raw_rows += bytes(px)
            idat = zlib.compress(raw_rows, 6)
            return sig + chunk('IHDR', ihdr_new) + chunk('IDAT', idat) + chunk('IEND', b'')
        rotated_name = f'capture_{quality_name}_{timestamp}_r.png'
        rotated_path = self._save_path(rotated_name)
        with open(rotated_path, 'wb') as f:
            f.write(make_png(new_rows, new_w, new_h, channels))
        os.remove(png_path)
        return rotated_path

    def _save_path(self, filename):
        if platform == 'android':
            base = '/storage/emulated/0/Pictures/KivyCam'
        else:
            base = os.path.join(os.path.expanduser('~'), 'Pictures', 'KivyCam')
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, filename)

    def _scan_gallery(self, filepath):
        if platform != 'android':
            return
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            MediaScannerConnection = autoclass('android.media.MediaScannerConnection')
            MediaScannerConnection.scanFile(PythonActivity.mActivity, [filepath], None, None)
        except Exception:
            pass


class FrontCameraApp(MDApp):
    def build(self):
        self.title = ' Front Camera'
        return CameraLayout()

    def on_stop(self):
        if hasattr(self.root, '_release_camera'):
            self.root._release_camera()


if __name__ == '__main__':
    FrontCameraApp().run()