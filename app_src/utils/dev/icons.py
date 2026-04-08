from kivy.properties import StringProperty
from kivy.lang import Builder
from kivy.core.clipboard import Clipboard

from kivymd.icon_definitions import md_icons
from kivymd.material_resources import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.recycleboxlayout import MDRecycleBoxLayout
from kivymd.uix.recycleview import MDRecycleView
from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from kivymd.uix.list import MDListItem
from kivymd.uix.snackbar import MDSnackbar, MDSnackbarSupportingText
from kivymd.uix.textfield import MDTextField, MDTextFieldHintText




from kivy import Config
# Linux has some weirdness with the touchpad by default... remove it
options = Config.options('input')
for option in options:
    if Config.get('input', option) == 'probesysfs':
        Config.remove_option('input', option)


Builder.load_string('''
<IconItem>

    MDListItemLeadingIcon:
        icon: root.icon

    MDListItemSupportingText:
        text: root.text
''')


class IconItem(MDListItem):
    icon = StringProperty()
    text = StringProperty()

    def on_release(self, *args):
        # self.app = MDApp.get_running_app()
        # self.app.screen.get_ids().search_field.text = self.text

        Clipboard.copy(self.text)
        MDSnackbar(
            MDSnackbarSupportingText(
                text=f"Copied to clipboard: {self.text}",
            )
        ).open()

class PreviousMDIcons(MDScreen):
    def set_list_md_icons(self, text="", search=False):
        '''Builds a list of icons for the screen MDIcons.'''

        def add_icon_item(name_icon):
            self.get_ids().rv.data.append(
                {
                    "viewclass": "IconItem",
                    "icon": name_icon,
                    "text": name_icon,
                    # "callback": lambda x = name_icon: x,
                }
            )

        self.get_ids().rv.data = []
        for name_icon in md_icons.keys():
            if search:
                if text in name_icon:
                    add_icon_item(name_icon)
            else:
                add_icon_item(name_icon)


class MainApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.screen = PreviousMDIcons(
            MDBoxLayout(
                MDBoxLayout(
                    MDIconButton(
                        icon='magnify',
                        pos_hint={'center_y': 0.5},
                    ),
                    MDTextField(
                        MDTextFieldHintText(
                            text='Search icon',
                        ),
                        id="search_field",
                    ),
                    adaptive_height=True,
                ),
                MDRecycleView(
                    MDRecycleBoxLayout(
                        padding=(dp(10), dp(10), 0, dp(10)),
                        default_size=(None, dp(48)),
                        default_size_hint=(1, None),
                        size_hint_y=None,
                        adaptive_height=True,
                        orientation='vertical',
                    ),
                    id="rv",
                ),
                orientation='vertical',
                spacing=dp(10),
                padding=dp(20),
            ),
            md_bg_color=self.theme_cls.backgroundColor,
        )

    def build(self):
        rv = self.screen.get_ids().rv
        rv.key_viewclass = 'viewclass'
        rv.key_size = 'height'
        search_field = self.screen.get_ids().search_field
        search_field.bind(
            text=lambda instance, value: self.screen.set_list_md_icons(
                value, True
            )
        )
        return self.screen

    def on_start(self):
        self.screen.set_list_md_icons()

if __name__ == '__main__':
    MainApp().run()