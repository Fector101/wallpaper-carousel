try:
    from kivymd.toast import toast
except TypeError:
    def toast(text=None,length_long=0):
        print(f'Fallback toast - text: {text}, length_long: {length_long}')