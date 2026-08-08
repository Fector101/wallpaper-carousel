from kivymd.uix.screen import MDScreen

from ui.widgets.spinner import SpinningArcWidget


class LoadingScreen(MDScreen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "loading_screen"
        self.md_bg_color = [0, 0, 0, 1]
        self.size_hint = [1, 1]
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        self.spinner = SpinningArcWidget()
        self.spinner.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.add_widget(self.spinner)
