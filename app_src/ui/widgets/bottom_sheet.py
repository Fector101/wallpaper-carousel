from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout

from kivymd.app import MDApp
from kivymd.uix.label import MDLabel

from ui.screens.gallery_screen import GalleryScreen, DateGroupLayout
from utils.logger import app_logger
from utils.config_manager import ConfigManager
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty
from ui.widgets.layouts import MyMDScreen, Column, Row, get_nav_bar_height, get_status_bar_height  # used in .kv file

my_config = ConfigManager()

class DropDownMain(Row):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.menu = None
        self.adaptive_size= 1
        self.md_bg_color=[0,0,0,.1]
        self.spacing= dp(10)
        self.radius= [dp(5)]
        self.padding= [dp(5)]

        # with self.canvas.after:
        #     self.bg_color_instr = Color(1,0,0,1)
        #     self.rect = RoundedRectangle(radius=[5, 0, 0, 5], size=[100, 100])
        #     self.rect.pos = self.pos
        #
        # self.bind(pos = lambda _,x:setattr(self.rect,"pos",x), size = lambda _,x:setattr(self.rect,"size",x))

        #
        # t = MDListItemTrailingIcon(
        #     icon="search",
        #     theme_icon_color="Custom",
        #     icon_color=[.6, .6, .6, 1],
        # )
        # self.add_widget(t)
        # self.bind(touch_up=self.on_release)

    def on_release(self):
        app_logger.warning("TODO Add Un-Grouped Logic")
        return True
        items = [
            {"text": "grouped", "trailing_icon": "check", "text_color": "white","divider_color":"red","md_bg_color":[.14,.14,.14,1]},
            {"text": "un-grouped", "text_color": "white","divider_color":"red","md_bg_color":[.14,.14,.14,1]}
            #, "trailing_icon": "check"}
        ]
        self.menu = MDDropdownMenu(
            caller=self,
            items=items,
            width_mult=4,
           theme_bg_color="Custom",
           theme_text_color="Custom",
            ver_growth="down",
            hor_growth="left",

        )
        self.menu.open()


from kivymd.uix.bottomsheet.bottomsheet import MDBottomSheet,MDBottomSheetDragHandle,MDBottomSheetDragHandleTitle,MDBottomSheetDragHandleButton

class TypeMapElement(MDBoxLayout):
    selected = BooleanProperty(False)
    icon = StringProperty()
    title = StringProperty()
    func = ObjectProperty()
    cols_int = NumericProperty()
    def on_touch_up(self,touch):
        self.parent.parent.hide(False) # Closes MDBottomSheet
        return super().on_touch_up(touch)


class TypeMapElementOptions(MDBoxLayout):
    selected = BooleanProperty(False)
    icon = StringProperty()
    title = StringProperty()
    func = ObjectProperty()
    # def on_touch_up(self,touch):
    #     self.parent.parent.hide(False) # Closes MDBottomSheet
    #     return super().on_touch_up(touch)


