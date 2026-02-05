import json
import threading
import traceback
from pythonosc import dispatcher, osc_server, udp_client

from utils.helper import get_free_port
from utils.logger import app_logger


SERVICE_IP = "0.0.0.0"


class UIServiceListener:
    on_changed_wallpaper = None
    on_changed_homescreen_widget = None
    on_countdown_change = None
    on_stopped_all = None

    def __init__(self):
        self.dispatcher = None
        self.UI_PORT = get_free_port()

    def setup_dispatcher(self):
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/countdown_change", self.countdown_change)
        self.dispatcher.map("/changed_wallpaper", self.changed_wallpaper)
        self.dispatcher.map("/changed_homescreen_widget", self.changed_homescreen_widget)
        self.dispatcher.map("/stopped", self.stopped_all)

    def __listen(self):
        server = osc_server.ThreadingOSCUDPServer(
            (SERVICE_IP, self.UI_PORT),
            self.dispatcher
        )
        server.serve_forever()

    @staticmethod
    def __parse_data(data):
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError as error_parsing_json:
            app_logger.exception(error_parsing_json)
            traceback.print_exc()
            return None

    def start(self, do_thread=True):
        self.setup_dispatcher()
        if not do_thread:
            self.__listen()
            return None
        try:
            threading.Thread(
                target=self.__listen,
                daemon=True,
                name="UIServiceListenerThread"
            ).start()
        except Exception as error_in_UIServiceListener_thread:
            print("error_in_UIServiceListener_thread:", error_in_UIServiceListener_thread)
            traceback.print_exc()
        return self

    def countdown_change(self, _, data):
        # TAG = "countdown_change"
        # app_logger.debug(f"[{TAG}] data: {data}")
        if not data:
            return None

        json_data = self.__parse_data(data)
        if not json_data:
            return None

        seconds = json_data["seconds"] if "seconds" in json_data else None

        if self.on_countdown_change:
            try:
                self.on_countdown_change(seconds)
            except Exception as error_on_countdown_change:
                app_logger.exception(error_on_countdown_change)
                traceback.print_exc()

        return None

    def changed_wallpaper(self, _, data):
        TAG = "changed_wallpaper"
        app_logger.debug(f"[{TAG}] data: {data}")
        if not data:
            return None

        json_data = self.__parse_data(data)
        if not json_data:
            return None

        current_wallpaper = json_data["current_wallpaper"] if "current_wallpaper" in json_data else None
        next_wallpaper = json_data["next_wallpaper"] if "next_wallpaper" in json_data else None

        if self.on_changed_wallpaper:
            try:
                self.on_changed_wallpaper(current_wallpaper, next_wallpaper)
            except Exception as error_on_changed_wallpaper:
                app_logger.exception(error_on_changed_wallpaper)
                traceback.print_exc()

        return None

    def changed_homescreen_widget(self, _, data):
        TAG = "changed_homescreen_widget"
        app_logger.debug(f"[{TAG}] data: {data}")
        if not data:
            return None
        try:
            json_data = json.loads(data)
        except json.decoder.JSONDecodeError as error_parsing_json:
            app_logger.exception(error_parsing_json)
            traceback.print_exc()
            return None

        current_wallpaper = json_data["current_wallpaper"] if "current_wallpaper" in json_data else None
        next_wallpaper = json_data["next_wallpaper"] if "next_wallpaper" in json_data else None

        if self.on_changed_homescreen_widget:
            try:
                self.on_changed_homescreen_widget(current_wallpaper, next_wallpaper)
            except Exception as error_on_changed_homescreen_widget:
                app_logger.exception(error_on_changed_homescreen_widget)
                traceback.print_exc()

        return None

    def stopped_all(self, _, data):
        TAG = "stopped_all"
        app_logger.info(f"[{TAG}] data: {data}")
        # if not data:
        #     return None
        # # try:
        #     JSON_data = json.loads(data)
        # except json.decoder.JSONDecodeError as error_parsing_json:
        #     app_logger.exception(error_parsing_json)
        #     return None

        if self.on_stopped_all:
            try:
                self.on_stopped_all()
            except Exception as error_on_stopped_all:
                app_logger.exception(error_on_stopped_all)
                traceback.print_exc()

        return None


class UIServiceMessenger:
    TAG = "UIServiceMessenger"

    def __init__(self, service_port: int):
        self.__client = None
        try:
            self.__client = udp_client.SimpleUDPClient(SERVICE_IP, service_port)
            app_logger.info(f"[{self.TAG}] Messenger Connected to {SERVICE_IP}:{service_port}")
        except Exception as error_trying_to_connect:
            app_logger.exception(
                f"[{self.TAG}] Could not Connected to {SERVICE_IP}:{service_port}, error: {error_trying_to_connect}")
            traceback.print_exc()

    def __send_data_to_service(self, path, dict_data):
        self.__client.send_message(address=path, value=json.dumps(dict_data))

    def change_next(self):
        app_logger.debug("Changing next wallpaper")
        self.__send_data_to_service("/change-next", {})

    def toggle_home_screen_widget_changes(self):
        app_logger.debug("Toggling Home Screen Widgets Loop")
        self.__send_data_to_service("/toggle_home_screen_widget_changes", {})


if __name__ == "__main__":
    UIServiceListener().start(False)
