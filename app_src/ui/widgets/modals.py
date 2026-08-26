import traceback

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty, BooleanProperty, ObjectProperty, NumericProperty
from kivy.uix.widget import Widget
from kivymd.uix.button import MDButtonText, MDButton
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.relativelayout import MDRelativeLayout
from ui.widgets.generic import LineDivider

from ui.widgets.layouts import Column, AdaptiveLabel, Row, PlaceOnMainScreen
from utils.helper import load_kv_file  # type
from utils.image_operations import get_image_info
from utils.logger import app_logger

from utils.model import get_app

load_kv_file(py_file_absolute_path=__file__)
# with open(os.path.join(appFolder(),"ui","components","templates.kv"), encoding="utf-8") as kv_file:
#     Builder.load_string(kv_file.read(), filename="MyBtmSheet.kv")

# class

class MyTextButton(MDButton):
    text = StringProperty("")
    text_color = ObjectProperty("")
    adaptive_size = BooleanProperty(False)
    font_name = StringProperty("")
    font_size = ObjectProperty("")
    size_padding = NumericProperty(10)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.elevation_level = 1
        self.theme_width = "Custom"
        self.theme_height = "Custom"
        self.txt = MDButtonText(text=self.text,
                                theme_text_color='Custom',
                                pos_hint={"center_x": .5, "center_y": .5})

        # p(self.adaptive_size)
        if self.adaptive_size:
            self.txt.bind(width=self.fix_text_out_of_bounds_width_on_android)
        else:
            Clock.schedule_once(self.set_width_to_parent_width, 1)
        if self.font_name:
            self.txt.font_name = self.font_name
            self.txt.theme_font_name="Custom"
        if self.font_size:
            self.txt.font_size = self.font_size
            self.txt.theme_font_size="Custom"

        self.set_text_color(self, self.text_color)
        self.bind(text=self.set_val, text_color=self.set_text_color)
        # Clock.schedule_once(self.fix_width,2)
        Clock.schedule_once(self.add_text_widget)

    def set_width_to_parent_width(self,*_):
        # self.height = self.parent.height
        padding = self.parent.spacing#10
        available_width = self.parent.width - padding
        # p(f"available_width: {available_width}")
        self.width = int(available_width/2)

    def add_text_widget(self, _=None):
        self.add_widget(self.txt)

    def set_val(self, _, value):
        self.txt.text = value

    def set_text_color(self, _, value):
        if not value:
            return
        self.txt.text_color = value

    def fix_text_out_of_bounds_width_on_android(self,_,v):
        # fix_text_out_of_bounds_width_on_android receives v as the MDButtonText width, which Kivy already reports in device pixels.
        #  Wrapping it in dp() scales it a second time, so the button becomes roughly density times too wide on high-density screens.
        self.width = v + dp(self.size_padding)

        # p(self.txt.texture_size[0] + 10,v,"used")

    def adjust_width(self,*gg):
        pass

    def fix_width(self, *_):
        self.adjust_width()

