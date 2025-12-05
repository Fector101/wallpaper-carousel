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
        "Mycarousel": "dataSync"
        # "Tracker": "location",
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
                    print(f"✅ Added foregroundServiceType='{fgs_type}' to Service{name.capitalize()}")
                else:
                    print(f"ℹ️ Service{name.capitalize()} already has foregroundServiceType")
            else:
                print(f"⚠️ Service{name.capitalize()} found but no '/>' closing tag")
        else:
            print(f"⚠️ Service{name.capitalize()} not found in manifest")

    # ====================================================
    # Save final manifest back
    # ====================================================
    manifest_file.write_text(text, encoding="utf-8")
    print("🎯 Manifest update completed successfully!")
