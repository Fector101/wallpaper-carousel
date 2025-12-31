import os
from datetime import datetime
from collections import deque

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.core.clipboard import Clipboard

from kivymd.uix.screen import MDScreen
from utils.helper import makeDownloadFolder

# ---------- CONFIG ----------
LOG_HORIZONTAL_PADDING = dp(10)
MAX_STARTUP_LINES = 500     # load only last N lines
CHUNK_SIZE = 25             # labels added per frame

COLORS = {
    "ERROR": get_color_from_hex("#FF5252"),
    "WARN":  get_color_from_hex("#FFB300"),
    "INFO":  get_color_from_hex("#E0E0E0"),
}


class LogsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name = "logs"
        self.md_bg_color = [0.1, 0.1, 0.1, 1]

        # ---------- LOG FILE SETUP ----------
        base_dir = makeDownloadFolder()
        self.logs_dir = os.path.join(base_dir, "logs")
        os.makedirs(self.logs_dir, exist_ok=True)
        self.log_file_path = os.path.join(self.logs_dir, "all_output1.txt")

        # ---------- UI ----------
        main = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10),
        )

        title = Label(
            text="Application Logs",
            size_hint_y=None,
            height=dp(40),
            color=(1,1,1,1),
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda i,_: setattr(i,"text_size",(i.width,None)))
        main.add_widget(title)

        self.scroll = ScrollView(size_hint=(1,1))

        self.logs_layout = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=dp(6),
            padding=(0, dp(4)),
        )
        self.logs_layout.bind(minimum_height=self.logs_layout.setter("height"))

        self.scroll.add_widget(self.logs_layout)
        main.add_widget(self.scroll)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10),
        )

        add_btn = Button(text="Add Test Log")
        add_btn.bind(on_release=lambda *_: self.add_test_log())

        clear_btn = Button(text="Clear Logs")
        clear_btn.bind(on_release=lambda *_: self.clear_logs())

        buttons.add_widget(add_btn)
        buttons.add_widget(clear_btn)
        main.add_widget(buttons)

        self.add_widget(main)

        # ---------- LOAD LOGS ----------
        self._pending_lines = []
        self.load_logs_from_file()

    # ---------- HELPERS ----------
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
        )
        label.font_size = sp(12)

        # height auto-adjust
        def update_size(instance, *_):
            wrap_width = instance.width - LOG_HORIZONTAL_PADDING*2
            if wrap_width <= 0:
                return
            instance.text_size = (wrap_width, None)
            instance.height = instance.texture_size[1] + dp(8)
        label.bind(width=update_size)
        label.bind(texture_size=lambda i,v: setattr(i,"height", v[1]+dp(8)))

        # Double-tap to copy
        def on_double_tap(inst, touch):
            if inst.collide_point(*touch.pos) and touch.is_double_tap:
                Clipboard.copy(inst.text)
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
            f.write(full_log + "\n")

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

    # ---------- NON-BLOCKING FILE LOAD ----------
    def load_logs_from_file(self):
        if not os.path.exists(self.log_file_path):
            return
        with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = deque(f, maxlen=MAX_STARTUP_LINES)
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


# ---------- STANDALONE TEST ----------



if __name__ == "__main__":
    from kivymd.app import MDApp
    class LogsApp(MDApp):
        def build(self):
            return LogsScreen()
    LogsApp().run()
