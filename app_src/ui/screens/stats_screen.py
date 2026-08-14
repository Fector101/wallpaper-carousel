import random

from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line


from kivymd.uix.button import MDIconButton, MDButton
from kivymd.uix.label import MDLabel


from ui.widgets.layouts import MyMDScreen, GenericStatusBarSpacer, Row, Column



# 1. Define a reusable, self-updating horizontal line widget
class LineDivider(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 2  # Set line thickness space area

        with self.canvas:
            Color(*get_color_from_hex("5E5E5E"))
            self.line = Line(points=[], width=0.5)

        # Bind it to its own size/position changes
        self.bind(pos=self.update_line, size=self.update_line)

    def update_line(self, *args):
        # Keeps the line perfectly straight along its own layout position
        self.line.points = [self.x, self.y, self.x + self.width, self.y]


from kivy.uix.anchorlayout import AnchorLayout
from kivymd.uix.button import MDButtonText

class MyTextButton(MDButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.fix_width,2)
    def adjust_width(self,*gg):
        pass
    def fix_width(self, *_):
        pass

class StatsListItem(Row):  # Assuming Row inherits from horizontal MDBoxLayout
    title = StringProperty()
    size_txt = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        grey_color=get_color_from_hex("999898")

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
        button_container = AnchorLayout(anchor_x="center", anchor_y="center")

        self.button = MyTextButton(
            style="outlined",
            theme_line_color="Custom",
            line_color=grey_color,
            radius=[4, ],
            # 'theme_elevation_level',
            # 'theme_icon_color', 'theme_line_color', 'theme_shadow_color',
            # 'theme_shadow_offset', 'theme_shadow_softness',
            # padding=[4, ]
        )
        self.theme_height="Custom"
        self.theme_width="Custom"
        # self.button.width=dp(10)
        self.button.height=dp(35)
        self.button_text = MDButtonText(
            text="Remove",
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            theme_font_size="Custom", font_size="12sp"
        )
        self.button.add_widget(self.button_text)

        # 2. Add button to container, then container to your row layout
        button_container.add_widget(self.button)

        self.add_widget(self.title_label)
        self.add_widget(self.size_label)
        self.add_widget(button_container)  # This acts as the third centered column

        # self.md_bg_color = (random.random(), random.random(), random.random(), 1)
        # self.adaptive_height=10
        self.padding=[10,0]
        self.size_hint_y=None
        self.height = dp(40)

class StatsScreen(MyMDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "stats"
        self.status_bar_spacer = GenericStatusBarSpacer(
            status_bar_height=self.status_bar_height,
            md_bg_color=[.1, .1, .1, 1]
        )
        self.md_bg_color = get_color_from_hex("252424")
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
                                theme_font_name="Custom", font_name = "RobotoMono"
                        )
        self.header_btn_2 = MDIconButton(
            icon="refresh",
            style="tonal",
            size=(dp(70), dp(70)),
            pos_hint={'center_y': 0.45},
            theme_text_color='Custom',
            text_color=[1, 1, 1, 1],
            on_release=self.handle_going_back,
            theme_bg_color='Custom'
        )

        # Scroll area
        scroll = ScrollView(size_hint=(1, 1))
        sections_container = Column(
            # md_bg_color=[1, .4, .4, 1],
            # size_hint_y=None,
            spacing=dp(6),
            # padding=(0, dp(4))
        )
        sections_container.bind(minimum_height=sections_container.setter("height"))

        self.section_layout = Column(padding=10,
                                     adaptive_height=True,
                                     spacing=dp(10),
                                     # md_bg_color=[1, 1, .1, 1]
                                     )
        self.section_title_1= MDLabel(
            text="Pictures",bold=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            adaptive_height=1,padding=[10]

        )
        self.sub_text_1 = StatsListItem(title="Both", size_txt="70KB")
        self.sub_text_2 = StatsListItem(title="Day", size_txt="5MB")
        self.sub_text_3 = StatsListItem(title="Noon", size_txt="200KB",)
        self.sub_text_3.padding=[10,0,10,10]
        self.sub_text_3.height=dp(50)


        self.section_layout_2 = Column(
                                       padding=[10,10,10,20],
                                       adaptive_height=True,
                                       spacing=dp(10),
                                       # md_bg_color=[1, .1, .1, 1]
                                       )
        self.section_title_2 = MDLabel(
            text="Images",
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            adaptive_height=1,padding=[10]

        )
        self.sub_text_4 = StatsListItem(title="Cache", size_txt="100KB")
        self.sub_text_5 = StatsListItem(title="Config", size_txt="50KB")
        self.sub_text_5.padding = [10, 0, 10, 10]
        self.sub_text_5.height = dp(50)



        self.add_widget(self.status_bar_spacer)
        self.header_section.add_widget(self.header_btn)
        self.header_section.add_widget(self.header_label)
        self.header_section.add_widget(self.header_btn_2)


        from ui.widgets.charts import HorizontalBarChart

        self.graph_container = Column(
            adaptive_height=True,
            padding=[16, 12, 16, 16],
            spacing=dp(12),
            md_bg_color=get_color_from_hex("2E2E2E"),
            radius=[12, 12, 12, 12],
        )
        self.graph_title = MDLabel(
            text="Storage Usage",
            bold=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name="RobotoMono",
            theme_font_size="Custom", font_size="15sp",
            adaptive_height=True,
        )
        self.storage_chart = HorizontalBarChart(
            data=[
                ("Both", 70 * 1024),
                ("Day", 5 * 1024 * 1024),
                ("Noon", 200 * 1024),
                ("Cache", 100 * 1024),
                ("Config", 50 * 1024),
            ],
            size_hint_y=None,
            height=dp(210),
        )
        self.graph_container.add_widget(self.graph_title)
        self.graph_container.add_widget(self.storage_chart)
        sections_container.add_widget(self.graph_container)
        sections_container.add_widget(LineDivider())
        sections_container.add_widget(self.section_title_1)
        sections_container.add_widget(self.sub_text_1)
        sections_container.add_widget(self.sub_text_2)
        sections_container.add_widget(self.sub_text_3)
        # sections_container.add_widget(self.section_layout)

        # Section 2
        sections_container.add_widget(LineDivider())
        self.section_layout_2.add_widget(self.section_title_2)
        self.section_layout_2.add_widget(self.sub_text_4)
        self.section_layout_2.add_widget(self.sub_text_5)
        sections_container.add_widget(self.section_layout_2)

        scroll.add_widget(sections_container)
        self.add_widget(self.header_section)
        self.add_widget(scroll)

        self.build_ui()

    @staticmethod
    def update_line(parent_widget, widget):
        # Keeps the Y coordinate identical (self.center_y) to ensure it stays perfectly flat
        widget.points = [parent_widget.x, parent_widget.center_y, parent_widget.x + parent_widget.width, parent_widget.center_y]

    def build_ui(self):
        pass

    def handle_going_back(self,*_):
        self.manager.go_to_thumbs()
