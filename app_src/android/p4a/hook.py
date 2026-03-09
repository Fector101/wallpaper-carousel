import os
from pathlib import Path
from pythonforandroid.toolchain import ToolchainCL # type: ignore
from android_widgets.maker import Receiver, inject_foreground_service_types

spec_file_path = "/home/fabian/Documents/Laner/mobile/buildozer.spec"
package = "org.wally.waller"# if not os.path.exists(spec_file_path) else None
# package = "vercel.app.androidNotify"


def insert_to_end_of_xml(new_content,xml_file_content) -> str:
    return xml_file_content.replace("</application>", f"{new_content}\n</application>")

def generate_receivers(package_: str = None) -> str:
    receivers = [
        Receiver(
            name="DetectReceiver",
            actions=["android.intent.action.SCREEN_ON", "android.intent.action.SCREEN_OFF","android.intent.action.USER_PRESENT"]
        ),
        Receiver(
            name="CarouselReceiver",
            actions=["ACTION_STOP", "ACTION_SKIP"]
        ),
        Receiver(
            name="CarouselWidgetProvider",
            actions=[
                "android.intent.action.BOOT_COMPLETED",
                "android.appwidget.action.APPWIDGET_UPDATE",
            ],
            meta_resource="@xml/carousel_widget_info",
        ),
        Receiver(
            name="SimpleWidget",
            label="Simple Text",
            actions=["android.appwidget.action.APPWIDGET_UPDATE"],
            meta_resource="@xml/widgetproviderinfo",
        ),
        Receiver(
            name="ButtonWidget",
            label="Counter Button Demo",
            actions=["android.appwidget.action.APPWIDGET_UPDATE"],
            meta_resource="@xml/button_widget_provider",
        ),

        # Receiver(
        #     name="TheReceiver",
        #     actions=["ALARM_ACTION"]
        # ),
        #
        # Receiver(
        #     name="BootReceiver",
        #     actions=["android.intent.action.BOOT_COMPLETED"]
        # )

    ]

    return "\n\n".join(r.to_xml(package = package_,spec_file_path=spec_file_path) for r in receivers)


def after_apk_build(toolchain: ToolchainCL):
    android_manifest_file_path = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    print(android_manifest_file_path)
    manifest_file_content = android_manifest_file_path.read_text(encoding="utf-8")


    # Add foregroundServiceType to multiple services
    services = {
        "Wallpapercarousel": "specialUse",
        # "Wallpapercarousel": "dataSync",

        }

    manifest_file_content = inject_foreground_service_types(
        manifest_text=manifest_file_content,
        package=package,
        spec_file_path=spec_file_path,
        services=services,
    )

    receiver_xml = generate_receivers(package)


    if receiver_xml.strip() not in manifest_file_content:
        manifest_file_content = manifest_file_content.replace("</application>", f"{receiver_xml}\n</application>")
        print("Receiver added")
    else:
        print("Receiver already exists in manifest")

    file_share_to_other_app_provider = f"""
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="{package}.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/file_paths" />
</provider>

    """
    # text = text.replace("</application>", f"{file_share_to_other_app_provider}\n</application>")
    manifest_file_content = insert_to_end_of_xml(file_share_to_other_app_provider, manifest_file_content)
    android_manifest_file_path.write_text(manifest_file_content, encoding="utf-8")
    print("Successfully_101: Manifest update completed successfully!\n",manifest_file_content)

#     receiver_xml += f"""
#     <receiver
#     android:name="org.wally.waller.MyWorker"
#     android:exported="false" />""" + """
# <provider
#     android:name="androidx.startup.InitializationProvider"
#     android:authorities="${applicationId}.androidx-startup"
#     android:exported="false" />
# """