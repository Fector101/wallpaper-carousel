"""The new-release-download flow, tested against a laptop-hosted release server.

Nothing here touches the network. ``local_release_server`` serves the release JSON and
the assets over real sockets on 127.0.0.1, and the app's own production functions are
exercised against it -- no mocked ``requests``.
"""

import json
import os
from unittest import mock

import pytest
import ui.screens.download_apk_screen as d
from local_release_server import DEFAULT_NOTES, ReleaseServer
from update_download_e2e import next_version

# The version this suite advertises must be *newer* than the one the app reports,
# because `check_update` answers "Already up to date." when the two match. Deriving
# it keeps a release bump in utils/constants.py from turning these tests red.
NEW_VERSION = next_version(d.VERSION)
APK_BYTES = 250_000


class _StubEvent:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


@pytest.fixture
def inline_clock():
    """Run Clock callbacks synchronously so check_update's hops are observable."""
    events = []

    def run(callback, timeout=0):
        event = _StubEvent()
        events.append(event)
        callback(timeout)
        return event

    with mock.patch.object(d.Clock, "schedule_once", side_effect=run):
        yield events


@pytest.fixture
def apk_file(tmp_path):
    path = tmp_path / "new.apk"
    path.write_bytes(b"APK" + bytes(APK_BYTES - 3))
    return path


@pytest.fixture
def download_dir(tmp_path, monkeypatch):
    directory = tmp_path / "files"
    directory.mkdir()
    monkeypatch.setattr(d, "get_apk_directory", lambda: str(directory))
    monkeypatch.delenv("WALLER_UPDATE_API_URL", raising=False)
    monkeypatch.delenv("WALLER_UPDATE_BASE_URL", raising=False)
    return directory


@pytest.fixture
def server(apk_file):
    with ReleaseServer(version=NEW_VERSION, apk_path=str(apk_file)) as running:
        yield running


@pytest.fixture
def pointed_at(server, download_dir):
    """Point the app at the local server the same way the device test does."""
    (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(server.endpoint_config()))
    return server


def _collect():
    return [], []


def apk_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def test_endpoint_config_points_the_app_at_the_local_server(pointed_at, download_dir):
    assert json.loads((download_dir / d.UPDATE_ENDPOINT_FILENAME).read_text()) == pointed_at.endpoint_config()
    assert d.get_release_api_url() == pointed_at.api_url
    assert d.get_release_base_url() == pointed_at.base_url
    assert d.get_apk_download_url(NEW_VERSION) == (
        f"{pointed_at.base_url}/v{NEW_VERSION}/waller-v{NEW_VERSION}.apk"
    )


def test_without_an_override_the_github_urls_are_used(download_dir):
    assert not (download_dir / d.UPDATE_ENDPOINT_FILENAME).exists()
    assert d.get_update_endpoint_config() == {}
    assert d.get_release_api_url() == d.DEFAULT_RELEASE_API_URL
    assert d.get_release_base_url() == d.DEFAULT_RELEASE_BASE_URL


def test_env_var_beats_the_override_file(pointed_at, monkeypatch):
    monkeypatch.setenv("WALLER_UPDATE_API_URL", "http://192.0.2.1/api")
    monkeypatch.setenv("WALLER_UPDATE_BASE_URL", "http://192.0.2.1/dl")
    assert d.get_release_api_url() == "http://192.0.2.1/api"
    assert d.get_release_base_url() == "http://192.0.2.1/dl"


