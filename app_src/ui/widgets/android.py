from android_notify.config import on_android_platform, from_service_file

if on_android_platform() and not from_service_file():
    from kivymd.toast import toast # type: ignore

else:
    def toast(text=None,length_long=0):
        print(f'Fallback toast - text: {text}, length_long: {length_long}')

