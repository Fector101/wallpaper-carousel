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
import sys
import types
from unittest import mock

import pytest

import image_samples
from utils import image_operations as io
from utils.image_operations import is_loadable_image

_png_bytes = image_samples.png_bytes


@pytest.fixture
def good_png(tmp_path):
    return image_samples.write_png(tmp_path / "good.png")


@pytest.fixture
def truncated_png(tmp_path):
    """A PNG cut off after 20 bytes: the 8-byte magic number is intact.

    This is the case a size check and a magic-byte check both wave through, which is
    why it gets its own fixture. Kept as a Path so the assertions below can inspect
    the bytes.
    """
    path = tmp_path / "truncated.png"
    image_samples.write_truncated_png(path)
    return path


@pytest.fixture
def garbage_png(tmp_path):
    return image_samples.write_garbage(tmp_path / "garbage.png")


@pytest.fixture
def empty_png(tmp_path):
    return image_samples.write_empty(tmp_path / "empty.png")


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


# --- the four call sites -----------------------------------------------------------
#
# Each of these hands a path to ``kivy.loader.Loader.image``. The loader does not raise
# for a file it cannot read, it fails later on a Clock callback, so the guard has to be
# *before* the call. These assert the loader is never reached with an unreadable path,
# because that is the only place the failure can still be stopped.


def _stub_loader(monkeypatch):
    """A ``kivy.loader.Loader`` whose ``image`` raises if anything calls it.

    A silent stub would let a regression look like a pass: the load is skipped, the
    assertions below are still true, and the app crashes in the field instead.
    """
    loader = mock.MagicMock()
    loader.image.side_effect = AssertionError("Loader.image reached with an unreadable path")
    loader_module = types.ModuleType("kivy.loader")
    loader_module.Loader = loader
    monkeypatch.setitem(sys.modules, "kivy.loader", loader_module)
    return loader


def _unreadable_paths(tmp_path):
    """One path per way a file can be present but unreadable."""
    return image_samples.write_broken_variants(tmp_path)


def test_the_gallery_placeholder_never_hands_the_loader_a_broken_file(monkeypatch, tmp_path):
    from ui.screens.gallery_screen import LowResDisplayerWithLoader

    _stub_loader(monkeypatch)

    widget = LowResDisplayerWithLoader.__new__(LowResDisplayerWithLoader)
    widget.proxy = None

    for label, path in _unreadable_paths(tmp_path).items():
        widget.low_res_abs_path = path
        widget.load_low_res_image()

        assert widget.proxy is None, f"{label} was accepted"


def test_the_gallery_placeholder_still_loads_a_good_file(monkeypatch, tmp_path):
    """The guard has to reject only what is broken, or the gallery goes blank."""
    from ui.screens.gallery_screen import LowResDisplayerWithLoader

    proxy = mock.MagicMock()
    proxy.loaded = False
    loader = mock.MagicMock()
    loader.image.return_value = proxy
    loader_module = types.ModuleType("kivy.loader")
    loader_module.Loader = loader
    monkeypatch.setitem(sys.modules, "kivy.loader", loader_module)

    widget = LowResDisplayerWithLoader.__new__(LowResDisplayerWithLoader)
    widget.proxy = None
    widget.low_res_abs_path = image_samples.write_png(tmp_path / "good.png")

    widget.load_low_res_image()

    loader.image.assert_called_once_with(widget.low_res_abs_path)
    assert widget.proxy is proxy


def test_the_settings_preview_never_hands_the_loader_a_broken_file(monkeypatch, tmp_path):
    from ui.screens.settings_screen import ScaledLoaderImage

    _stub_loader(monkeypatch)

    widget = ScaledLoaderImage.__new__(ScaledLoaderImage)
    widget.proxy = None

    for label, path in _unreadable_paths(tmp_path).items():
        widget.high_res_abs_path = path
        widget.load_scaled_image()

        assert widget.proxy is None, f"{label} was accepted"


def test_the_settings_preview_rejects_a_broken_scaled_down_cache_entry(monkeypatch, tmp_path):
    """A stale scaled-down file can be truncated even when the original is fine.

    ``get_or_create_scaled_down_image`` only returns the cache path when it already
    exists, so the cached copy is what reaches the loader and it gets the same check.
    """
    from ui.screens import settings_screen as settings_module

    good = image_samples.write_png(tmp_path / "original.png")
    broken_cache = image_samples.write_truncated_png(tmp_path / "scaled.png")

    monkeypatch.setattr(
        settings_module,
        "get_or_create_scaled_down_image",
        lambda src, size: broken_cache,
    )
    _stub_loader(monkeypatch)

    widget = settings_module.ScaledLoaderImage.__new__(settings_module.ScaledLoaderImage)
    widget.proxy = None
    widget.high_res_abs_path = good

    widget.load_scaled_image()

    assert widget.proxy is None


def test_the_preview_screen_never_hands_the_loader_a_broken_file(monkeypatch, tmp_path):
    """The preview screen had no guard at all, not even the ``os.path.exists`` one."""
    from ui.screens import preview_screen as preview_module

    _stub_loader(monkeypatch)

    screen = preview_module.PreviewScreen.__new__(preview_module.PreviewScreen)
    screen.proxy = None
    screen.image_widget = mock.MagicMock()
    screen.high_res_badge = mock.MagicMock()
    screen.how_to_modal = None

    for label, path in _unreadable_paths(tmp_path).items():
        screen.abs_img_path = path

        assert screen.format_widget() is None
        assert screen.proxy is None, f"{label} was accepted"


def test_the_preview_screen_leaves_nothing_behind_when_it_bails(monkeypatch, tmp_path):
    """The sharp texture is missing forever, so nothing may be left spinning.

    The badge comes down and the image stays hidden: a preview showing the blurry
    version with a spinner that never resolves would be worse than the blur alone.
    """
    from ui.screens import preview_screen as preview_module

    _stub_loader(monkeypatch)

    screen = preview_module.PreviewScreen.__new__(preview_module.PreviewScreen)
    screen.proxy = None
    screen.image_widget = mock.MagicMock()
    screen.high_res_badge = mock.MagicMock()
    screen.how_to_modal = None
    screen.abs_img_path = image_samples.write_truncated_png(tmp_path / "truncated.png")

    screen.format_widget()

    screen.high_res_badge.hide.assert_called()
    assert screen.image_widget.opacity == 0


def test_the_fullscreen_carousel_never_hands_the_loader_a_broken_file(monkeypatch, tmp_path):
    from ui.screens.full_screen import FullscreenScreen

    _stub_loader(monkeypatch)

    class _Slide:
        def __init__(self, path):
            self.higher_format = path
            self.texture = None

    class _Carousel:
        size = (100, 200)

        def __init__(self, slide):
            self.slides = [slide]
            self.index = 0

        @property
        def current_slide(self):
            return self.slides[0]

    fs = FullscreenScreen.__new__(FullscreenScreen)
    fs.high_res_proxy = None
    fs.high_res_on_load = None
    fs.proxy = None

    for label, path in _unreadable_paths(tmp_path).items():
        slide = _Slide(path)
        fs.carousel = _Carousel(slide)
        fs._load_high_res(slide)

        assert fs.high_res_proxy is None, f"{label} was accepted"


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