class MyDialogBox(Column,PlaceOnMainScreen):
    # source = StringProperty()
    # ok_callback = ObjectProperty()
    icon_name=StringProperty("")
    header_text=StringProperty("_")
    subtitle_text=StringProperty("_")
    show_ok_button=BooleanProperty(True)
    ok_button_text=StringProperty("Yes, Remove")
    ok_button_color=ListProperty([1.0, 0.063, 0.063, 1.0])
    def __init__(self,ok_callback, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.md_bg_color=(0.984, 0.984, 0.984, 1.0)
        self.ok_callback=ok_callback
        self.adaptive_height=1
        # self.size_hint=[None,None]
        self.size_hint_x=None
        # self.width = Window.width-50
        self.pos_hint={'center_x':0.5,'center_y':0.5}
        
        p=dp(15)
        self.padding=[p,dp(50),p,dp(30)]
        self.spacing=dp(15)
        self.radius=10
        sub_text = "This wallpaper will be permanently removed from App Storage"
        # self.img = AsyncImage(source="/home/fabian/Pictures/1065154.jpg",size=[100,100],size_hint=[None,None],mipmap=True,pos_hint={"center_x":0.5})
        # self.icon_name="trash-can-outline"
        # self.header_text = "Remove Image?"
        # self.subtitle_text = sub_text
        # p("self.icon_name",self.icon_name)
        if self.icon_name:
            self.img = MDIcon(
                icon=self.icon_name,
                theme_text_color="Custom",
                text_color=[1,1,1,1],
                font_size = "64sp",
                theme_font_size="Custom",
                pos_hint={"center_x":.5}
            )
            self.bind(icon_name=lambda _,v: setattr(self.img,"icon",v))
        else:
            self.img = FitImage(size=[dp(120),dp(80)],size_hint=[None,None],mipmap=True,pos_hint={"center_x":0.5},radius=10)

        self.add_widget(self.img)
        self.title_widget = MDLabel(text=self.header_text,adaptive_width=1,adaptive_height=1,theme_font_name="Custom",font_name="RobotoMono",bold=True,pos_hint={"center_x":0.5,"center_y":0.5})
        self.bind(header_text=lambda _,v: setattr(self.title_widget,"text",v))
        self.title_widget.font_size="19sp"
        # self.title_widget.md_bg_color=[1,0,1,1]

        # subtext_layout = Column(
        #     adaptive_height=1,
        #     spacing=dp(1),
        #     pos_hint={"center_y": .5}
        # )
        self.subtext = AdaptiveLabel(text=self.subtitle_text,font_name="RobotoMono",size_hint=[None, None])
        self.bind(subtitle_text=lambda _,v: setattr(self.subtext,"text",v))
        self.subtext.font_size="13sp"
        self.subtext.pos_hint={"center_x":0.5,"center_y":0.5}
        self.subtext.color = (0.302, 0.278, 0.278, 1.0)
        self.subtext.valign="center"
        self.subtext.halign="center"
        self.bind(width=self.wrap_text_width)
        # self.subtext.size_hint=[None, None]
        self.add_widget(self.title_widget)
        self.add_widget(self.subtext)
        # subtext_layout.add_widget(self.subtext)
        # self.add_widget(subtext_layout)
        # self.subtext.pos_hint={"center_x":0.5,"center_y":0.5}
        # self.subtext.md_bg_color=[1,1,0,1]
        # self.subtext.adaptive_height=1

        self.buttons_box = Row(spacing=dp(10),padding=[0,10,0,0],pos_hint={"center_x":.5},size_hint_x=.8,adaptive_height=1)
        # self.buttons_box.md_bg_color=[0,0,1,1]
        self.cancel_btn = MyTextButton(text="Dismiss" if not self.show_ok_button else "Cancel",md_bg_color=(0.851, 0.851, 0.851, 1.0),theme_bg_color="Custom",text_color=[0,0,0,1],radius=[5],on_release=self.close)

        self.buttons_box.add_widget(self.cancel_btn)
        if self.show_ok_button:
            self.ok_btn = MyTextButton(text=self.ok_button_text,md_bg_color=self.ok_button_color,theme_bg_color="Custom",text_color=[0,0,0,1],radius=[5],on_release=self.ok)
            self.ok_btn.pos_hint = {"right":1}
            self.buttons_box.add_widget(self.ok_btn)
        self.add_widget(self.buttons_box)
        self.buttons_box.bind(width=self.fix_buttons_width)
        self.bind(ok_button_text=lambda _,v: setattr(self.ok_btn,"text",v) if self.show_ok_button else None)
        self.bind(ok_button_color=lambda _,v: setattr(self.ok_btn,"md_bg_color",v) if self.show_ok_button else None)
        self.app.bind(device_theme=self.set_theme)
        self.set_theme(None, self.app.device_theme)
        Clock.schedule_once(lambda dt:self.wrap_text_width(0,0),0)

    def wrap_text_width(self, i, v):
        # p(f"self.text_layout {self.text_layout.width}, dp:{dp(self.text_layout.width)}") # self.text_layout 470.0, dp:940.0
        self.subtext.text_size = [self.width, None]

    def set_theme(self, _, theme):
        if theme == "light":
            self.md_bg_color = (0.984, 0.984, 0.984, 1.0)
            self.title_widget.text_color = [0, 0, 0, 1]
            self.subtext.color = (0.302, 0.278, 0.278, 1.0)
            self.cancel_btn.md_bg_color = (0.851, 0.851, 0.851, 1.0)
            self.cancel_btn.text_color = [0, 0, 0, 1]
            if self.show_ok_button:
                self.ok_btn.text_color = [0, 0, 0, 1]
            if self.icon_name:
                self.img.text_color = [0, 0, 0, 1]
        else:
            self.md_bg_color = [0.1, 0.1, 0.1, 1]
            self.title_widget.text_color = [1, 1, 1, 1]
            self.subtext.color = [0.7, 0.7, 0.7, 1.0]
            self.cancel_btn.md_bg_color = [0.2, 0.2, 0.2, 1]
            self.cancel_btn.text_color = [1, 1, 1, 1]
            if self.show_ok_button:
                self.ok_btn.text_color = [1, 1, 1, 1]
            if self.icon_name:
                self.img.text_color = [1, 1, 1, 1]

    def close(self,*_):
        self.parent.hide()

    def ok(self,*_):
        self.ok_callback()
        self.close()

    def fix_buttons_width(self,*_):
        self.cancel_btn.set_width_to_parent_width()
        if self.show_ok_button:
            self.ok_btn.set_width_to_parent_width()

class DialogScreen(MDFloatLayout,PlaceOnMainScreen):
    icon_name=StringProperty("")
    header_text=StringProperty("_")
    subtitle_text=StringProperty("_")
    ok_callback=ObjectProperty(None)
    show_ok_button=BooleanProperty(True)
    ok_button_text=StringProperty("Yes, Remove")
    ok_button_color=ListProperty([1.0, 0.063, 0.063, 1.0])
    on_hide_callback=ObjectProperty(None)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.md_bg_color=[0,0,0,0.6]
        self.dialog_box = MyDialogBox(icon_name=self.icon_name, header_text=self.header_text, subtitle_text=self.subtitle_text, ok_callback=self.ok_callback, show_ok_button=self.show_ok_button, ok_button_text=self.ok_button_text, ok_button_color=self.ok_button_color)

        self.bind(width=self.fix_child_width,
                # icon_name=lambda _,v: setattr(self.dialog_box,"icon_name",v),
                header_text=lambda _,v: setattr(self.dialog_box,"header_text",v),
                subtitle_text=lambda _,v: setattr(self.dialog_box,"subtitle_text",v),
                ok_callback=lambda _,v: setattr(self.dialog_box,"ok_callback",v),
                show_ok_button=lambda _,v: setattr(self.dialog_box,"show_ok_button",v),
                ok_button_text=lambda _,v: setattr(self.dialog_box,"ok_button_text",v),
                ok_button_color=lambda _,v: setattr(self.dialog_box,"ok_button_color",v)
                  )
        self.add_widget(self.dialog_box)

    def fix_child_width(self,_,value):
        # p(_,value)
        self.dialog_box.width=value-70

    def show(self,img_texture):
        if hasattr(self.app,"sm"):
            current_screen =self.app.sm.current_screen
        else:
            app_logger.warning(f"This only calls when on hot reload")
            return
        if not self.dialog_box.icon_name:
            self.dialog_box.img.texture = img_texture
        # p(current_screen)
        current_screen.add_widget(self)
        # self.disabled=1
        super().show()

    def hide(self, *_):
        if self.on_hide_callback:
            self.on_hide_callback()
        super().hide()

    def on_touch_down(self, touch):
        super().on_touch_down(touch)# for the children touch
        return True # consume the touch for self


from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivymd.uix.fitimage import FitImage
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel, MDIcon


class IconCard(Row):
    icon=StringProperty("clock")
    title=StringProperty("clock")
    subtext=StringProperty("clock")
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # self.md_bg_color=[1,1,0.5,1]
        self.adaptive_size=1
        self.pos_hint= {"center_y":.5}
        self.spacing=dp(5)
        self.icon_widget = MDIcon(
            icon=self.icon,pos_hint= {"center_y":.5},
            theme_font_size="Custom",
            font_size=dp(35)
        )
        self.icon_widget.theme_bg_color="Custom"
        # self.icon_widget._md_bg_color=[1,0,0,1]# = MDIcon(icon=self.icon)
        self.text_layout = Column(
            adaptive_size=1,padding=5,
            # md_bg_color=[1,1,0,1]
        )
        self.title_label = MDLabel(
            text=self.title,adaptive_size=1, theme_font_name="Custom",font_name="RobotoMono",theme_font_size="Custom",font_size=sp(17),bold=True,
            theme_text_color="Custom",
            text_color="white",
            color="white",
        )
        self.subtext_label = MDLabel(
            text=self.subtext,adaptive_size=1,
            theme_font_name="Custom",font_name="RobotoMono",
            theme_font_size="Custom",font_size=sp(12),
            theme_text_color="Custom", text_color=get_color_from_hex("#8E8E93"),

        )
        self.bind(title=lambda _, value: setattr(self.title_label, "text", value))
        self.bind(subtext=lambda _, value: setattr(self.subtext_label, "text", value))

        self.add_widget(self.icon_widget)
        self.text_layout.add_widget(self.title_label)
        self.text_layout.add_widget(self.subtext_label)
        self.add_widget(self.text_layout)


class InfoPopUpContent(Column,PlaceOnMainScreen):
    hide_callback=ObjectProperty(None)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = get_color_from_hex("#1E1E21")
        self.spacing = dp(10)
        self.padding = dp(10)
        # self.size_hint=(None,None)
        # self.size=[350,360]
        # self.adaptive_size=1
        self.adaptive_height=1
        self.size_hint_x=None
        self.width=dp(330)
        header=Column(
            adaptive_height=True,
        )
        l=MDLabel(
                text="Image Info",
                padding=[0,10,0,0],
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size=sp(15),
            theme_text_color="Custom", text_color="white",
            bold=True,
            adaptive_height=True,
            # md_bg_color=[1, 0, 0, 1]
            # size_hint_y=None,height=40
        )
        header.add_widget(l)
        header.add_widget(LineDivider())
        self.add_widget(header)
        self.first_row = Row(
            # md_bg_color=[1,0,0,1],
            adaptive_height=True,
            spacing=dp(10)
        )
        # self.first_row.adaptive_size=1
        img_size=dp(60)
        self.img = FitImage(
            # source='assets/icons/mountain.png',
            size_hint=(None,None),
            size=[img_size,img_size],
            radius=[dp(img_size/2)],
            pos_hint={"center_y": .5},
        )
        self.when_text = MDLabel(
            text="Noon",
            theme_text_color="Custom",
            text_color=get_color_from_hex("#86EFF3"),
            bold=True,
            adaptive_size=1,
            theme_font_name="Custom",
            font_name="RobotoMono",
            pos_hint={"center_y": .5},
            # md_bg_color=[1,0,0,1]
        )
        self.when_text.size_hint=(None,None)
        self.when_text.bind(texture_size= lambda i,v: setattr(self.when_text,"size",v))
        self.total_usage_layout = Column(
            # md_bg_color=[.1,0.4,1,1],
            md_bg_color=get_color_from_hex("#2D2D30"),
            adaptive_size=1,
            padding=dp(6),
            radius=[dp(5)]
            # r

        )

        self.total_usage_data_layout=Row(
            # md_bg_color=[.31,.1,0,1],
            adaptive_size=1,
            spacing=dp(5)
        )
        self.times_changed_card = IconCard(icon="clock",title="--",subtext="Usage")
        self.times_skipped_card = IconCard(
            icon="skip-next",title="--",subtext="Skips"
        )


        self.second_row = Row(
            # md_bg_color=[1,0.5,0,1],
            spacing=dp(10),
            adaptive_height=True)

        self.props_layout = Column(
            padding=dp(5),
            spacing=dp(10),
            # md_bg_color=[1,0,.3,1],
            md_bg_color=get_color_from_hex("#2D2D30"),
            # adaptive_width=True,
            pos_hint={"top": 1},
            radius=[dp(5)]

        )
        props_grid = MDGridLayout(
            cols=2, rows=2,
            spacing=dp(5),
            # md_bg_color=[1,0,1,1]
            # padding=[0,10,0,10],
            # adaptive_size=True,
            # size_hint=[1,1]
        )

        # Add four buttons to make a 2x2 layout
        props_grid.add_widget(
            MDLabel(
                text='Pixels',adaptive_size=True,
                theme_font_name="Custom",font_name="RobotoMono",
                theme_font_size="Custom",font_size=sp(12),
                theme_text_color="Custom", text_color="white",
            ))

        self.file_res_label=MDLabel(
            text='300x300',
            # adaptive_size=True,
            halign="right",
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size=sp(12),
            theme_text_color="Custom", text_color="white",
            # md_bg_color=[1,0,0,1]
        )
        props_grid.add_widget(self.file_res_label)
        props_grid.add_widget(
            MDLabel(
                text='Size',adaptive_size=True,
                theme_font_name="Custom",font_name="RobotoMono",
                theme_font_size="Custom",font_size=sp(12),
                theme_text_color = "Custom", text_color = "white",

        ))
        self.file_size_label=MDLabel(text='200kB',
                    # adaptive_size=True,
                    halign="right",
                    theme_font_name="Custom",font_name="RobotoMono",
                    theme_font_size="Custom",font_size=sp(12),
                    theme_text_color="Custom", text_color="white",
            )
        props_grid.add_widget(self.file_size_label)

        self.date_layout = MDGridLayout(
            md_bg_color=get_color_from_hex("#2D2D30"),
            pos_hint={"top": 1},
            # padding=5,
            padding=dp(5),
            spacing=dp(5),
            rows=3,
            adaptive_size=True,
            radius = [dp(5)]

        )
        # self.date_layout.orientation='lr-tb'
        self.date_label_one= MDLabel(text="Thursday, 12th oct 2026", adaptive_size=1,
                                theme_font_name="Custom",font_name="RobotoMono",
                                theme_font_size="Custom",font_size=sp(12),
                                theme_text_color="Custom",
                                text_color="white",
                                )
        self.date_label_two= MDLabel(text="12:30PM", adaptive_size=1, theme_font_name="Custom",font_name="RobotoMono",theme_font_size="Custom",font_size=sp(13),
                                theme_text_color="Custom",
                                text_color="white",
                                )

        self.third_row = Column(
            md_bg_color = get_color_from_hex("#2D2D30"),
            adaptive_height=True,
            padding=dp(10),
            spacing=dp(5),
            radius=[dp(5)]

        )
        self.file_name_label = AdaptiveLabel(
            text="img.jpg",
            # adaptive_size=1,
            # theme_font_name="Custom", font_name="RobotoMono",
            # theme_font_size="Custom",
            font_size=sp(13),
            # theme_text_color="Custom",

            # text_color=[1,0,0,1]
            # text_color="white",
            # halign="left"
            # text_size=(30, None),
            size_hint=( None, None),
            # bold=True,
        )
        # self.file_name_label.size_hint=(None, None)
        self.third_row.bind(width=lambda _,v: setattr(self.file_name_label,"text_size",[v,self.file_name_label.text_size[1]]))
        # self.file_name_label.


        self.first_row.add_widget(self.img)
        self.first_row.add_widget(self.when_text)
        self.first_row.add_widget(Widget())

        self.total_usage_data_layout.add_widget(self.times_changed_card)
        self.total_usage_data_layout.add_widget(self.times_skipped_card)

        self.total_usage_layout.add_widget(MDLabel(
            text="Analytics",adaptive_size=1,
            theme_text_color="Custom", text_color=get_color_from_hex("#8E8E93"),
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size=sp(13),
            bold=True
        ))
        self.total_usage_layout.add_widget(self.total_usage_data_layout)

        self.props_layout.add_widget(MDLabel(
            text="Props",adaptive_size=1,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#8E8E93"),
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size=sp(13),
            bold=True
        ))
        self.props_layout.add_widget(props_grid)

        self.date_layout.add_widget(MDLabel(
            text="Added on",adaptive_size=1,
            theme_text_color="Custom", text_color=get_color_from_hex("#8E8E93"),
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size=sp(13),
            bold=True,pos_hint={"top":1},
            # md_bg_color=[1,0,1,1]

        ))


        self.date_layout.add_widget(self.date_label_one)
        self.date_layout.add_widget(self.date_label_two)

        self.third_row.add_widget(MDLabel(
            text="File name",adaptive_size=1,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#8E8E93"),
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size=sp(13),
            bold=True
        ))
        self.third_row.add_widget(self.file_name_label)


        self.first_row.add_widget(self.total_usage_layout)
        self.second_row.add_widget(self.props_layout)
        self.second_row.add_widget(self.date_layout)
        # self.first_row.add_widget(self.total_usage_layout)

        # self.add_widget(MDLabel(text="This is a sample KivyMD app with Kivy Reloader support.", halign="center"))
        self.add_widget(self.first_row)
        self.add_widget(self.second_row)
        self.add_widget(self.third_row)
        self.btn_widget = MyTextButton(
            text="Copy",
            # style="outlined",
            pos_hint={"right":1},
            adaptive_size=True,
            size_padding=dp(18),
            radius=[dp(5)],
            text_color="white",
            theme_bg_color="Custom",
            md_bg_color=get_color_from_hex("#2D2D30"),
        )
        self.btn_widget.bind(on_release=self.hide_callback)
        self.btn_widget.theme_height="Custom"
        # self.btn_widget.size_hint_y=None
        self.btn_widget.height=dp(35)
        # self.btn_widget.size_hint=(None,None)
        # self.btn_widget.size = [20,50]
        # self.btn_widget.padding=
        self.add_widget(self.btn_widget)

class InfoPopUpModal(MDRelativeLayout,PlaceOnMainScreen):
    image_abs_path=StringProperty("")
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.md_bg_color=[0,0,0,0.6]
        self.dialog_box = InfoPopUpContent(
            hide_callback=self.hide,
            pos_hint={"center_x":.5,"center_y":.5},
        )
        self.add_widget(self.dialog_box)

    def on_image_abs_path(self,_,path):
        import os
        if not os.path.exists(path):
            return
        info_dict = get_image_info(path)

        self.dialog_box.file_name_label.text=os.path.basename(path)
        self.dialog_box.file_size_label.text=info_dict["Size"]
        self.dialog_box.file_res_label.text=info_dict["Pixels"]
        self.dialog_box.date_label_one.text=info_dict["long_date"]
        self.dialog_box.date_label_two.text=info_dict["time"]

        try:
            from utils.database import ImageDatabase
            stats = ImageDatabase().get_image_stats(path)
            print(f"stats: {stats}")
            if stats:
                set_count, skip_count, last_set, last_skipped, tab = stats
                self.dialog_box.times_changed_card.title = str(set_count or 0)
                self.dialog_box.times_skipped_card.title = str(skip_count or 0)
                tab_labels = {"both": "Both", "day": "Day", "noon": "Noon"}
                self.dialog_box.when_text.text = tab_labels.get(tab or "both", "Both")
        except Exception as error_get_analyticis:
            app_logger.exception("Error getting image analytics:", exc_info=error_get_analyticis)
            traceback.print_exc()
            pass


    def show(self,image_abs_path,img_texture,*_):
        self.image_abs_path=str(image_abs_path)
        self.dialog_box.img.texture=img_texture
        if hasattr(self.app,"sm"):
            current_screen =self.app.sm.current_screen
        else:
            app_logger.warning(f"This only calls when on hot reload")
            return
        current_screen.add_widget(self)
        super().show()

    def hide(self, *_):
        super().hide()

    def on_touch_down(self, touch):
        super().on_touch_down(touch)# for the children touch
        return True # consume the touch for self