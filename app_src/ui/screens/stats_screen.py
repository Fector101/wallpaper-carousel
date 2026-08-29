import os
import traceback

from ui.widgets.generic import LineDivider
from utils.boot_log import boot_log
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.utils import get_color_from_hex
from kivy.metrics import dp

from ui.widgets.layouts import MyMDScreen, GenericStatusBarSpacer, Row, Column
from ui.widgets.modals import DialogScreen
from utils.config_manager import ConfigManager
from utils.constants import theme_colors
from utils.database import ImageDatabase
from utils.helper import appFolder, format_size, get_folder_size, get_files_size


class StatsListItem(Row):
    title = StringProperty()
    size_txt = StringProperty()
    button_text = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from ui.widgets.modals import MyTextButton
        from kivymd.uix.label import MDLabel
        grey_color=get_color_from_hex("999898")
        self.spacing=dp(10)
        self.title_label = MDLabel(
            text=self.title,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            theme_font_size="Custom", font_size="15sp",
            adaptive_height=True, pos_hint={"center_y": 0.5},
        )
        self.size_label = MDLabel(
            text=self.size_txt,theme_text_color="Custom", text_color=grey_color,
            theme_font_name="Custom", font_name = "RobotoMono",
            theme_font_size="Custom", font_size="13sp",
            adaptive_height=True, pos_hint={"center_y": 0.5},
            halign="right"
        )

        # 1. Create a wrapper to isolate and center the button horizontally

        button_container = Row(
            # anchor_x="center", anchor_y="center",
            # pos_hint={"right":1},
            # halign = "right",
            # md_bg_color=[1,0,1,1],
            pos_hint={"center_y": 0.5},
            adaptive_size=1
        )

        self.button = MyTextButton(
            style="outlined",
            theme_line_color="Custom",
            line_color=grey_color,
            radius=[30, ],
            text=self.button_text,
            adaptive_size=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            font_name="RobotoMono",
            theme_font_size="Custom", font_size="12sp",
            bold=1,size_padding=dp(10)

            # padding=[4, ]
        )
        self.button.height=dp(30)
        button_container.add_widget(self.button)
        self.add_widget(self.title_label)
        self.add_widget(self.size_label)
        self.add_widget(button_container)  # This acts as the third centered column

        # self.md_bg_color = (random.random(), random.random(), random.random(), 1)
        # self.adaptive_height=10
        self.padding=[10,0]
        self.size_hint_y=None
        self.height = dp(40)
        self.bind(size_txt=lambda _,v: setattr(self.size_label, "text", v))


