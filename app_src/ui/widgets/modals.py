from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import ListProperty, StringProperty, BooleanProperty, ObjectProperty
from kivymd.uix.button import MDButtonText, MDButton
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel, MDIcon

from ui.widgets.layouts import Column, AdaptiveLabel, Row, PlaceOnMainScreen
from utils.helper import load_kv_file  # type
from utils.logger import app_logger

from utils.model import get_app

load_kv_file(py_file_absolute_path=__file__)
# with open(os.path.join(appFolder(),"ui","components","templates.kv"), encoding="utf-8") as kv_file:
#     Builder.load_string(kv_file.read(), filename="MyBtmSheet.kv")

# class

class MyTextButton(MDButton):
    text = StringProperty("")
    text_color = ListProperty("")
    adaptive_size = BooleanProperty(False)
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
        self.width = dp(v+10)

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
                icon=self.icon_name,#,
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
            self.ok_btn = MyTextButton(text="Yes, Remove",md_bg_color=(1.0, 0.063, 0.063, 1.0),theme_bg_color="Custom",text_color=[0,0,0,1],radius=[5],on_release=self.ok)
            self.ok_btn.pos_hint = {"right":1}
            self.buttons_box.add_widget(self.ok_btn)
        self.add_widget(self.buttons_box)
        self.buttons_box.bind(width=self.fix_buttons_width)
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
        else:
            self.md_bg_color = [0.1, 0.1, 0.1, 1]
            self.title_widget.text_color = [1, 1, 1, 1]
            self.subtext.color = [0.7, 0.7, 0.7, 1.0]
            self.cancel_btn.md_bg_color = [0.2, 0.2, 0.2, 1]
            self.cancel_btn.text_color = [1, 1, 1, 1]
            if self.show_ok_button:
                self.ok_btn.text_color = [1, 1, 1, 1]

    def close(self,*_):
        self.parent.close()

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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.md_bg_color=[0,0,0,0.6]
        self.dialog_box = MyDialogBox(icon_name=self.icon_name, header_text=self.header_text, subtitle_text=self.subtitle_text, ok_callback=self.ok_callback, show_ok_button=self.show_ok_button)

        self.bind(width=self.fix_child_width,
                # icon_name=lambda _,v: setattr(self.dialog_box,"icon_name",v),
                header_text=lambda _,v: setattr(self.dialog_box,"header_text",v),
                subtitle_text=lambda _,v: setattr(self.dialog_box,"subtitle_text",v),
                ok_callback=lambda _,v: setattr(self.dialog_box,"ok_callback",v),
                show_ok_button=lambda _,v: setattr(self.dialog_box,"show_ok_button",v)
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

    def hide(self, frm_esc_key=False, key=None, *_):
        super().hide(frm_esc_key=frm_esc_key, key=key)

    def on_touch_down(self, touch):
        touch_x,touch_y=touch.pos
        db = self.dialog_box
        dialog_box_x = db.pos[0]
        dialog_box_y = db.pos[1]

        # p(dialog_box_x,dialog_box_y,touch)
        # p(touch_y,dialog_box_y, db.height)
        in_y_range = touch_y < dialog_box_y + db.height and touch_y > dialog_box_y
        in_x_range = touch_x < dialog_box_x + db.width and touch_x > dialog_box_x

        if in_y_range and in_x_range:
            return super().on_touch_down(touch)
        else:
            return True
