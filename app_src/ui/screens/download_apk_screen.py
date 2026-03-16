import os
import threading
import time
import traceback
import requests
from android_notify.config import on_android_platform

from kivy.clock import Clock
from kivy.graphics import RoundedRectangle, Color
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, ListProperty, ObjectProperty, BooleanProperty
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButtonText, MDButton
from kivymd.uix.fitimage import FitImage
from kivymd.uix.label import MDLabel
# from kivymd.uix.relativelayout import MDRelativeLayout
from kivymd.uix.scrollview import MDScrollView

from ui.widgets.android import toast
from ui.widgets.layouts import MyMDScreen, Column, Row
from utils.constants import VERSION
from utils.logger import app_logger

def get_apk_path(version):
    folder = get_apk_directory()
    filename = get_apk_filename(version)
    return os.path.join(folder, filename)

def get_apk_directory():
    if on_android_platform():
        from android import mActivity #type: ignore
        context = mActivity.getApplicationContext()
        return context.getFilesDir().getAbsolutePath()
    return "./"

def download_apk(url, filename="waller.apk", progress_callback=None):
    """Download APK with resume support"""
    try:
        sent_percent = 0
        print("Entered download apk:", url)

        files_dir = get_apk_directory()
        apk_path = os.path.join(files_dir, filename)

        # check existing partial file
        existing_size = 0
        if os.path.exists(apk_path):
            existing_size = os.path.getsize(apk_path)
            print("Resuming download from:", existing_size)

        headers = {}
        if existing_size > 0:
            headers["Range"] = f"bytes={existing_size}-"

        r = requests.get(url, headers=headers, stream=True)
        r.raise_for_status()

        # total file size
        total_size = int(r.headers.get("content-length", 0)) + existing_size
        downloaded = existing_size

        # append mode if resuming
        mode = "ab" if existing_size > 0 else "wb"

        with open(apk_path, mode) as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size and progress_callback:
                        percent = int((downloaded / total_size) * 100)
                        if sent_percent != percent:
                            sent_percent=percent
                            progress_callback(percent)

        return apk_path

    except Exception as e:
        print("Download failed:", e)
        traceback.print_exc()
        return None

def install_apk15(apk_path):
    """Install APK using FileProvider (Android 15+)"""
    import os
    from jnius import autoclass
    from android import mActivity #type: ignore

    if not os.path.exists(apk_path):
        print("APK not found:", apk_path)
        return

    context = mActivity.getApplicationContext()
    Intent = autoclass('android.content.Intent')
    File = autoclass('java.io.File')
    FileProvider = autoclass('androidx.core.content.FileProvider')

    apk_file = File(apk_path)
    authority = context.getPackageName() + ".fileprovider"
    uri = FileProvider.getUriForFile(context, authority, apk_file)

    intent = Intent(Intent.ACTION_VIEW)
    intent.setDataAndType(uri, "application/vnd.android.package-archive")
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    mActivity.startActivity(intent)

def install_apk(apk_path):
    """Fallback installer for older Android versions"""
    import os
    from jnius import autoclass
    from android import mActivity#type: ignore

    if not os.path.exists(apk_path):
        print("APK not found:", apk_path)
        return

    Intent = autoclass('android.content.Intent')
    Uri = autoclass('android.net.Uri')
    File = autoclass('java.io.File')

    intent = Intent(Intent.ACTION_VIEW)
    apk_file = File(apk_path)
    uri = Uri.fromFile(apk_file)
    intent.setDataAndType(uri, "application/vnd.android.package-archive")
    intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    mActivity.startActivity(intent)

def do_android_install(apk_path):
    print("Called do_android_install")
    try:
        install_apk15(apk_path)
    except Exception as e:
        print("install_apk15 failed:", e)
        try:
            install_apk(apk_path)
        except Exception as e1:
            print("install_apk failed:", e1)


class TextButton(MDButton):
    text = StringProperty("")
    text_color = ListProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.txt = MDButtonText(text=self.text,
                                theme_text_color='Custom',
                                pos_hint={"center_x": .5, "center_y": .5})
        self.set_text_color(self, self.text_color)
        self.bind(text=self.set_val, text_color=self.set_text_color)
        Clock.schedule_once(self.fix_width,2)
        Clock.schedule_once(self.add_text_widget)

    def add_text_widget(self, dt=None):
        self.add_widget(self.txt)

    def set_val(self, instance, value):
        self.txt.text = value

    def set_text_color(self, instance, value):
        if not value:
            return
        self.txt.text_color = value

    def fix_width(self, *_):
        self.adjust_width()