class StatsScreen(MyMDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "stats"
        self.graph_title = None
        self.storage_chart = None
        self.graph_container = None
        self.sub_text_4 = None
        self.sub_text_5 = None
        self.section_title_2 = None
        self.section_layout_2 = None
        self.sub_text_1 = None
        self.sub_text_2 = None
        self.sub_text_3 = None
        self.section_title_1 = None
        self.header_btn_2 = None
        self.header_label = None
        self.header_btn = None
        self.header_section = None
        self.status_bar_spacer = None
        self.section_layout = None
        self.built_ui = False
        self.md_bg_color = theme_colors.BG

    def on_enter(self, *args):
        super().on_enter(*args)
        if not self.built_ui:
            Clock.schedule_once(self._timer_set)
        else:
            Clock.schedule_once(self.refresh_storage_data,0)

    def _timer_set(self,_):
        Clock.schedule_once(self.build_ui)

    def build_ui(self,_):
        if self.built_ui:
            return
        self.built_ui = True

        from kivy.uix.scrollview import ScrollView
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.label import MDLabel

        # Horizontal inset (per side) of section content inside sections_container.
        # The graph width binding subtracts both sides (2 * this) from the container
        # width, and the section paddings below use the same per-side value.
        content_inset = dp(25)

        self.status_bar_spacer = GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
            md_bg_color=[.1, .1, .1, 1]
        )
        self.header_section = Row(
            pos_hint = {'center_y': 1},
            adaptive_height = True,
            # md_bg_color = [.1, .1, 1, 1],
            spacing = dp(10),
            padding=10,
        )
        self.header_btn = MDIconButton(
                    icon="chevron-left",
                    style="tonal",
                    size=(dp(70), dp(70)),
                    pos_hint={'center_y': 0.5},
                    theme_text_color='Custom',
                    text_color=[1, 1, 1, 1],
                    on_release=self.handle_going_back,
                    theme_bg_color='Custom'
                )
        self.header_label = MDLabel(
                                text="Manage Storage",
                                theme_text_color="Custom", text_color=(1, 1, 1, 1),
                                theme_font_name="Custom", font_name = "RobotoMono",
                                adaptive_size=True, pos_hint={"center_y":.5},
                                bold=True,
                                # md_bg_color=[1,0,0,1]

                        )
        self.header_label.theme_width="Custom"
        self.header_label.size_hint_x=1


        self.header_btn_2 = MDIconButton(
            icon="refresh",
            style="tonal",
            size=(dp(70), dp(70)),
            pos_hint={'center_y': 0.45},
            theme_text_color='Custom',
            text_color=[1, 1, 1, 1],
            on_release=self.refresh_storage_data,
            theme_bg_color='Custom'
        )

        # Scroll area
        scroll = ScrollView(size_hint=(1, 1))
        sections_container = Column(
            # md_bg_color=[1, .4, .4, 1],
            size_hint_y=None,
            spacing=dp(6),
            padding=(0, dp(10))
        )
        sections_container.bind(minimum_height=sections_container.setter("height"))

        self.section_layout = Column(
                                     # padding=[10,10],
                                     adaptive_height=True,
                                     spacing=dp(10),
                                    padding=[content_inset, 10, content_inset, 20],

            # md_bg_color=[1, 1, .1, 1]
                                     )
        self.section_title_1= MDLabel(
            text="Pictures",bold=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            adaptive_height=1,
            # padding=[20,10]

        )
        self.sub_text_1 = StatsListItem(title="Both", size_txt="70KB",button_text="Remove")
        self.sub_text_2 = StatsListItem(title="Day", size_txt="5MB",button_text="Remove")
        self.sub_text_3 = StatsListItem(title="Noon", size_txt="200KB",button_text="Remove")
        self.sub_text_1.button.bind(on_release=lambda *_: self._remove_wallpapers("wallpapers", "Both"))
        self.sub_text_2.button.bind(on_release=lambda *_: self._remove_wallpapers("day_wallpapers", "Day"))
        self.sub_text_3.button.bind(on_release=lambda *_: self._remove_wallpapers("noon_wallpapers", "Noon"))
        self.sub_text_3.padding=[10,0,10,10]
        self.sub_text_3.height=dp(50)


        self.section_layout_2 = Column(
                                       padding=[content_inset,10,content_inset,20],
                                       adaptive_height=True,
                                       spacing=dp(10),
                                       # md_bg_color=[1, .1, .1, 1]
                                       )
        self.section_title_2 = MDLabel(
            text="Others",bold=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            adaptive_height=1,
            # padding=[10]

        )
        self.sub_text_4 = StatsListItem(title="Cache", size_txt="100KB",button_text="Clear")
        self.sub_text_5 = StatsListItem(title="Config", size_txt="50KB",button_text="Clear")
        self.sub_text_4.button.bind(on_release=lambda *_: self._clear_cache())
        self.sub_text_5.button.bind(on_release=lambda *_: self._clear_config())
        self.sub_text_5.padding = [10, 0, 10, 10]
        self.sub_text_5.height = dp(50)



        self.add_widget(self.status_bar_spacer)
        self.header_section.add_widget(self.header_btn)
        self.header_section.add_widget(self.header_label)
        self.header_section.add_widget(self.header_btn_2)


        from ui.widgets.charts import StackedBarChart

        self.graph_container = Column(
            adaptive_height=True,
            size_hint_x=None,
            pos_hint={'center_x': 0.5},
            padding=[16, 12, 16, 16],
            spacing=dp(12),
            # md_bg_color=[1,0,0,1],
            # md_bg_color=get_color_from_hex("2E2E2E"),
            # md_bg_color=(0.132, 0.136, 0.136, 1.0),

            radius=[12, 12, 12, 12],
        )
        sections_container.bind(width=lambda x,value: setattr(self.graph_container,"width",value-2*25))
        self.graph_title = MDLabel(
            text="Storage Usage",
            bold=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size="15sp",
            adaptive_height=True,
        )

        self.storage_chart = StackedBarChart(
            data=[
                ("Other apps", 42 * 1024 * 1024 * 1024,
                 get_color_from_hex("999898")),
                ("Waller", 9 * 1024 * 1024 * 1024,
                 get_color_from_hex("98F1DD")),
                ("Free", 13 * 1024 * 1024 * 1024,
                 get_color_from_hex("434343")),
            ],
            size_hint_y=None,
            height=dp(130),
        )
        self.graph_container.add_widget(self.graph_title)
        self.graph_container.add_widget(self.storage_chart)
        sections_container.add_widget(self.graph_container)
        sections_container.add_widget(LineDivider())
        self.section_layout.add_widget(self.section_title_1)
        self.section_layout.add_widget(self.sub_text_1)
        self.section_layout.add_widget(self.sub_text_2)
        self.section_layout.add_widget(self.sub_text_3)
        sections_container.add_widget(self.section_layout)

        # Section 2
        sections_container.add_widget(LineDivider())
        self.section_layout_2.add_widget(self.section_title_2)
        self.section_layout_2.add_widget(self.sub_text_4)
        self.section_layout_2.add_widget(self.sub_text_5)
        sections_container.add_widget(self.section_layout_2)

        scroll.add_widget(sections_container)
        self.add_widget(self.header_section)
        self.add_widget(scroll)
        Clock.schedule_once(self.refresh_storage_data,0)
        return True

    def handle_going_back(self,*_):
        self.manager.go_to_thumbs()

    def refresh_storage_data(self,widget=None):
        try:
            v = total_and_free_storage_in_android_device()
            print(f"storage v: {v}")
        except Exception as e:
            print(e)
            traceback.print_exc()
            v = {
                "other_apps": 0,  # bytes
                "waller": 0,
                "free": 0,
            }

        self.storage_chart.data=[
                ("Other apps", v["other_apps"], get_color_from_hex("cc73df")),
                ("Waller", v["waller"], get_color_from_hex("98F1DD")),
                ("Free", v["free"],
                 get_color_from_hex("#6b7070")),
        ]

        # free vars for better error stack trace, if any :)
        cm=ConfigManager()
        cm1_file_path=cm.config_path() #config.json v1
        cm2_file_path=ImageDatabase.config_path() #config.json v2

        cm1_file_path_size = os.path.getsize(cm1_file_path)
        cm2_file_path_size = os.path.getsize(cm2_file_path) if os.path.exists(cm2_file_path) else 0
        config_total_bytes=cm1_file_path_size+cm2_file_path_size

        both_wallpapers_file_paths=cm.get_wallpapers()
        noon_wallpapers_file_paths=cm.get_noon_wallpapers()
        day_wallpapers_file_paths=cm.get_day_wallpapers()

        both_bytes=get_files_size(both_wallpapers_file_paths)
        day_bytes=get_files_size(day_wallpapers_file_paths)
        noon_bytes=get_files_size(noon_wallpapers_file_paths)

        # User can't clear running app cache
        # total_known_data_size=both_bytes + day_bytes + noon_bytes+config_total_bytes
        # others_total_bytes = v["waller"]-total_known_data_size

        wallpapers_thumbs_src = os.path.join(appFolder(),"wallpapers","thumbs")
        others_total_bytes=0
        if os.path.exists(wallpapers_thumbs_src):
            others_total_bytes = get_folder_size(wallpapers_thumbs_src)

        print(f"total_known_data_size:{format_size(others_total_bytes)}")
        self.sub_text_1.size_txt= format_size(both_bytes)
        self.sub_text_2.size_txt= format_size(day_bytes)
        self.sub_text_3.size_txt= format_size(noon_bytes)
        self.sub_text_4.size_txt= format_size(others_total_bytes)
        self.sub_text_5.size_txt= format_size(config_total_bytes)

    def _refresh_thumbs_screen(self):
        try:
            self.manager.gallery_screen.refresh_gallery_screen()
        except Exception:
            traceback.print_exc()

    def _remove_wallpapers(self, config_key, label):
        cm = ConfigManager()
        getter = {
            "wallpapers": cm.get_wallpapers,
            "day_wallpapers": cm.get_day_wallpapers,
            "noon_wallpapers": cm.get_noon_wallpapers,
        }[config_key]
        paths = [p for p in getter() if p and os.path.exists(p)]
        count = len(paths)
        if count == 0:
            return
        dialog = DialogScreen(
            icon_name="trash-can-outline",
            header_text=f"Remove {count} {'Image' if count == 1 else 'Images'}?",
            subtitle_text=f"This will permanently remove all {label} wallpapers from storage",
            ok_callback=lambda: self._do_remove_wallpapers(config_key, paths),
        )
        dialog.show(img_texture=None)

    def _do_remove_wallpapers(self, config_key, paths):
        cm = ConfigManager()
        for path in paths:
            if not path:
                continue
            if os.path.exists(path):
                os.remove(path)
            try:
                from pathlib import Path as _P
                thumb = _P(path).parent / "thumbs" / f"{_P(path).stem}_thumb.jpg"
                if thumb.exists():
                    thumb.unlink()
            except Exception:
                traceback.print_exc()
            cm.remove_wallpaper(path)
            cm.remove_wallpaper_to_from("day_wallpapers", path)
            cm.remove_wallpaper_to_from("noon_wallpapers", path)

        ImageDatabase().remove_images(paths)
        self.refresh_storage_data()
        self._refresh_thumbs_screen()

    def _clear_cache(self):
        from pathlib import Path
        thumb_dir = Path(appFolder()) / "wallpapers" / "thumbs"
        if not thumb_dir.exists():
            return
        count = sum(1 for _ in thumb_dir.iterdir())
        if count == 0:
            return
        dialog = DialogScreen(
            icon_name="broom",
            header_text=f"Clear {count} {'thumbnail' if count == 1 else 'thumbnails'}?",
            subtitle_text="This will permanently remove all cached thumbnails",
            ok_callback=lambda: self._do_clear_cache(thumb_dir),
        )
        dialog.show(img_texture=None)

    def _do_clear_cache(self, thumb_dir):
        import shutil
        shutil.rmtree(thumb_dir, ignore_errors=True)
        self.refresh_storage_data()
        self._refresh_thumbs_screen()

    def _clear_config(self):
        dialog = DialogScreen(
            icon_name="cog",
            header_text="Reset app data?",
            subtitle_text="This will reset config and clear image history",
            ok_callback=self._do_clear_config,
        )
        dialog.show(img_texture=None)

    def _do_clear_config(self):
        ConfigManager.write(ConfigManager.DEFAULT_CONFIG)
        db = ImageDatabase()
        db.clear_all()
        self.refresh_storage_data()
        self._refresh_thumbs_screen()

def total_and_free_storage_in_android_device():
    data = {
        "other_apps":0, # bytes
        "waller":0,
        "free":0,
    }
    from android_notify.internal.java_classes import autoclass
    Environment = autoclass("android.os.Environment")
    StatFs = autoclass("android.os.StatFs")
    path = Environment.getDataDirectory()
    stat = StatFs(path.getPath())
    blockSize = stat.getBlockSizeLong()
    totalBlocks = stat.getBlockCountLong()
    availableBlocks = stat.getAvailableBlocksLong()
    total_storage_in_bytes = totalBlocks * blockSize
    free_storage_in_bytes = availableBlocks * blockSize
    src=os.path.join(appFolder()) # In tests /data/user/0/org.wally.waller/files == /data/user/0/org.wally.waller/
    app_total_in_bytes = get_folder_size(src)

    data["waller"]=app_total_in_bytes
    data["other_apps"]=total_storage_in_bytes - (app_total_in_bytes+free_storage_in_bytes)
    data["free"]=free_storage_in_bytes
    return data

boot_log("sm: StatsScreen end of file")