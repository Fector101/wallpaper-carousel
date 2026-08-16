from utils.boot_log import boot_log
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.uix.widget import Widget

from ui.widgets.layouts import MyMDScreen, GenericStatusBarSpacer, Row, Column


class LineDivider(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.graphics import Color, Line
        self.size_hint_y = None
        self.height = 2  # Set line thickness space area

        with self.canvas:
            Color(*get_color_from_hex("5E5E5E"))
            self.line = Line(points=[], width=0.5)

        # Bind it to its own size/position changes
        self.bind(pos=self.update_line, size=self.update_line)

    def update_line(self, *_):
        # Keeps the line perfectly straight along its own layout position
        self.line.points = [self.x, self.y, self.x + self.width, self.y]


class StatsListItem(Row):  # Assuming Row inherits from horizontal MDBoxLayout
    title = StringProperty()
    size_txt = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from ui.widgets.modals import MyTextButton
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
            radius=[4, ],
            text="Remove",
            adaptive_size=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            font_name="RobotoMono",
            theme_font_size="Custom", font_size="12sp",
            size_padding=0,

            # padding=[4, ]
        )
        self.theme_height="Custom"
        self.theme_width="Custom"
        # self.button.width=dp(10)
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

        # self.button_text.bind(width=self.fix_text_out_of_bounds_width_on_android)

    def fix_text_out_of_bounds_width_on_android(self,_,v):
        self.button.width = dp(v+10)


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
        self.md_bg_color = get_color_from_hex("252424")

    def on_enter(self, *args):
        super().on_enter(*args)
        if not self.built_ui:
            Clock.schedule_once(self._timer_set)
            self.built_ui = True

    def _timer_set(self,_):
        Clock.schedule_once(self.build_ui)

    @staticmethod
    def update_line(parent_widget, widget):
        # Keeps the Y coordinate identical (self.center_y) to ensure it stays perfectly flat
        widget.points = [parent_widget.x, parent_widget.center_y, parent_widget.x + parent_widget.width, parent_widget.center_y]

    def build_ui(self,_):
        global MDLabel
        from kivy.uix.scrollview import ScrollView
        from kivymd.uix.button import MDIconButton
        from kivymd.uix.label import MDLabel

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
                                text="Manage Storage(WIP)",
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
            size_hint_y=None,
            spacing=dp(6),
            padding=(0, dp(10))
        )
        sections_container.bind(minimum_height=sections_container.setter("height"))

        self.section_layout = Column(
                                     # padding=[10,10],
                                     adaptive_height=True,
                                     spacing=dp(10),
                                    padding=[25, 10, 25, 20],

            # md_bg_color=[1, 1, .1, 1]
                                     )
        self.section_title_1= MDLabel(
            text="Pictures",bold=1,
            theme_text_color="Custom", text_color=(1, 1, 1, 1),
            theme_font_name="Custom", font_name = "RobotoMono",
            adaptive_height=1,
            # padding=[20,10]

        )
        self.sub_text_1 = StatsListItem(title="Both", size_txt="70KB")
        self.sub_text_2 = StatsListItem(title="Day", size_txt="5MB")
        self.sub_text_3 = StatsListItem(title="Noon", size_txt="200KB",)
        self.sub_text_3.padding=[10,0,10,10]
        self.sub_text_3.height=dp(50)


        self.section_layout_2 = Column(
                                       padding=[25,10,25,20],
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
        self.sub_text_4 = StatsListItem(title="Cache", size_txt="100KB")
        self.sub_text_5 = StatsListItem(title="Config", size_txt="50KB")
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
            md_bg_color=get_color_from_hex("2E2E2E"),
            radius=[12, 12, 12, 12],
        )
        sections_container.bind(width=lambda x,value: setattr(self.graph_container,"width",value-50))
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
        return True

    def handle_going_back(self,*_):
        print("test")
        self.manager.go_to_thumbs()

boot_log("sm: StatsScreen end of file")
