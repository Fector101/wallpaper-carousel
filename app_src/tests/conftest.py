import sys
import tempfile
from pathlib import Path
from unittest import mock

APP_SRC = Path(__file__).resolve().parent.parent
if str(APP_SRC) not in sys.path:
    sys.path.insert(0, str(APP_SRC))

def _mock_module(name, **attrs):
    m = mock.MagicMock()
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

_mock_module(
    "android_notify.config",
    on_android_platform=mock.MagicMock(return_value=False),
    on_pydroid_app=mock.MagicMock(return_value=False),
    from_service_file=mock.MagicMock(return_value=False),
    get_package_name=mock.MagicMock(return_value="com.waller.test"),
)
_mock_module("android_notify.internal.java_classes")
_mock_module("android_notify.internal")
_mock_module("android_notify")
for name in ("android", "android_widgets", "android.permissions", "jnius"):
    _mock_module(name)

import utils.helper as helper

_TMP_APP = Path(tempfile.mkdtemp())
helper.appFolder = lambda: str(_TMP_APP)
