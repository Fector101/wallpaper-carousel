from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.label import MDLabel

from ui.screens.download_apk_screen import TextButton
from ui.widgets.layouts import Column, AdaptiveLabel, Row, PlaceOnMainScreen
from utils.helper import load_kv_file  # type

from utils.model import get_app

load_kv_file(py_file_absolute_path=__file__)
# with open(os.path.join(appFolder(),"ui","components","templates.kv"), encoding="utf-8") as kv_file:
#     Builder.load_string(kv_file.read(), filename="MyBtmSheet.kv")

# class
class MyDialogBox(Column):
    # source = StringProperty()
    # ok_callback = ObjectProperty()
    def __init__(self,ok_callback, **kwargs):
        super().__init__(**kwargs)
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
        sub_text = "This wallpaper will be permanently removed from Apps Storage"
        # self.img = AsyncImage(source="/home/fabian/Pictures/1065154.jpg",size=[100,100],size_hint=[None,None],mipmap=True,pos_hint={"center_x":0.5})
        self.img = FitImage(source="/home/fabian/Pictures/1065154.jpg",size=[dp(120),dp(80)],size_hint=[None,None],mipmap=True,pos_hint={"center_x":0.5},radius=10)

        self.add_widget(self.img)
        title_widget = MDLabel(text="Delete Image?",adaptive_width=1,adaptive_height=1,theme_font_name="Custom",font_name="RobotoMono",bold=True,pos_hint={"center_x":0.5,"center_y":0.5})
        title_widget.font_size="19sp"
        # title_widget.md_bg_color=[1,0,1,1]

        # subtext_layout = Column(
        #     adaptive_height=1,
        #     spacing=dp(1),
        #     pos_hint={"center_y": .5}
        # )
        self.subtext = AdaptiveLabel(text="This wallpaper will be permanently removed from Apps Storage",font_name="RobotoMono",size_hint=[None, None])
        self.subtext.font_size="13sp"
        self.subtext.pos_hint={"center_x":0.5,"center_y":0.5}
        self.subtext.color = (0.302, 0.278, 0.278, 1.0)
        self.subtext.valign="center"
        self.subtext.halign="center"
        self.bind(width=self.wrap_text_width)
        # self.subtext.size_hint=[None, None]
        self.add_widget(title_widget)
        self.add_widget(self.subtext)
        # subtext_layout.add_widget(self.subtext)
        # self.add_widget(subtext_layout)
        # self.subtext.pos_hint={"center_x":0.5,"center_y":0.5}
        # self.subtext.md_bg_color=[1,1,0,1]
        # self.subtext.adaptive_height=1

        buttons_box = Row(spacing=10,padding=[0,10,0,0],pos_hint={"right":1},adaptive_size=1)
        # buttons_box.md_bg_color=[1,0,0,1]
        cancel_btn = TextButton(text="Cancel",md_bg_color=(0.851, 0.851, 0.851, 1.0),theme_bg_color="Custom",text_color=[0,0,0,1],radius=[5],on_release=self.close)

        buttons_box.add_widget(cancel_btn)
        ok_btn = TextButton(text="Yes, Delete",md_bg_color=(1.0, 0.063, 0.063, 1.0),theme_bg_color="Custom",text_color=[0,0,0,1],radius=[5],on_release=self.ok)
        buttons_box.add_widget(ok_btn)
        self.add_widget(buttons_box)
        Clock.schedule_once(lambda dt:self.wrap_text_width(0,0),0)

    def wrap_text_width(self, i, v):
        # print(f"self.text_layout {self.text_layout.width}, dp:{dp(self.text_layout.width)}") # self.text_layout 470.0, dp:940.0
        self.subtext.text_size = [self.width, None]

    def close(self,*_):
        self.parent.close()

    def ok(self,*_):
        self.ok_callback()
        self.close()

class DialogScreen(MDFloatLayout,PlaceOnMainScreen):
    def __init__(self, ok_callback, **kwargs):
        super().__init__(**kwargs)
        self.app = get_app()
        self.md_bg_color=[0,0,0,0.6]
        self.dialog_box = MyDialogBox(ok_callback=ok_callback)
        self.bind(width=self.fix_child_width)
        self.add_widget(self.dialog_box)
    def fix_child_width(self,_,value):
        print(_,value)
        self.dialog_box.width=value-70

    def show(self,img_texture):
        current_screen = self.app.sm.current_screen
        self.dialog_box.img.texture = img_texture
        # print(current_screen)
        current_screen.add_widget(self)
        # self.disabled=1
    def close(self,*_):
        parent = self.parent
        if parent:
            parent.remove_widget(self)
    def on_touch_down(self, touch):
        touch_x,touch_y=touch.pos
        db = self.dialog_box
        dialog_box_x = db.pos[0]
        dialog_box_y = db.pos[1]

        # print(dialog_box_x,dialog_box_y,touch)
        # print(touch_y,dialog_box_y, db.height)
        in_y_range = touch_y < dialog_box_y + db.height and touch_y > dialog_box_y
        in_x_range = touch_x < dialog_box_x + db.width and touch_x > dialog_box_x

        if in_y_range and in_x_range:
            return super().on_touch_down(touch)
        else:
            return True