def test_a_corrupt_override_file_falls_back_to_github(download_dir):
    (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text("not json at all")
    assert d.get_update_endpoint_config() == {}
    assert d.get_release_api_url() == d.DEFAULT_RELEASE_API_URL


def test_a_non_object_override_file_falls_back_to_github(download_dir):
    (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text('["http://192.0.2.1"]')
    assert d.get_update_endpoint_config() == {}
    assert d.get_release_api_url() == d.DEFAULT_RELEASE_API_URL


def test_a_base_url_only_override_is_not_an_api_override(download_dir):
    (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(
        json.dumps({"base_url": "http://127.0.0.1:8000/downloads"})
    )

    # The version check only reads api_url, so this config leaves it on GitHub. Counting it
    # as an override would let a debug build auto-check against api.github.com.
    assert d.get_release_api_url() == d.DEFAULT_RELEASE_API_URL
    assert d._has_update_api_override() is False


def test_a_config_api_url_is_an_api_override(pointed_at):
    assert d._has_update_api_override() is True


def test_an_env_var_is_an_api_override_without_a_file(download_dir, monkeypatch):
    monkeypatch.setenv("WALLER_UPDATE_API_URL", "http://127.0.0.1:8000/api")

    assert d._has_update_api_override() is True


def test_check_update_offers_the_new_release(pointed_at, inline_clock):
    shown, not_shown = _collect()

    d.check_update(lambda **kw: shown.append(kw), lambda **kw: not_shown.append(kw))

    assert not not_shown
    assert len(shown) == 1
    assert shown[0]["new_version"] == NEW_VERSION
    assert shown[0]["apk_size"] == pointed_at.apk_size
    assert DEFAULT_NOTES in shown[0]["release_notes"]
    assert pointed_at.api_path in pointed_at.paths_requested()
    assert f"/releases/download/v{NEW_VERSION}/{pointed_at.notes_name}" in pointed_at.paths_requested()


def test_check_update_falls_back_to_default_notes_when_the_asset_is_absent(
    apk_file, inline_clock, download_dir
):
    with ReleaseServer(version=NEW_VERSION, apk_path=str(apk_file), notes="") as bare:
        (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(bare.endpoint_config()))
        shown, _ = _collect()

        d.check_update(lambda **kw: shown.append(kw), lambda **kw: None)

    assert shown[0]["release_notes"] == d.DEFAULT_RELEASE_NOTE


def test_check_update_reports_already_up_to_date(download_dir, inline_clock):
    with ReleaseServer(version=d.VERSION, notes="") as same:
        (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(same.endpoint_config()))
        shown, not_shown = _collect()

        d.check_update(lambda **kw: shown.append(kw), lambda **kw: not_shown.append(kw))

    assert not shown
    assert [kw["msg"] for kw in not_shown] == ["Already up to date."]


def test_check_update_deletes_stale_apks_when_already_current(download_dir, inline_clock):
    stale = download_dir / "waller-v0.0.1.apk"
    stale.write_bytes(b"old")

    with ReleaseServer(version=d.VERSION, notes="") as same:
        (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(same.endpoint_config()))
        d.check_update(lambda **kw: None, lambda **kw: None)

    assert not stale.exists()


def test_check_update_reports_no_connection(download_dir, inline_clock):
    shown, not_shown = _collect()
    (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(
        json.dumps({"api_url": "http://127.0.0.1:1/releases/latest"})
    )

    d.check_update(lambda **kw: shown.append(kw), lambda **kw: not_shown.append(kw))

    assert not shown
    assert [kw["msg"] for kw in not_shown] == ["No internet connection"]


def test_check_update_reports_a_read_timeout(download_dir, inline_clock):
    import requests

    shown, not_shown = _collect()
    (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(
        json.dumps({"api_url": "http://127.0.0.1:1/releases/latest"})
    )

    with mock.patch("requests.get", side_effect=requests.exceptions.ReadTimeout("slow")):
        d.check_update(lambda **kw: shown.append(kw), lambda **kw: not_shown.append(kw))

    assert not shown
    assert [kw["msg"] for kw in not_shown] == ["Timeout Error, Slow internet Connection"]


def test_check_update_reports_a_server_error(pointed_at, inline_clock):
    shown, not_shown = _collect()

    with mock.patch("requests.get", side_effect=RuntimeError("boom")):
        d.check_update(lambda **kw: shown.append(kw), lambda **kw: not_shown.append(kw))

    assert not shown
    assert not_shown[0]["msg"].startswith("Failed:")


def test_download_apk_saves_the_served_bytes(pointed_at, download_dir):
    percents = []

    path = d.download_apk(
        d.get_apk_download_url(NEW_VERSION),
        filename=d.get_apk_filename(NEW_VERSION),
        progress_callback=percents.append,
    )

    expected = download_dir / d.get_apk_filename(NEW_VERSION)
    assert path == str(expected)
    assert os.path.getsize(path) == pointed_at.apk_size
    assert apk_bytes(path)[:3] == b"APK"
    assert percents[-1] == 100
    assert percents == sorted(percents)


def test_download_apk_resumes_from_a_partial_file(pointed_at, download_dir):
    partial = download_dir / d.get_apk_filename(NEW_VERSION)
    partial.write_bytes(apk_bytes(pointed_at.apk_path)[:1000])

    path = d.download_apk(d.get_apk_download_url(NEW_VERSION), filename=d.get_apk_filename(NEW_VERSION))

    assert path == str(partial)
    assert pointed_at.requests[0]["range"] == "bytes=1000-"
    assert apk_bytes(path) == apk_bytes(pointed_at.apk_path)


def test_download_apk_restarts_when_the_server_ignores_the_range(apk_file, download_dir):
    with ReleaseServer(version=NEW_VERSION, apk_path=str(apk_file), range_mode="ignore") as ignoring:
        (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(ignoring.endpoint_config()))
        partial = download_dir / d.get_apk_filename(NEW_VERSION)
        partial.write_bytes(apk_bytes(apk_file)[:1000])

        path = d.download_apk(d.get_apk_download_url(NEW_VERSION), filename=d.get_apk_filename(NEW_VERSION))

        assert path == str(partial)
        assert apk_bytes(path) == apk_bytes(apk_file)


def test_download_apk_restarts_when_the_range_is_rejected(apk_file, download_dir):
    with ReleaseServer(version=NEW_VERSION, apk_path=str(apk_file), range_mode="reject") as rejecting:
        (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(rejecting.endpoint_config()))
        partial = download_dir / d.get_apk_filename(NEW_VERSION)
        partial.write_bytes(apk_bytes(apk_file)[:1000])

        path = d.download_apk(d.get_apk_download_url(NEW_VERSION), filename=d.get_apk_filename(NEW_VERSION))

        assert path == str(partial)
        assert apk_bytes(path) == apk_bytes(apk_file)


class _FakeResponse:
    def __init__(self, status_code, headers, body):
        self.status_code = status_code
        self.headers = headers
        self._body = body
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.closed = True
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError(f"unexpected HTTP {self.status_code}")

    def iter_content(self, _chunk_size):
        yield self._body


def _lying_about_the_offset(data, content_range, replayed):
    """A server that answers a ranged request with a 206 whose Content-Range lies.

    `replayed` is what it sends instead of the bytes we asked for, and the retry after a
    restart carries no Range header and gets the whole file. So the caller ending up with
    `data` intact means it restarted, and a doubled-up first half means it appended.
    """
    requested = []
    served = []

    def get(_url, headers=None, **_kwargs):
        headers = headers or {}
        requested.append(headers)
        if "Range" not in headers:
            response = _FakeResponse(200, {"content-length": str(len(data))}, data)
        else:
            ranged_headers = {"content-length": str(len(replayed))}
            if content_range is not None:
                ranged_headers["Content-Range"] = content_range
            response = _FakeResponse(206, ranged_headers, replayed)
        served.append(response)
        return response

    get.requested = requested
    get.served = served
    return get


@pytest.mark.parametrize(
    "content_range",
    [
        "bytes 0-999/2000",  # starts at 0 while we asked for 1000
        "bytes */2000",  # reports no offset at all
        "bytes 1000",  # no dash
        "1000-1999/2000",  # no unit
        "items 1000-1999/2000",  # wrong unit
    ],
    ids=["wrong-offset", "star", "no-dash", "no-unit", "wrong-unit"],
)
def test_download_apk_restarts_when_a_206_cannot_be_trusted(apk_file, download_dir, content_range):
    data = apk_bytes(apk_file)
    partial = download_dir / d.get_apk_filename(NEW_VERSION)
    partial.write_bytes(data[:1000])
    fake = _lying_about_the_offset(data, content_range, data[:1000])

    with mock.patch("requests.get", fake):
        path = d.download_apk("http://local/apk", filename=d.get_apk_filename(NEW_VERSION))

    assert "Range" in fake.requested[0], "a resume was attempted"
    assert len(fake.requested) == 2, "the download was retried from byte 0"
    assert apk_bytes(path) == data


def test_download_apk_restarts_when_the_206_omits_content_range(apk_file, download_dir):
    data = apk_bytes(apk_file)
    partial = download_dir / d.get_apk_filename(NEW_VERSION)
    partial.write_bytes(data[:1000])
    fake = _lying_about_the_offset(data, None, data[:1000])

    with mock.patch("requests.get", fake):
        path = d.download_apk("http://local/apk", filename=d.get_apk_filename(NEW_VERSION))

    assert len(fake.requested) == 2, "the download was retried from byte 0"
    assert apk_bytes(path) == data


def test_download_apk_closes_the_response_it_abandons_when_restarting(apk_file, download_dir):
    data = apk_bytes(apk_file)
    partial = download_dir / d.get_apk_filename(NEW_VERSION)
    partial.write_bytes(data[:1000])
    fake = _lying_about_the_offset(data, "bytes 0-999/2000", data[:1000])

    with mock.patch("requests.get", fake):
        d.download_apk("http://local/apk", filename=d.get_apk_filename(NEW_VERSION))

    # A streamed response only hands its connection back once the body is read or close()
    # runs, so the abandoned ranged response has to be closed or the retry can stall.
    assert [response.closed for response in fake.served] == [True, True]


def test_download_apk_appends_when_the_206_offset_matches(apk_file, download_dir):
    data = apk_bytes(apk_file)
    partial = download_dir / d.get_apk_filename(NEW_VERSION)
    partial.write_bytes(data[:1000])
    fake = _lying_about_the_offset(
        data, f"bytes 1000-{len(data) - 1}/{len(data)}", data[1000:]
    )

    with mock.patch("requests.get", fake):
        path = d.download_apk("http://local/apk", filename=d.get_apk_filename(NEW_VERSION))

    assert len(fake.requested) == 1, "a matching offset must not trigger a restart"
    assert apk_bytes(path) == data


@pytest.mark.parametrize(
    "header,expected",
    [
        ("bytes 1000-1999/2000", 1000),
        ("bytes 0-999/1000", 0),
        ("BYTES 5-9/10", 5),
        ("bytes */2000", None),
        ("bytes 1000", None),
        ("1000-1999/2000", None),
        ("items 1000-1999/2000", None),
        ("bytes\u0663-9/10", None),  # non-ASCII digits are not an offset we asked for
        ("", None),
        (None, None),
    ],
)
def test_resume_offset_only_accepts_a_well_formed_bytes_range(header, expected):
    headers = {} if header is None else {"Content-Range": header}

    assert d._resume_offset(headers) == expected


def test_download_apk_gives_up_on_a_stalled_server(apk_file, download_dir, monkeypatch):
    monkeypatch.setattr(d, "DOWNLOAD_TIMEOUT", (1, 0.5))
    with ReleaseServer(
        version=NEW_VERSION, apk_path=str(apk_file), stall_seconds=3
    ) as stalling:
        (download_dir / d.UPDATE_ENDPOINT_FILENAME).write_text(json.dumps(stalling.endpoint_config()))

        assert d.download_apk(d.get_apk_download_url(NEW_VERSION), filename="stalled.apk") is None


def test_download_apk_reports_a_404_rather_than_raising(pointed_at, download_dir):
    assert d.download_apk(f"{pointed_at.base_url}/v{NEW_VERSION}/nope.apk", filename="nope.apk") is None


def test_apk_is_valid_accepts_the_served_size(pointed_at, download_dir):
    target = download_dir / d.get_apk_filename(NEW_VERSION)
    d.download_apk(d.get_apk_download_url(NEW_VERSION), filename=d.get_apk_filename(NEW_VERSION))

    assert d.apk_is_valid(str(target), pointed_at.apk_size) == str(target)
    assert d.apk_is_valid(str(target), pointed_at.apk_size + 1) is None
    assert d.apk_is_valid(str(download_dir / "absent.apk"), pointed_at.apk_size) is None


def test_apk_size_is_read_from_the_assets_list(pointed_at):
    assert d.get_apk_size(pointed_at.latest_release_json()) == pointed_at.apk_size
    assert d.get_apk_size({"assets": []}) == 0


class _FakeExtras:
    def __init__(self, values):
        self.values = values

    def getString(self, key, default=None):
        return self.values.get(key, default)

    def getLong(self, key, default=0):
        return self.values.get(key, default)

    def getInt(self, key, default=0):
        return self.values.get(key, default)


class _FakeIntent:
    def __init__(self, values):
        self.extras = _FakeExtras(values)
        self.replaced_with = "never called"

    def getExtras(self):
        return self.extras

    def replaceExtras(self, value):
        self.replaced_with = value


class _FakeScreen:
    def __init__(self):
        self.shown = None
        self.downloads = 0
        self.installs = 0

    def show(self, **kwargs):
        self.shown = kwargs

    def start_download(self):
        self.downloads += 1

    def start_install(self):
        self.installs += 1


class _FakeApp:
    def __init__(self, screen):
        self.sm = type("_Sm", (), {"download_apk_screen": screen})()


@pytest.fixture
def update_checker():
    """Reload utils.update_checker with on_android_platform() forced true."""
    import importlib

    import utils.update_checker as uc

    with mock.patch("android_notify.config.on_android_platform", return_value=True):
        importlib.reload(uc)
    yield uc
    with mock.patch("android_notify.config.on_android_platform", return_value=False):
        importlib.reload(uc)


def _handle(uc, values):
    screen = _FakeScreen()
    intent = _FakeIntent(values)
    with mock.patch("kivy.clock.Clock.schedule_once", side_effect=lambda cb, t=0: cb(t)):
        uc.handle_update_intent(_FakeApp(screen), intent=intent)
    return screen, intent


def test_open_update_intent_navigates_with_the_size_from_java(update_checker):
    screen, intent = _handle(
        update_checker,
        {"action": "open_update", "version": NEW_VERSION, "release_notes": "notes", "apk_size": 4096},
    )

    assert screen.shown == {
        "new_version": NEW_VERSION,
        "release_notes": "notes",
        "apk_size": 4096,
    }
    assert intent.replaced_with is None
    assert screen.downloads == 0


def test_open_update_intent_accepts_an_int_apk_size(update_checker):
    screen, _ = _handle(update_checker, {"action": "open_update", "version": NEW_VERSION, "apk_size": 4096})
    assert screen.shown["apk_size"] == 4096


def test_open_update_without_a_size_falls_back_to_zero(update_checker):
    screen, _ = _handle(update_checker, {"action": "open_update", "version": NEW_VERSION})
    assert screen.shown["apk_size"] == 0


def test_open_update_falls_back_to_a_placeholder_note(update_checker):
    screen, _ = _handle(update_checker, {"action": "open_update", "version": NEW_VERSION})
    assert screen.shown["release_notes"] == f"Version {NEW_VERSION} is available."


def test_download_update_intent_also_starts_the_download(update_checker):
    screen, _ = _handle(update_checker, {"action": "download_update", "version": NEW_VERSION})
    assert screen.downloads == 1
    assert screen.installs == 0


def test_install_update_intent_fires_the_installer(update_checker):
    screen, _ = _handle(update_checker, {"action": "install_update", "version": NEW_VERSION})
    assert screen.installs == 1
    assert screen.downloads == 0


def test_an_unrelated_intent_is_ignored(update_checker):
    screen, intent = _handle(update_checker, {"action": "open_update_share", "version": NEW_VERSION})
    assert screen.shown is None
    assert intent.replaced_with == "never called"


def test_the_java_side_reads_the_same_endpoint_file_the_python_side_writes(pointed_at, download_dir):
    """The two resolvers must agree, or Java and Python check different releases."""
    payload = (download_dir / d.UPDATE_ENDPOINT_FILENAME).read_text()
    served = json.loads(payload)
    assert served == {"api_url": pointed_at.api_url, "base_url": pointed_at.base_url}
    assert d.get_release_api_url().startswith("http://127.0.0.1:")
    assert d.get_release_base_url().startswith("http://127.0.0.1:")