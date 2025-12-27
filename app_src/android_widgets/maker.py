print("----------------------Running android_widget.maker-----------------")

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Receiver:
    name: str
    actions: List[str]
    enabled: bool = True
    exported: bool = False
    label: Optional[str] = None
    meta_name: Optional[str] = "android.appwidget.provider"
    meta_resource: Optional[str] = None

    def to_xml(self, package: str) -> str:
        attrs = [
            f'android:name="{package}.{self.name}"',
            f'android:enabled="{str(self.enabled).lower()}"',
            f'android:exported="{str(self.exported).lower()}"',
        ]

        if self.label:
            attrs.append(f'android:label="{self.label}"')

        xml = [f"<receiver {' '.join(attrs)}>"]
        xml.append("    <intent-filter>")

        for action in self.actions:
            xml.append(f'        <action android:name="{action}" />')

        xml.append("    </intent-filter>")

        if self.meta_resource:
            xml.append(
                f'    <meta-data android:name="{self.meta_name}"\n'
                f'           android:resource="{self.meta_resource}" />'
            )

        xml.append("</receiver>")
        return "\n".join(xml)


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
            name="Image1",
            actions=[
                "android.intent.action.BOOT_COMPLETED",
                "android.appwidget.action.APPWIDGET_UPDATE",
            ],
            meta_resource="@xml/image_test_widget_info",
        ),
    ]

    return "\n\n".join(r.to_xml(package) for r in receivers)



print("------------------ Hello from android_widget.service_injector ------------------")


def inject_foreground_service_types(
    manifest_text: str,
    package: str,
    services: dict[str, str],
) -> str:
    """
    Inject android:foregroundServiceType into <service /> tags.
    :param manifest_text: AndroidManifest.xml file Text Content
    :param package: package.domain + "." + package.name
    :param services:
        {
            "service_name": "service_type",
            "music": "mediaPlayback",
            "location": "location"
        }
    """

    for name, fgs_type in services.items():
        service_name = f"{package}.Service{name.capitalize()}"
        target = f'android:name="{service_name}"'

        pos = manifest_text.find(target)
        if pos == -1:
            print(f"Error_101: {service_name} not found in manifest")
            continue

        # Find the end of the <service ... /> tag
        end = manifest_text.find("/>", pos)
        if end == -1:
            print(f"Error_101: {service_name} found but no '/>' closing tag")
            continue

        segment = manifest_text[pos:end]

        if "android:foregroundServiceType=" in segment:
            print(f"Error_101: {service_name} already has foregroundServiceType")
            continue

        manifest_text = (
                manifest_text[:end]
                + f' android:foregroundServiceType="{fgs_type}"'
                + manifest_text[end:]
        )

        print(
            f"Successfully_101: Added foregroundServiceType='{fgs_type}' "
            f"to {service_name}"
        )

    return manifest_text