class ProgressButton(MDBoxLayout):
    clicked=BooleanProperty(False)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = [1, None]
        self.height = dp(40)
        self.md_bg_color = [0,0,0,0]
        self.radius = 5

        self.streak = TextButton(
            text="Download APK for Upgrade",
            pos_hint={"center_x": .5},
            theme_bg_color="Custom",
            md_bg_color=get_color_from_hex("#98F1DD"),
            theme_text_color="Custom",
            text_color=get_color_from_hex("#262C3A"),
            radius=[dp(10)],

            size_hint=[1, 1],
            theme_width="Custom",
            theme_height="Custom",
            # on_release=self.function
        )
        # self.streak.bind(on_release=self.function)
        # self.bind(function=self.streak.on_release)
        self.add_widget(self.streak)
        self.layered_color = [0, 0, 0, .23]
        with self.canvas.after:
            self.bg_color_instr = Color(*self.layered_color)
            self.rect = RoundedRectangle(radius=[5, 0, 0, 5], size=[0, 0])

        self.streak.bind(size=self.update_rect, pos=self.update_rect)

    def update_rect(self, *_):
        self.rect.pos = self.pos
        # self.rect.size = [0, self.height]  # init empty
        self.rect.size = [self.width, self.height]

    def update_progress(self, percent):
        percent = min(max(percent, 0), 100)
        self.streak.text = f"Downloading {percent}%"

        if percent == 100:
            self.clicked=False
            per=self.width
            self.rect.a = 0
        else:
            per = self.width * (percent / 100)

        self.rect.size = [self.width - per, self.height]
        # print(f"time 2 {percent}")

