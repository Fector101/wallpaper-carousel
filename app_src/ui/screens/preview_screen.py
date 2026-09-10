from kivy.uix.floatlayout import FloatLayout
from ui.widgets.layouts import MyMDScreen
from kivy.properties import ListProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.scatterlayout import ScatterLayout

class MyImage(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.test)
    def test(self, instance, value):
        print("on_pos: ", value)

class MyScatter(ScatterLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_rotation=False
        self.min_scale = 1
        self.pos=(0,0)

        with self.canvas.before:
            Color(1, 1, 0, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        # Manually update the rectangle coordinates when the widget resizes
        self.rect.pos = self.pos
        self.rect.size = self.size
        print("Scatter pos: {pos}, {size}".format(pos=self.pos, size=self.size))

    def on_transform(self, instance, value):
        super().on_transform(instance, value)

        # Prevent scaling smaller than the screen
        if self.scale < self.min_scale:
            self.scale = self.min_scale

        # Constrain translation so the image doesn't drag completely off-screen
        parent = self.parent
        if not parent:
            return
        min_x = parent.width - (self.width * self.scale)

        min_y = parent.height - (self.height * self.scale)

        # Clamp position within bounds
        x = max(min_x, min(self.x, 0))
        y = max(min_y, min(self.y, 0))

        # Center if smaller than the screen on an axis
        # if self.width * self.scale < parent.width:
        #     x = (parent.width - (self.width * self.scale)) / 2
        # if self.height * self.scale < parent.height:
        #     y = (parent.height - (self.height * self.scale)) / 2

        self.pos = (x, y)



class MyBoxLayout(BoxLayout):
    background_color = ListProperty([1,0,0,1])
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(*self.background_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        # Manually update the rectangle coordinates when the widget resizes
        self.rect.pos = self.pos
        self.rect.size = self.size


class PreviewScreen(MyMDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name="preview"
        root = FloatLayout()

        scatter = MyScatter(
            size_hint=(None, None),
            auto_bring_to_front=0

        )  # ,pos_hint={"center_x":0.01, "center_y":0.5})
        # image = MyBoxLayout(size_hint=(1,1),background_color=[1,0,0.5,1])
        image = MyImage(
            source='sun.jpg',
            fit_mode="cover",
            keep_ratio=True,

        )
        self.bind(size=lambda _, v: setattr(image, 'size', v))  # ,pos=lambda _,v: setattr(image,'pos',v))
        self.bind(size=lambda _,v: setattr(scatter,'size',v),pos=lambda _,v: setattr(scatter,'pos',v))
        scatter.add_widget(image)
        root.add_widget(scatter)

        self.add_widget(root)
        self.hide_system_ui()

