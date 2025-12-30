import traceback
from pathlib import Path
from pythonforandroid.toolchain import ToolchainCL

from android_widgets.maker import Receiver, inject_foreground_service_types



def generate_receivers(package: str) -> str:
    receivers = [
        Receiver(
            name="Action1",
            actions=["android.intent.action.BOOT_COMPLETED"],
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
        Receiver(
            name="CarouselProvider",
            actions=[
                "android.intent.action.BOOT_COMPLETED",
                "android.appwidget.action.APPWIDGET_UPDATE",
            ],
            meta_resource="@xml/carousel_widget_info",
        ),
    ]

    return "\n\n".join(r.to_xml(package) for r in receivers)


def after_apk_build(toolchain: ToolchainCL):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    text = manifest_file.read_text(encoding="utf-8")

    package = "org.wally.waller"

    # Add foregroundServiceType to multiple services
    services = { "Wallpapercarousel": "dataSync", "Mytester": "dataSync" }

    text = inject_foreground_service_types(
        manifest_text=text,
        package=package,
        services=services,
    )

    receiver_xml = generate_receivers(package)

    if receiver_xml.strip() not in text:
        if "</application>" in text:
            text = text.replace("</application>", f"{receiver_xml}\n</application>")
            print("Receiver added")
        else: 
            print("Could not find </application> to insert receiver")
    else: 
        print("Receiver already exists in manifest")




    # ====================================================
    # Save final manifest back
    # ====================================================
    manifest_file.write_text(text, encoding="utf-8")
    print("Successfully_101: Manifest update completed successfully!")
    print(text)