class DownloadApkScreen(MyMDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.new_version = ''
        self.clock_for_progress_update=None
        self.apk_size = 0
        app = MDApp.get_running_app()
        self.md_bg_color = [0.9, 0.9, 0.9, 1] if app.device_theme == "light" else [.1, .1, .1, 1]
        self.name = "update_screen"

        root = Column(padding=[dp(20), dp(10)])

        # Top App Bar
        top_app_bar = Row(
            # md_bg_color=[1,0,1,1],
            size_hint_y=.2,
            pos_hint={"top": .4},
            my_widgets=[
                Row(
                    spacing=dp(10),
                    # md_bg_color=[1, 0, 0, 1],
                    adaptive_height=True,
                    pos_hint = {"top": 1},
                    my_widgets=[
                    FitImage(source="assets/icons/icon.png", size_hint=(None, None), size=(30, 30)),
                    MDLabel(text="Waller", theme_font_size="Custom", theme_text_color="Custom",  # font_size=sp(16),
                            text_color="white", bold=True, adaptive_height=True)
                ]
                )

            ]
        )

        # Body Content
        body_content = Column()


        self.h1_text_widget = MDLabel(
            text=f"Discover new version V7.51",
            theme_font_size="Custom",
            theme_text_color="Custom",
            text_color="white",
            font_size=sp(30),
            bold=True,
            adaptive_height=True,
        )
        body_content.add_widget(self.h1_text_widget)

        self.new_stuff_container = MDScrollView()
        body_content.add_widget(self.new_stuff_container)

        # Bottom Container
        bottom_container = Column(spacing=dp(10), adaptive_height=1, padding=[dp(10)])
        txt = MDLabel(text="Apk Sourced Securely from GitHub", markup=1,
                      theme_text_color="Custom", text_color="grey", pos_hint={"center_x": .5},
                      theme_font_size="Custom", font_size=sp(14), adaptive_size=1)
        bottom_container.add_widget(txt)

        self.update_button = ProgressButton()#function=lambda x: self.start_download(self.update_button))
        self.update_button.streak.bind(on_release=self.start_download)

        self.later_button = TextButton(
            text="Not now",
            pos_hint={"center_x": .5},
            theme_bg_color="Custom",
            md_bg_color=self.md_bg_color,
            theme_text_color="Custom",
            text_color=[.5, .5, .5, 1],
            on_release=lambda x: self.go_to_gallery_screen()
        )

        bottom_container.add_widget(self.update_button)
        bottom_container.add_widget(self.later_button)

        root.add_widget(top_app_bar)
        root.add_widget(body_content)
        root.add_widget(bottom_container)
        self.add_widget(root)

        Clock.schedule_once(lambda dt: thread_check_for_update(dt, self.show),3)
        # Clock.schedule_once(lambda dt: self.dev())

    def dev(self):
        print("Using hot reload...")
        # self.add_body_to_new_stuff_container(DEFAULT_RELEASE_NOTE)
        # self.show("1.0.4",DEFAULT_RELEASE_NOTE,0) # hot reload
        # self.change_download_btn_to_install(None)

    def add_body_to_new_stuff_container(self, markup_text):
        rst_widget = MDLabel(
            text=markup_text,
            theme_text_color="Custom",
            text_color="white",
            markup=1,
            pos_hint={"top": .99},
            adaptive_height=True,
        )
        self.new_stuff_container.clear_widgets()
        self.new_stuff_container.add_widget(rst_widget)

    def start_download(self,widget=None):
        print("Clicked start download...")

        if self.update_button.clicked:
            app_logger.warning("Already Clicked Download.")
            return
        self.update_button.clicked=True
        self.later_button.text = "Hide"
        def progress(percent):
            if self.clock_for_progress_update:
                self.clock_for_progress_update.cancel()
            self.clock_for_progress_update = Clock.schedule_once(lambda dt: self.update_button.update_progress(percent))
        def worker():
            apk_path__ = download_apk(
                "https://github.com/Fector101/wallpaper-carousel/releases/latest/download/waller.apk",
                progress_callback=progress,
                filename=get_apk_filename(self.new_version)
            )
            app_logger.info(f"Downloaded apk_path:{apk_path__}")
            if apk_path__:
                self.change_download_btn_to_install(apk_path__,"Tap to Install")
                # do_android_install(apk_path__)
        apk_path = get_apk_path(self.new_version)
        valid_apk = apk_is_valid(apk_path, self.apk_size)
        if valid_apk:
            self.change_download_btn_to_install(apk_path)
        else:
            progress(0)
            threading.Thread(target=worker, daemon=True).start()

    def start_install(self,widget):
        apk_path=get_apk_path(self.new_version)
        print(f"Clicked start install...:{apk_path}")
        do_android_install(apk_path)

    def change_download_btn_to_install(self,apk_path,text="Install Update"):
        app_logger.info(f"Called change btn to install: {apk_path}")
        if self.clock_for_progress_update:
            self.clock_for_progress_update.cancel()
        # print("time 1",self.update_button.streak.txt.text)
        Clock.schedule_once(lambda x: setattr(self.update_button.streak, "text", text), 1)
        # self.update_button.streak.txt.text = text

        self.update_button.streak.unbind(on_release = self.start_download)
        self.update_button.streak.bind(on_release = self.start_install)

    def change_download_btn_to_download(self,text="Download APK for Upgrade"):
        app_logger.info(f"Called change btn to download")
        Clock.schedule_once(lambda x: setattr(self.update_button.streak,"text",text),1)
        # self.update_button.streak.txt.text = text

        self.update_button.streak.bind(on_release = self.start_download)
        self.update_button.streak.unbind(on_release = self.start_install)
        # self.update_button.function = lambda x:do_android_install(apk_path)

    def go_to_gallery_screen(self):
        manager = self.manager
        if manager:
            self.manager.current = "thumbs"
        else:
            app_logger.warning("On Hot Reload Can't go to gallery screen")

    def show(self, new_version, release_notes, apk_size):
        self.disabled=True
        Clock.schedule_once(lambda dt: setattr(self, "disabled", False),1)
        self.h1_text_widget.text=f"Discover new version V{new_version}"
        self.new_version = new_version
        self.apk_size = apk_size
        self.add_body_to_new_stuff_container(release_notes)
        if self.manager:
            self.manager.current = self.name

        apk_path = get_apk_path(self.new_version)
        valid_apk = apk_is_valid(apk_path, self.apk_size)
        if valid_apk:
            self.change_download_btn_to_install(apk_path)
        else:
            self.change_download_btn_to_download()




def thread_check_for_update(dt, download_apk_screen__show,download_apk_screen__do_not_show=None):
    threading.Thread(target=check_update, args=[download_apk_screen__show,download_apk_screen__do_not_show],daemon=True).start()

def check_update(download_apk_screen__show,download_apk_screen__do_not_show=None,*args):
    """Check GitHub latest release version"""
    repo_owner = "Fector101"
    repo_name = "wallpaper-carousel"
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    release_notes = None
    latest_version = None
    apk_size = 0

    def go_to_update_screen(dt):
        download_apk_screen__show(new_version=latest_version,release_notes=release_notes,apk_size=apk_size)
    def do_not_go_to_update_screen(msg):
        if download_apk_screen__do_not_show:
            download_apk_screen__do_not_show(msg=msg)
    try:
        print("Checking for latest release version...")
        r = requests.get(api_url, timeout=10)
        r.raise_for_status()
        data = r.json()
        print("Here's data:", data)
        latest_version = data["tag_name"].lstrip("v")  # strip v prefix if any
        print("Current version:", VERSION, "Latest version:", latest_version)

        if latest_version != VERSION:
            Clock.schedule_once(lambda dt: toast("Update available!"))
            release_notes = get_release_note_txt(data,latest_version)
            apk_size = get_apk_size(data)
            Clock.schedule_once(go_to_update_screen)
        else:
            Clock.schedule_once(lambda dt: do_not_go_to_update_screen("Already up to date."))

    except requests.exceptions.ReadTimeout:
        msg_ = "Timeout Error, Slow internet Connection"
        Clock.schedule_once(lambda dt: do_not_go_to_update_screen(msg_))
        print(msg_)

    except Exception as e:
        Clock.schedule_once(lambda dt: do_not_go_to_update_screen(f"Failed:{e}"))
        traceback.print_exc()

def get_release_note_txt(data,latest_version):
    """Check GitHub latest release version"""
    release_notes = None
    file_name = f"update-note-v{latest_version}.txt"
    found_note = False
    for asset in data["assets"]:
        if asset["name"] == file_name:
            found_note = True
            url = asset["browser_download_url"]
            print("Downloading release notes:", url)
            try:
                for attempt in range(3):
                    try:
                        r = requests.get(url, timeout=10)
                        r.raise_for_status()
                        release_notes = r.text
                        break
                    except Exception as e:
                        app_logger.exception(f"Error getting release notes: {e}")
                        time.sleep(2)
            except Exception as error_getting_release_notes:
                app_logger.exception(f"Error getting release notes: {error_getting_release_notes}")
                traceback.print_exc()
            break
    if not found_note:
        app_logger.warning(f"Didn't find release notes for App-In Display '{file_name}'")
    return release_notes or DEFAULT_RELEASE_NOTE

def get_apk_filename(version):
    return f"waller-{version}.apk"

def get_apk_size(data):
    for asset in data["assets"]:
        if asset["name"].endswith(".apk"):
            size = asset["size"]
            app_logger.info(f"Found apk size for download: {size}")
            return size
    app_logger.error(f"Could not find apk size in data: {data}")
    return 0

def apk_is_valid(path, expected_size):
    if not os.path.exists(path):
        return None

    if os.path.getsize(path) == expected_size:
        return path

    # os.remove(path)
    return None

DEFAULT_RELEASE_NOTE = """[b]New Update Available[/b]

• Performance improvements
• Bug fixes
• UI refinements

Thanks for using Wallpaper Carousel!
"""

# GPT Said GitHub API rate Limit is 60 requests / hour / IP while raw file is unlimited
# TODO FOR FUTURE VERSIONS
# UPLOAD THIS FILE ON GITHUB - update.json
# {
#   "version": "1.0.4",
#   "apk": "https://github.com/Fector101/wallpaper-carousel/releases/download/v1.0.4/waller.apk",
#   "notes": "https://github.com/Fector101/wallpaper-carousel/releases/download/v1.0.4/release-note.txt"
# }
#
# def check_update_from_git_file(callback):
#
#     url = "https://raw.githubusercontent.com/Fector101/wallpaper-carousel/main/update.json"
#
#     try:
#         r = requests.get(url, timeout=10)
#         r.raise_for_status()
#
#         data = r.json()
#
#         latest_version = data["version"]
#
#         if latest_version != VERSION:
#
#             notes_url = data["notes"]
#             apk_url = data["apk"]
#
#             notes = requests.get(notes_url).text
#
#             Clock.schedule_once(
#                 lambda dt: callback(
#                     new_version=latest_version,
#                     release_notes=notes,
#                     apk_url=apk_url
#                 )
#             )
#
#     except Exception:
#         traceback.print_exc()
#