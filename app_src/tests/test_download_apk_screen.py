from unittest import mock

import pytest

import ui.screens.download_apk_screen as d

VERSION = "1.0.10"
EXPECTED_FILENAME = f"waller-v{VERSION}.apk"
EXPECTED_URL = (
    "https://github.com/Fector101/wallpaper-carousel/releases/download/"
    f"v{VERSION}/{EXPECTED_FILENAME}"
)


def test_get_apk_filename_includes_version_prefix():
    assert d.get_apk_filename("1.0.10") == "waller-v1.0.10.apk"


def test_get_apk_download_url_uses_versioned_asset():
    assert d.get_apk_download_url("1.0.10") == EXPECTED_URL


def test_download_url_last_segment_matches_asset_filename():
    url = d.get_apk_download_url(VERSION)
    assert url.rsplit("/", 1)[-1] == d.get_apk_filename(VERSION)


def test_get_apk_path_uses_versioned_filename(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "get_apk_directory", lambda: str(tmp_path))
    assert d.get_apk_path(VERSION) == str(tmp_path / EXPECTED_FILENAME)


def test_apk_is_valid_finds_versioned_file(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "get_apk_directory", lambda: str(tmp_path))
    apk = tmp_path / EXPECTED_FILENAME
    apk.write_bytes(b"x" * 100)
    result = d.apk_is_valid(str(apk), 100)
    assert result == str(apk)


def test_apk_is_valid_rejects_wrong_size(tmp_path):
    apk = tmp_path / EXPECTED_FILENAME
    apk.write_bytes(b"x" * 10)
    assert d.apk_is_valid(str(apk), 100) is None


class _FakeResponse:
    def __init__(self, content):
        self.content = content
        self.headers = {"content-length": str(len(content))}

    def raise_for_status(self):
        return None

    def iter_content(self, _):
        yield self.content


@pytest.fixture
def fake_download_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "get_apk_directory", lambda: str(tmp_path))
    return tmp_path


def test_download_apk_saves_to_versioned_filename(fake_download_dir):
    with mock.patch("requests.get", return_value=_FakeResponse(b"y" * 100)):
        path = d.download_apk(EXPECTED_URL, filename=EXPECTED_FILENAME)
    assert path == str(fake_download_dir / EXPECTED_FILENAME)
    assert (fake_download_dir / EXPECTED_FILENAME).read_bytes() == b"y" * 100


def test_download_apk_resumes_partial_file_with_range(fake_download_dir):
    target = fake_download_dir / EXPECTED_FILENAME
    target.write_bytes(b"a" * 40)

    captured = {}

    class _ResumeResponse:
        headers = {"content-length": "60"}

        def raise_for_status(self):
            return None

        def iter_content(self, _):
            yield b"b" * 60

    def fake_get(url, headers=None, stream=None):
        captured["headers"] = headers
        return _ResumeResponse()

    with mock.patch("requests.get", side_effect=fake_get):
        path = d.download_apk(EXPECTED_URL, filename=EXPECTED_FILENAME)

    assert captured["headers"] == {"Range": "bytes=40-"}
    assert path == str(target)
    assert target.read_bytes() == b"a" * 40 + b"b" * 60


class _FakeStreak:
    def bind(self, *_, **__):
        return None

    def unbind(self, *_, **__):
        return None


class _FakeUpdateButton:
    def __init__(self):
        self.clicked = False
        self.streak = _FakeStreak()

    def update_progress(self, *_):
        return None


class _FakeLaterButton:
    text = ""


def _instantiate_screen():
    from kivy.event import EventDispatcher
    from kivy.properties import StringProperty
    from kivymd.app import MDApp

    class _AppStub(EventDispatcher):
        device_theme = StringProperty("dark")

    fake_app = _AppStub()

    class _FakeMDApp(MDApp):
        pass

    fake_mdapp = _FakeMDApp()
    with mock.patch("utils.model.get_app", return_value=fake_app), \
         mock.patch("kivy.app.App.get_running_app", return_value=fake_mdapp):
        return d.DownloadApkScreen()


def test_start_download_uses_versioned_url_and_filename():
    screen = _instantiate_screen()
    screen.built_ui = True
    screen.new_version = VERSION
    screen.apk_size = 100
    screen.update_button = _FakeUpdateButton()
    screen.later_button = _FakeLaterButton()

    captured = {}

    class _FakeThread:
        def __init__(self, target=None, daemon=None):
            captured["target"] = target

        def start(self):
            captured["target"]()

    with mock.patch("threading.Thread", _FakeThread), \
         mock.patch.object(d, "apk_is_valid", return_value=None), \
         mock.patch.object(d.Clock, "schedule_once", lambda *a, **k: None), \
         mock.patch.object(d, "download_apk", return_value=None) as download_apk:
        screen.start_download()
        download_apk.assert_called_once_with(
            EXPECTED_URL,
            progress_callback=mock.ANY,
            filename=EXPECTED_FILENAME,
        )


def test_find_and_delete_unused_apks_removes_versioned_file(tmp_path, monkeypatch):
    monkeypatch.setattr(d, "get_apk_directory", lambda: str(tmp_path))
    leftover = tmp_path / EXPECTED_FILENAME
    leftover.write_bytes(b"x")
    d.find_and_delete_unused_apks(VERSION)
    assert not leftover.exists()


def test_release_workflow_uploads_versioned_and_legacy_assets():
    import os

    workflow = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".github", "workflows", "android-build.yml",
    )
    if not os.path.exists(workflow):
        pytest.skip("workflow file not present in checkout")
    content = open(workflow, encoding="utf-8").read()
    assert "bin/waller-v${{ steps.version.outputs.VERSION }}.apk" in content
    assert "bin/waller.apk" in content