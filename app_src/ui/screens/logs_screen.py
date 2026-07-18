import os
from datetime import datetime
from collections import deque

from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.metrics import dp, sp
from kivy.core.clipboard import Clipboard
from kivy.uix.screenmanager import NoTransition
from ui.widgets.android import toast

from ui.widgets.layouts import MyMDScreen, GenericStatusBarSpacer
from utils.constants import theme_colors

# ---------- CONFIG ----------
LOG_HORIZONTAL_PADDING = dp(10)
MAX_STARTUP_LINES = 500
CHUNK_SIZE = 25
UPDATE_INTERVAL = 1.0

COLORS = {
    "ERROR": theme_colors.LOG_ERROR,
    "WARN":  theme_colors.LOG_WARN,
    "INFO":  theme_colors.LOG_INFO,
}


class LogsScreen(MyMDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name = "logs"
        from kivymd.app import MDApp
        app = MDApp.get_running_app()
        self.md_bg_color = [0.1, 0.1, 0.1, 1]
        self._file_pos = 0
        self._line_count = 0
        self._auto_update_started = False
        self.generic_status_bar_spacer = GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
            md_bg_color=[.1, .1, .1, 1])
        self.add_widget(self.generic_status_bar_spacer)
        # ---------- LOG FILE SETUP ----------

        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file_path = os.path.join(self.logs_dir, "all_output1.txt")

        # ---------- UI ----------
        main = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))
        main.pos_hint = {"top":1}

        # Top bar with Start button
        top_bar = BoxLayout(size_hint_y=None, height=dp(40))
        self.title_label = Label(text="Application Logs", color=(1,1,1,1))
        top_bar.add_widget(self.title_label)
        self.title_label.font_name = "RobotoMono"

        start_btn = Button(text="Start Loading", size_hint_x=None, width=dp(90),font_size=sp(13))
        start_btn.bind(on_release=self.start_loading)

        back_btn = Button(text="Go Back", size_hint_x=None, width=dp(70),font_size=sp(13))
        back_btn.bind(on_release=self.handle_going_back)

        top_bar.add_widget(start_btn)
        top_bar.add_widget(back_btn )
        main.add_widget(top_bar)

        # Scroll area
        self.scroll = ScrollView(size_hint=(1,1))
        self.logs_layout = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(6), padding=(0, dp(4))
        )
        self.logs_layout.bind(minimum_height=self.logs_layout.setter("height"))
        self.scroll.add_widget(self.logs_layout)
        main.add_widget(self.scroll)

        # Buttons at bottom
        buttons = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        add_btn = Button(text="Export Logs")
        add_btn.bind(on_release=lambda *_: self.export_logs())
        clear_btn = Button(text="Clear Logs")
        clear_btn.bind(on_release=lambda *_: self.clear_logs())
        buttons.add_widget(add_btn)
        buttons.add_widget(clear_btn)
        main.add_widget(buttons)

        self.add_widget(main)

        # Pending lines buffer
        self._pending_lines = []
        app.bind(device_theme=self._set_theme)

    def _set_theme(self, _, theme):
        is_dark = theme == "dark"
        self.md_bg_color = [0.1, 0.1, 0.1, 1] if is_dark else [0.9, 0.9, 0.9, 1]
        self.generic_status_bar_spacer.md_bg_color = [0.1, 0.1, 0.1, 1] if is_dark else [0.9, 0.9, 0.9, 1]
        self.title_label.color = (1,1,1,1) if is_dark else (0,0,0,1)

    @property
    def logs_dir(self):
        try:
            from utils.helper import appFolder
            base_dir = appFolder()
            return  os.path.join(base_dir, "logs")
        except ModuleNotFoundError:
            from kivy.core.window import Window
            Window.size = (370, 700)
            return os.getcwd()

    def handle_going_back(self,*_):
        self.manager.transition = NoTransition()
        self.manager.current = "settings"

    @staticmethod
    def _detect_level(text):
        t = text.upper()
        if "ERROR" in t or "EXCEPTION" in t or "TRACEBACK" in t:
            return "ERROR"
        if "WARN" in t or "WARNING" in t:
            return "WARN"
        return "INFO"

    def _create_log_label(self, text):
        level = self._detect_level(text)
        label = Label(
            text=text,
            color=COLORS[level],
            size_hint_x=1,
            size_hint_y=None,
            halign="left",
            valign="top",
            padding=(LOG_HORIZONTAL_PADDING, dp(4)),
            font_size=sp(12),
        )

        def update_size(instance, *_):
            wrap_width = instance.width - LOG_HORIZONTAL_PADDING*2
            if wrap_width <= 0: return
            instance.text_size = (wrap_width, None)
            instance.height = instance.texture_size[1] + dp(8)

        label.bind(width=update_size)
        label.bind(texture_size=lambda i,v: setattr(i,"height", v[1]+dp(8)))

        def on_double_tap(inst, touch):
            if inst.collide_point(*touch.pos) and touch.is_double_tap:
                Clipboard.copy(inst.text)
                toast('Copied')
                return True
            return None

        label.bind(on_touch_down=on_double_tap)

        return label

    # ---------- LOG HANDLING ----------
    def add_log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_log = f"[{timestamp}] {message}"
        label = self._create_log_label(full_log)
        self.logs_layout.add_widget(label)
        with open(self.log_file_path, "a", encoding="utf-8") as f:
            f.write(full_log+"\n")
        self.scroll.scroll_y = 0

    def export_logs(self, *_):
        if not os.path.exists(self.log_file_path):
            toast("No logs to export")
            return

        from jnius import autoclass
        from android_notify.config import get_python_activity_context

        context = get_python_activity_context()

        Environment = autoclass('android.os.Environment')
        ContentValues = autoclass('android.content.ContentValues')
        BuildVersion = autoclass('android.os.Build$VERSION')
        File = autoclass('java.io.File')
        FileInputStream = autoclass('java.io.FileInputStream')

        if BuildVersion.SDK_INT >= 29:
            MediaStoreDownloads = autoclass('android.provider.MediaStore$Downloads')
            MediaColumns = autoclass('android.provider.MediaStore$MediaColumns')

            content_values = ContentValues()
            content_values.put(MediaColumns.DISPLAY_NAME, "app_logs.txt")
            content_values.put(MediaColumns.MIME_TYPE, "text/plain")
            content_values.put(MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS)

            resolver = context.getContentResolver()
            uri = resolver.insert(MediaStoreDownloads.EXTERNAL_CONTENT_URI, content_values)

            if uri:
                try:
                    input_stream = FileInputStream(File(self.log_file_path))
                    output_stream = resolver.openOutputStream(uri)

                    buffer = bytearray(8192)
                    while True:
                        length = input_stream.read(buffer)
                        if length <= 0:
                            break
                        output_stream.write(buffer, 0, length)

                    input_stream.close()
                    output_stream.close()
                    toast("Logs exported to Downloads")
                except Exception as e:
                    print("Export error:", e)
                    toast("Export failed")
            else:
                toast("Export failed")
        else:
            downloads_dir = Environment.getExternalStoragePublicDirectory(
                Environment.DIRECTORY_DOWNLOADS
            ).getAbsolutePath()
            dest_path = os.path.join(downloads_dir, "app_logs.txt")
            try:
                with open(self.log_file_path, "r") as src, open(dest_path, "w") as dst:
                    dst.write(src.read())
                MediaScannerConnection = autoclass('android.media.MediaScannerConnection')
                MediaScannerConnection.scanFile(context, [dest_path], ["text/plain"], None)
                toast("Logs exported to Downloads")
            except Exception as e:
                print("Export error:", e)
                toast("Export failed")

    def clear_logs(self):
        self.logs_layout.clear_widgets()
        with open(self.log_file_path, "w", encoding="utf-8"):
            pass
        self._file_pos = 0

    # ---------- LOADING ----------
    def load_logs_from_file(self):
        if not os.path.exists(self.log_file_path):
            self._file_pos = 0
            return
        with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = deque(f, maxlen=MAX_STARTUP_LINES)
            self._file_pos = f.tell()
        self._pending_lines = [l.rstrip() for l in lines if l.strip()]
        Clock.schedule_once(self._load_next_chunk, 0)

    def _load_next_chunk(self, *_):
        if not self._pending_lines:
            self.scroll.scroll_y = 0
            return
        for _ in range(min(CHUNK_SIZE, len(self._pending_lines))):
            line = self._pending_lines.pop(0)
            label = self._create_log_label(line)
            self.logs_layout.add_widget(label)
        Clock.schedule_once(self._load_next_chunk, 0)

    # ---------- AUTO UPDATE ----------
    def _update_logs(self, _):
        if not os.path.exists(self.log_file_path): return
        with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(self._file_pos)
            new_lines = f.readlines()
            self._file_pos = f.tell()

        for line in new_lines:
            line = line.rstrip()
            if line:
                label = self._create_log_label(line)
                self.logs_layout.add_widget(label)

        if new_lines: self.scroll.scroll_y = 0

    # ---------- START BUTTON ----------
    def start_loading(self, *_):
        if not self._auto_update_started:
            self.load_logs_from_file()
            Clock.schedule_interval(self._update_logs, UPDATE_INTERVAL)
            self._auto_update_started = True

if __name__ == "__main__":
    from kivymd.app import MDApp
    class LogsApp(MDApp):
        def build(self):
            return LogsScreen()
    LogsApp().run()
