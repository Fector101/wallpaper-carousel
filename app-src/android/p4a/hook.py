from pathlib import Path
from pythonforandroid.toolchain import ToolchainCL


def after_apk_build(toolchain: ToolchainCL):
    manifest_file = Path(toolchain._dist.dist_dir) / "src" / "main" / "AndroidManifest.xml"
    text = manifest_file.read_text(encoding="utf-8")

    package = "org.wally.waller"

    # ==========================================
    # Add foregroundServiceType to multiple services
    # ==========================================
    services = {
        "Wallpapercarousel": "dataSync",
        "Mytester": "dataSync",
    }

    for name, fgs_type in services.items():
        target = f'android:name="{package}.Service{name.capitalize()}"'
        pos = text.find(target)

        if pos != -1:
            end = text.find("/>", pos)
            if end != -1:
                if "foregroundServiceType=" not in text[pos:end]:
                    text = (
                        text[:end] +
                        f' android:foregroundServiceType="{fgs_type}"' +
                        text[end:]
                    )
                    print(f"Successfully_101: Added foregroundServiceType='{fgs_type}' to Service{name.capitalize()}")
                else:
                    print(f"Error_101: Service{name.capitalize()} already has foregroundServiceType")
            else:
                print(f"Error_101: Service{name.capitalize()} found but no '/>' closing tag")
        else:
            print(f"Error_101: Service{name.capitalize()} not found in manifest")

    receiver_xml = f'''
    <receiver android:name="{package}.SimpleWidget"
              android:enabled="true"
              android:exported="false"
              android:label="Simple Text">
        <intent-filter>
            <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
        </intent-filter>
        <meta-data android:name="android.appwidget.provider"
               android:resource="@xml/widgetproviderinfo" />
    </receiver>
    
    <receiver
        android:name="{package}.ButtonWidget"
        android:exported="false"
        android:label="Counter Button Demo">
        <intent-filter>
            <action android:name="android.appwidget.action.APPWIDGET_UPDATE"/>
        </intent-filter>
    
        <meta-data
            android:name="android.appwidget.provider"
            android:resource="@xml/button_widget_provider" />
    </receiver>

    '''

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

