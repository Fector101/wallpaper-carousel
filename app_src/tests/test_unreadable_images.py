"""Unreadable-image handling at the four ``Loader.image`` call sites.

``kivy.loader.Loader.image`` is asynchronous and does **not** raise for a file it
cannot read: it returns a ``ProxyImage`` with ``loaded=False`` and the decode happens
on a worker thread. When that decode fails, ``ImageLoader.load`` returns ``None``, the
``None`` is queued in the loader's ``_q_done``, and Kivy's own ``_update`` dereferences
it from a ``Clock`` callback::

    File "kivy/loader.py", line 445, in _update
        if not image.nocache:
    AttributeError: 'NoneType' object has no attribute 'nocache'

That is on the Clock thread, so nothing in the calling widget can catch it, and on
Android it kills the process. ``on_error`` is no help: it is dispatched only from
``_load_urllib``, the remote branch, so a bad *local* file never fires it.

So the check has to happen before the loader is handed the path. These pin that.
"""

import builtins
import struct
import zlib

import pytest

from utils import image_operations as io
from utils.image_operations import is_loadable_image


def _png_bytes(width=4, height=4):
    """A complete, decodable 1-frame PNG."""

    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    idat = chunk(b"IDAT", zlib.compress(raw))
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + chunk(b"IEND", b"")


@pytest.fixture
def good_png(tmp_path):
    path = tmp_path / "good.png"
    path.write_bytes(_png_bytes())
    return path


@pytest.fixture
def truncated_png(tmp_path, good_png):
    """A PNG cut off after 20 bytes: the 8-byte magic number is intact.

    This is the case a size check and a magic-byte check both wave through, which is
    why it gets its own fixture.
    """
    path = tmp_path / "truncated.png"
    path.write_bytes(good_png.read_bytes()[:20])
    return path


@pytest.fixture
def garbage_png(tmp_path):
    path = tmp_path / "garbage.png"
    path.write_bytes(b"this is definitely not a png")
    return path


@pytest.fixture
def empty_png(tmp_path):
    path = tmp_path / "empty.png"
    path.write_bytes(b"")
    return path


def test_a_complete_png_is_loadable(good_png):
    assert is_loadable_image(str(good_png)) is True


def test_a_missing_path_is_not_loadable(tmp_path):
    assert is_loadable_image(str(tmp_path / "never_existed.png")) is False


def test_a_zero_byte_file_is_not_loadable(empty_png):
    assert is_loadable_image(str(empty_png)) is False


def test_garbage_bytes_are_not_loadable(garbage_png):
    assert is_loadable_image(str(garbage_png)) is False


def test_a_truncated_png_is_not_loadable(truncated_png):
    """The load-bearing case.

    The file exists and starts with the PNG signature, so ``os.path.exists`` and a
    magic-byte sniff both accept it. Only parsing the header catches it.
    """
    assert truncated_png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(truncated_png.read_bytes()) > 0
    assert is_loadable_image(str(truncated_png)) is False


def test_no_path_is_not_loadable():
    assert is_loadable_image(None) is False


def test_an_empty_string_is_not_loadable():
    assert is_loadable_image("") is False


def test_the_guard_costs_a_header_read_not_a_full_decode(tmp_path, monkeypatch):
    """It runs on the UI thread, so it must not decode the whole image.

    Pillow's ``Image.open`` is lazy and only parses the header; ``load()`` is the
    expensive part. This fails if someone "simplifies" it into a full decode, which
    measured ~69 ms for an 838 KB wallpaper.
    """
    from PIL import Image

    path = tmp_path / "probe.png"
    path.write_bytes(_png_bytes(width=64, height=64))

    def explode(*_args, **_kwargs):
        raise AssertionError("is_loadable_image decoded the image body")

    monkeypatch.setattr(Image.Image, "load", explode)
    assert is_loadable_image(str(path)) is True


def test_the_android_branch_asks_only_for_the_bounds(tmp_path, monkeypatch):
    """On Android the check is ``inJustDecodeBounds``, so no pixels are decoded."""
    path = tmp_path / "bounds.png"
    path.write_bytes(_png_bytes())

    class FakeOptions:
        def __init__(self):
            self.inJustDecodeBounds = None
            self.outWidth = -1
            self.outHeight = -1

    class FakeBitmapFactory:
        def __init__(self):
            self.calls = []

        def decodeFile(self, path_, options):
            self.calls.append(options.inJustDecodeBounds)
            if options.inJustDecodeBounds:
                options.outWidth, options.outHeight = 4, 4
                return None
            raise AssertionError("is_loadable_image decoded pixels on Android")

    # raising=False: these lazy classes are only created when the module is
    # imported on a real device, so they are absent in the test environment.
    monkeypatch.setattr(io, "_on_android_platform", lambda: True)
    monkeypatch.setattr(io, "Options", FakeOptions, raising=False)
    factory = FakeBitmapFactory()
    monkeypatch.setattr(io, "BitmapFactory", factory, raising=False)

    assert is_loadable_image(str(path)) is True
    assert factory.calls == [True]


def test_the_android_branch_rejects_an_undecodable_header(tmp_path, monkeypatch):
    """Android leaves outWidth/outHeight at -1 when the header will not parse."""
    path = tmp_path / "bad_header.png"
    path.write_bytes(b"nonsense")

    class FakeOptions:
        def __init__(self):
            self.inJustDecodeBounds = None
            self.outWidth = -1
            self.outHeight = -1

    class FakeBitmapFactory:
        @staticmethod
        def decodeFile(path_, options):
            return None  # outWidth stays -1, exactly as Android reports it

    monkeypatch.setattr(io, "_on_android_platform", lambda: True)
    monkeypatch.setattr(io, "Options", FakeOptions, raising=False)
    monkeypatch.setattr(io, "BitmapFactory", FakeBitmapFactory, raising=False)

    assert is_loadable_image(str(path)) is False


def test_without_pillow_it_falls_back_to_a_size_check(tmp_path, monkeypatch):
    """Better to accept a corrupt file than to reject a good one.

    With no Pillow we cannot see corruption, but we must not start blanking real
    wallpapers on a machine where the import fails.
    """
    good = tmp_path / "fine.png"
    good.write_bytes(_png_bytes())
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")

    real_import = builtins.__import__

    def no_pil(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("no Pillow here")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pil)

    assert is_loadable_image(str(good)) is True
    assert is_loadable_image(str(empty)) is False
    assert is_loadable_image(str(tmp_path / "gone.png")) is False
