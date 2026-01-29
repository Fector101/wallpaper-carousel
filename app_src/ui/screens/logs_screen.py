import os
from datetime import datetime
from collections import deque

from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.core.clipboard import Clipboard
from kivy.uix.screenmanager import NoTransition
from ui.widgets.android import toast
from kivymd.uix.screen import MDScreen

# ---------- CONFIG ----------
LOG_HORIZONTAL_PADDING = dp(10)
MAX_STARTUP_LINES = 500
CHUNK_SIZE = 25
UPDATE_INTERVAL = 1.0

COLORS = {
    "ERROR": get_color_from_hex("#FF5252"),
    "WARN":  get_color_from_hex("#FFB300"),
    "INFO":  get_color_from_hex("#E0E0E0"),
    # "INFO":  get_color_from_hex("#A8E4A0"), # GREEN
}


class LogsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name = "logs"
        self.md_bg_color = [0.1, 0.1, 0.1, 1]
        self._file_pos = 0
        self._line_count = 0
        self._auto_update_started = False

        # ---------- LOG FILE SETUP ----------

        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file_path = os.path.join(self.logs_dir, "all_output1.txt")

        # ---------- UI ----------
        main = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10))

        # Top bar with Start button
        top_bar = BoxLayout(size_hint_y=None, height=dp(40))
        title = Label(text="Application Logs", color=(1,1,1,1))
        top_bar.add_widget(title)
        title.font_name = "RobotoMono"

        start_btn = Button(text="Start Loading", size_hint_x=None, width=dp(90),font_size=sp(13))
        start_btn.bind(on_release=self.start_loading)

        back_btn = Button(text="Go Back", size_hint_x=None, width=dp(70),font_size=sp(13))
        back_btn.bind(on_release=self.back_to_settings_screen)

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
        add_btn = Button(text="Add Test Log")
        add_btn.bind(on_release=lambda *_: self.add_test_log())
        clear_btn = Button(text="Clear Logs")
        clear_btn.bind(on_release=lambda *_: self.clear_logs())
        buttons.add_widget(add_btn)
        buttons.add_widget(clear_btn)
        main.add_widget(buttons)

        self.add_widget(main)

        # Pending lines buffer
        self._pending_lines = []
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
    def back_to_settings_screen(self,*args):
        self.manager.transition = NoTransition()
        self.manager.current = "settings"
    def _detect_level(self, text):
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

    def add_test_log(self):
        self.add_log("INFO This is a normal log message")
        self.add_log("WARN Something looks suspicious")
        self.add_log("ERROR Something broke badly")
        self.add_log("EXCEPTION ValueError: invalid input")
        self.add_log("TRACEBACK File \"main.py\", line 42")

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
    def _update_logs(self, dt):
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
