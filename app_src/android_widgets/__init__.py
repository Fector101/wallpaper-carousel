
import os
import traceback

from .config import is_platform_android
from .aw_logging import logger, enable_logging


__all__ = ["logger"]

from .config import get_python_activity_context

try:
    from .java_classes import *
except Exception as e:
    print("[android_widgets] Import Java classes Error:", e)
    from .facade import *

    RemoteViews_ = RemoteViews
    AppWidgetManager_ = AppWidgetManager

from .tools import SpecFile

if is_platform_android():
    enable_logging()

def get_resources():
    context = get_python_activity_context()
    return context.getResources()

def get_package_name():
    context = get_python_activity_context()
    return context.getPackageName()  # package.domain + "." + package.name

def get_resource(name, folder_base):
    resources = get_resources()
    package_name = get_package_name()
    print("resources.getIdentifier",name, folder_base,"id:",resources.getIdentifier(name, folder_base, package_name))
    return resources.getIdentifier(name, folder_base, package_name)

def get_buildozer_spec_file_path():
    return os.path.join(os.getcwd(), "buildozer.spec")


class Layout:
    def __init__(self, layout_name):
        """

        :param layout_name: base name without '.xml'
        """
        self.layout_name = layout_name
        self.id = get_resource(layout_name, "layout")
        self.check_if_layout_exists()

    @property
    def layout_path(self):
        specFile = SpecFile(get_buildozer_spec_file_path())
        resources_folder = specFile.get("app", "android.add_resources", '')
        layout_path = os.path.join(resources_folder, 'layout', self.layout_name + '.xml')
        return layout_path

    def check_if_layout_exists(self):
        if is_platform_android():
            if not self.id:
                logger.error(f"Layout doesn't exist: {self.layout_name}")
            return None

        spec_file_path = get_buildozer_spec_file_path()
        # This not a real path on android /data/data/org.wally.waller/files/app/buildozer.spec

        if not os.path.exists(spec_file_path):
            logger.debug(f"buildozer.spec file not found at: {spec_file_path}")
            return None

        if not os.path.exists(self.layout_path):
            logger.error(f"Layout doesn't exist: {self.layout_path}")
            return None
        else:
            logger.info(f"Found Layout: {self.layout_path}")
            return None


class RemoteViews:
    def __init__(self, layout:Layout):
        self.layout = layout
        layout_id = layout.id
        package_name = get_package_name()
        self.main = RemoteViews_(package_name, layout_id)

    def setTextViewText(self, text_id, text):
        resources = get_resources()
        package_name = get_package_name()
        __text_id = resources.getIdentifier(text_id, "id",package_name)
        # print("text_id:", __text_id)
        if not __text_id:
            logger.error(f"Text ID doesn't exist: No @+id/{text_id} in res/layout/{self.layout.layout_name}.xml")
            return None
        self.main.setTextViewText(__text_id, String(text))
        return None


class AppWidgetManager:
    def __init__(self, java_class_name):
        self.java_class_name = java_class_name
        context = get_python_activity_context()
        package_name = get_package_name()
        component = ComponentName(context, f'{package_name}.{java_class_name}')
        self.main = AppWidgetManager_.getInstance(context)
        self.widget_ids = self.main.getAppWidgetIds(component)
        self.check_if_java_file_exists()

    def updateAppWidget(self, java_view_object):
        self.main.updateAppWidget(self.widget_ids, java_view_object)

    @property
    def java_file_path(self):
        specFile = SpecFile(get_buildozer_spec_file_path())
        jave_src_folder = specFile.get("app", "android.add_src", '')
        java_file_path__ = os.path.join(jave_src_folder, self.java_class_name + '.java')
        return java_file_path__

    def check_if_java_file_exists(self):
        spec_file_path = get_buildozer_spec_file_path()
        if is_platform_android():
            if not self.widget_ids: # when wrong .java file name is given self.widget_ids == []
                logger.warning(f"Java File might not exist: {self.java_class_name}.java")
            return None

        if not os.path.exists(spec_file_path):
            logger.debug(f"buildozer.spec file not found at: {spec_file_path}")
            return None

        java_file_path = self.java_file_path
        if not os.path.exists(java_file_path):
            logger.error(f"Java File doesn't exist: {java_file_path}")
            # TODO Write emtpy java file
            return None
        else:
            logger.info(f"Found Layout: {java_file_path}")
            return None

# try:
#     print("-"*5,'test 1','-'*5)
#     appWidgetManager = AppWidgetManager("Image")
#     print("The widget_ids:", appWidgetManager.widget_ids)
#
#     text_layout = Layout("image_test_widget")
#     views = RemoteViews(layout=text_layout)
#     views.setTextViewText(text_id="widget_text", text="Frm py 1")
#
#     appWidgetManager.updateAppWidget(java_view_object=views.main)
# except Exception as e:
#     print("-"*5,"test 1  Error:",e,"-"*5)
#     traceback.print_exc()
#
# try:
#     print("-"*5,'test 2','-'*5)
#
#     appWidgetManager = AppWidgetManager("Image1")
#     print("The widget_ids:", appWidgetManager.widget_ids)
#
#     text_layout = Layout("image_test_widget1")
#     views = RemoteViews(layout=text_layout)
#     views.setTextViewText(text_id="widget_text", text="Frm py 2")
#
#     appWidgetManager.updateAppWidget(java_view_object=views.main)
# except Exception as e:
#     print("-" * 5, "test 2  Error:",e, "-" * 5)
#     traceback.print_exc()
#
# try:
#     print("-" * 5, 'test 3', '-' * 5)
#
#     appWidgetManager = AppWidgetManager("Image1")
#     print("The widget_ids:", appWidgetManager.widget_ids)
#
#     text_layout = Layout("image_test_widget")
#     views = RemoteViews(layout=text_layout)
#     views.setTextViewText(text_id="widget_text3", text="Frm py 3")
#
#     appWidgetManager.updateAppWidget(java_view_object=views.main)
# except Exception as e:
#     print("-" * 5, "test 3 Error:",e, "-" * 5)
#     traceback.print_exc()

# For Reference
# AppWidgetManager = autoclass('android.appwidget.AppWidgetManager')
# ComponentName = autoclass('android.content.ComponentName')
# RemoteViews = autoclass('android.widget.RemoteViews')
#
# context = get_python_activity_context()  # PythonActivity.mActivity.getApplicationContext()
# resources = context.getResources()
# package_name = context.getPackageName()
#
# # IMPORTANT: use CLASS NAME STRING, NOT autoclass
# component = ComponentName( context, 'org.wally.waller.Image1' )
#
# appWidgetManager = AppWidgetManager.getInstance(context)
# ids = appWidgetManager.getAppWidgetIds(component)
#
# text_layout = resources.getIdentifier("image_test_widget", "layout", package_name)
# title_id = resources.getIdentifier("widget_text", "id", package_name)
#
# views = RemoteViews(package_name, text_layout)
# views.setTextViewText(title_id, AndroidString("Madness"))
# appWidgetManager.updateAppWidget(ids, views)