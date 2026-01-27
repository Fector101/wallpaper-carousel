import os
from pathlib import Path
from pythonforandroid.toolchain import ToolchainCL
from android_widgets.maker import Receiver, inject_foreground_service_types

spec_file_path = "/home/fabian/Documents/Laner/mobile/buildozer.spec"
package = "org.wally.waller" if not os.path.exists(spec_file_path) else None


def generate_receivers(package_: str = None) -> str:
    receivers = [
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
        # )

    ]

    return "\n\n".join(r.to_xml(package = package_,spec_file_path=spec_file_path) for r in receivers)


def after_apk_build(toolchain: ToolchainCL):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    text = manifest_file.read_text(encoding="utf-8")

    # package = "vercel.app.androidNotify"

    # Add foregroundServiceType to multiple services
    services = {
        "Wallpapercarousel": "dataSync",
        # "Mytester": "dataSync"
        }

    text = inject_foreground_service_types(
        manifest_text=text,
        package=package,
        spec_file_path=spec_file_path,
        services=services,
    )

    receiver_xml = generate_receivers(package)
#     receiver_xml += f"""
#     <receiver
#     android:name="{package}.MyWorker"
#     android:exported="false" />""" + """
# <provider
#     android:name="androidx.startup.InitializationProvider"
#     android:authorities="${applicationId}.androidx-startup"
#     android:exported="false" />
# """

    if receiver_xml.strip() not in text:
        if "</application>" in text:
            text = text.replace("</application>", f"{receiver_xml}\n</application>")
            print("Receiver added")
        else:
            print("Could not find </application> to insert receiver")
    else:
        print("Receiver already exists in manifest")

    manifest_file.write_text(text, encoding="utf-8")
    print("Successfully_101: Manifest update completed successfully!")
    print(text)