class MyBtmSheet(MDBottomSheet):
    sheet_type = "standard"
    items = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # super(MyBtmSheet,self).__init__(**kwargs)
        self.md_bg_color=[.14,.14,.14,1]
        self.adaptive_height=1
        # self.size_hint_y = None
        # self.height = dp(410)
        self.padding=[0,0,0, get_nav_bar_height()*2.5]
        self.drag_sheet = MDBottomSheetDragHandle(
            # drag_handle_color= "grey"
            # md_bg_color=[1,1,0,1],
            drag_handle_color = [.7, .7, .7, 1],


        )
        # with self.drag_sheet.canvas.after:
        #     self.bg_color_instr = Color(1,0,0,1)
        #     self.rect = RoundedRectangle(radius=[5, 0, 0, 5], size=[100, 100])
        #     self.rect.pos = self.drag_sheet.pos

        # self.drag_sheet.bind(pos = lambda _,x:setattr(self.rect,"pos",x), size = lambda _,x:setattr(self.rect,"size",x))


        self.sheet_title = MDBottomSheetDragHandleTitle(
            text="Display Settings",
            pos_hint={"center_y": .5},
            adaptive_height=True,
            shorten_from='right',
            shorten=True,
            theme_text_color= "Custom",
            text_color="white",

        )
        self.drag_sheet.add_widget(self.sheet_title)
        self.drag_sheet.add_widget(
            MDBottomSheetDragHandleButton(
                icon="close",
                ripple_effect=False,
                on_release=lambda x: self.set_state("close"),
                theme_text_color="Custom",
                text_color="white"

            )
        )

        self.content = MDBoxLayout(padding=[0, 0, 0, 0], orientation="vertical",spacing=dp(10))
        # self.content.md_bg_color = [1, 0, 0, 1]
        self.content.adaptive_height=1
        self.add_widget(self.drag_sheet)
        self.add_widget(self.content)
        self.enable_swiping = 0
        c=.3
        self.items=[{
            "header_title": "Grouped",
            "icon": "search",
            "function": print,

        }]
        self.content.add_widget(MDLabel(text="View",adaptive_size=1,theme_text_color="Custom",text_color=[0.7, 0.7, 0.9, 1.0],padding=[dp(15),0,0,0]))#,pos_hint={"center_x":.1}))
        self.content.add_widget(
            TypeMapElementOptions(
                title="Layout",
                icon="form-dropdown",
                func=self.__change_number_of_columns_in_store,
                md_bg_color=[ c,c,c,.3]

            )
        )
        self.content.add_widget(
            MDLabel(
                text="Grid Columns",
                adaptive_size=1,
                theme_text_color="Custom",
                text_color=[0.7, 0.7, 0.9, 1.0],
                padding=[dp(15),0,0,0]
            )
        )
        self.content.add_widget(
            TypeMapElement(
                title="3 Cols",
                cols_int=3,
                # icon="form-dropdown",
                func=self.__change_number_of_columns_in_store,
                md_bg_color=[ c,c,c,.3]

            )
        )
        self.content.add_widget(
            TypeMapElement(
                title="4 Cols",
                cols_int=4,
                # icon="form-dropdown",
                func=self.__change_number_of_columns_in_store,
                md_bg_color=[ c,c,c,.3]

            )
        )
        self.content.add_widget(
            TypeMapElement(
                title="5 Cols",
                cols_int=5,
                func=self.__change_number_of_columns_in_store,
                md_bg_color=[ c,c,c,.3]

            )
        )
        self.content.add_widget(
            TypeMapElement(
                title="6 Cols",
                cols_int=6,
                func=self.__change_number_of_columns_in_store,
                md_bg_color=[ c,c,c,.3]

            )
        )
        # for each_item in self.items:
        #     title=each_item['header_title'].capitalize()
        #     icon=each_item['icon']
        #     function=each_item['function']
        #     self.content.add_widget(
        #         TypeMapElement(
        #             title=title,
        #             icon=icon,
        #             func=function
        #         )
        #     )
        # self.set_state("open")


    def on_touch_up(self,e):

        x,y=e.pos

        # print(f"x:{x}, y:{y}")
        for each in self.walk():
            if isinstance(each,DropDownMain):
                # drop_down_pos=each.pos
                drop_down_pos_x,drop_down_pos_y=each.pos
                if drop_down_pos_x <= x <= drop_down_pos_x + each.width and drop_down_pos_y <= y <= drop_down_pos_y + each.height:
                # if x >= drop_down_pos_x and y >= drop_down_pos_y x <= drop_down_pos_x + each.width and y <= drop_down_pos_y + each.height:
                #     print('thing')
                    each.on_release()

    def on_touch_move(self, touch):
        if self.enable_swiping:
            if self.status == "opened" and abs(touch.y - touch.oy) > self.swipe_distance:
                self.status = "closing_with_swipe"
        if self.status == "closing_with_swipe":
            self.open_progress = max( min( self.open_progress + (touch.dy if self.anchor == "left" else - touch.dy) / self.height, 1 ), 0 )
            if touch.pos[1] <=get_nav_bar_height():
                self.hide(False)
            return True
        return None

    def on_close(self, *args):
        self.enable_swiping = 0
        return super().on_close(*args)

    def show(self):
        self.enable_swiping = True
        self.set_state("toggle")
        self.__mark_number_of_cols_selected()

    def __mark_number_of_cols_selected(self):
        for each in self.walk():
            if isinstance(each,TypeMapElement):
                clickable_item =each
                clickable_item_ids =clickable_item.ids#["icon"]
                clickable_item_ids.icon_widget.icon = ""
                if clickable_item.cols_int == my_config.get_cols():
                    # print(clickable_item, clickable_item_ids, clickable_item.cols_int)
                    clickable_item_ids.icon_widget.icon = "check"

    def __change_number_of_columns_in_store(self, caller,text):

        chosen_cols = caller.cols_int
        my_config.set_cols(chosen_cols)
        clickable_children = self.walk()#caller.parent.children
        for each in clickable_children:
            if not isinstance(each,TypeMapElement):
                continue
            each.ids["icon_widget"].icon = ""
            if each.cols_int == chosen_cols:
                each.ids["icon_widget"].icon = "check"

        app = MDApp.get_running_app()
        gallery_screen = app.sm.current_screen
        if not isinstance(gallery_screen, GalleryScreen):
            app_logger.error("Add way to use other screens")
            return

        # gallery_screen = None
        # for e in app.sm.screens:
        #     gallery_screen = e
        #     if isinstance(e,GalleryScreen):
        #         break
        for each in gallery_screen.walk():
            if isinstance(each,DateGroupLayout):
                each.change_preview_img_size(None,chosen_cols)
        self.hide()
    def hide(self, animation=True):
        self.set_state('close', animation=animation)

    def adjust_padding(self,rotation):
        # self.screen_content.padding = [0, 0, 0, self.nav_bar_height + self.status_bar_height]
        if rotation == "TOP":
            self.padding = [0, 0, 0, get_nav_bar_height()*2.5]

        elif rotation == "BOTTOM":
            self.padding = [0, 0, 0,(get_nav_bar_height()*2.5) + get_nav_bar_height()]

        pass
