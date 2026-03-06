from utils.helper import appFolder,load_kv_file  # type
import os
from kivy.lang import Builder

load_kv_file(py_file_absolute_path=__file__)
# with open(os.path.join(appFolder(),"ui","components","templates.kv"), encoding="utf-8") as kv_file:
#     Builder.load_string(kv_file.read(), filename="MyBtmSheet.kv")
