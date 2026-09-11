from unittest import mock

from ui.screens import full_screen as fs_module
from ui.screens.full_screen import FullscreenScreen
from utils import image_operations as io


class _FakeSlide:
    def __init__(self, path="", source=""):
        self.higher_format = path
        self.source = source
        self._high_res_loaded = False


class _FakeImage:
    def __init__(self, **kwargs):
        self.source = kwargs.get("source")
        self.fit_mode = kwargs.get("fit_mode")
        self.higher_format = kwargs.get("higher_format")
        self._high_res_loaded = False


class _FakeCarousel:
    def __init__(self, n_slides=3):
        self.slides = [_FakeSlide() for _ in range(n_slides)]
        self.index = 0

    def clear_widgets(self):
        self.slides.clear()

    def add_widget(self, widget):
        self.slides.append(widget)

    def unbind(self, **kwargs):
        pass

    def bind(self, **kwargs):
        pass

    @property
    def current_slide(self):
        if 0 <= self.index < len(self.slides):
            return self.slides[self.index]
        return None


def _bare_screen(**attrs):
    fs = FullscreenScreen.__new__(FullscreenScreen)
    fs.wallpapers_data = []
    fs.carousel_index = None
    fs.clock_for_higher_format = None
    fs.manager = mock.MagicMock()
    fs.manager.gallery_screen.wallpapers = []
    fs.carousel = _FakeCarousel()
    fs.build_ui = mock.MagicMock()
    fs.update_header_texts = mock.MagicMock()
    fs._load_high_res = mock.MagicMock()
    for k, v in attrs.items():
        setattr(fs, k, v)
    return fs


def _patch_carousel_deps(monkeypatch):
    monkeypatch.setattr(fs_module, "MyImage", _FakeImage)
    monkeypatch.setattr(io, "thumbnail_path_for", lambda p: str(p))


def test_get_index_center():
    fs = _bare_screen()
    fs.carousel.index = 1
    assert fs.get_index("left") == 0
    assert fs.get_index("right") == 2


def test_get_index_left_edge_wraps_to_last_slide():
    fs = _bare_screen()
    fs.carousel.index = 0
    assert fs.get_index("left") == -1
    assert fs.get_index("right") == 1


def test_get_index_right_edge_wraps_to_first_slide():
    fs = _bare_screen()
    fs.carousel.index = 2
    assert fs.get_index("left") == 1
    assert fs.get_index("right") == 0


def test_get_scroll_data_middle():
    fs = _bare_screen()
    fs.wallpapers_data = ["w0", "w1", "w2", "w3", "w4"]
    data = fs._get_scroll_data("w2")
    assert data == {"left": "w1", "center": "w2", "right": "w3"}
    assert fs.carousel_index == 2


def test_get_scroll_data_wraps_left_from_first():
    fs = _bare_screen()
    fs.wallpapers_data = ["w0", "w1", "w2"]
    data = fs._get_scroll_data("w0")
    assert data == {"left": "w2", "center": "w0", "right": "w1"}
    assert fs.carousel_index == 0


def test_get_scroll_data_wraps_right_from_last():
    fs = _bare_screen()
    fs.wallpapers_data = ["w0", "w1", "w2"]
    data = fs._get_scroll_data("w2")
    assert data == {"left": "w1", "center": "w2", "right": "w0"}
    assert fs.carousel_index == 2


def test_get_scroll_data_single_wallpaper():
    fs = _bare_screen()
    fs.wallpapers_data = ["only"]
    data = fs._get_scroll_data("only")
    assert data == {"left": "only", "center": "only", "right": "only"}
    assert fs.carousel_index == 0


def test_update_images_clamps_index_above_last(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    wallpapers = [str(tmp_path / f"w{i}.png") for i in range(3)]
    fs = _bare_screen()
    fs.manager.gallery_screen.wallpapers = wallpapers

    fs.update_images(index=5)

    assert fs.carousel_index == 2
    assert fs.carousel.index == 1
    assert len(fs.carousel.slides) == 3
    assert fs.build_ui.called


def test_update_images_clamps_index_below_zero(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    wallpapers = [str(tmp_path / f"w{i}.png") for i in range(3)]
    fs = _bare_screen()
    fs.manager.gallery_screen.wallpapers = wallpapers

    fs.update_images(index=-5)

    assert fs.carousel_index == 0
    assert fs.carousel.index == 1
    assert fs.build_ui.called


def test_update_images_empty_wallpapers_returns_early(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    fs = _bare_screen()
    fs.manager.gallery_screen.wallpapers = []

    fs.update_images(index=0)

    assert not fs.build_ui.called


def test_update_images_without_index_returns_early(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    fs = _bare_screen()
    fs.manager.gallery_screen.wallpapers = [str(tmp_path / "w0.png")]

    fs.update_images()

    assert not fs.build_ui.called


def test_on_current_slide_returns_without_images():
    fs = _bare_screen(carousel_has_images=False)
    result = fs.on_current_slide(fs.carousel, 1)
    assert result is None
    assert all(s.source == "" for s in fs.carousel.slides)


def test_on_current_slide_returns_without_current_slide():
    fs = _bare_screen(carousel_has_images=True)
    fs.carousel = _FakeCarousel(n_slides=0)
    assert fs.on_current_slide(fs.carousel, 1) is None


def test_on_current_slide_updates_neighbors(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    wallpapers = [str(tmp_path / f"w{i}.png") for i in range(3)]
    fs = _bare_screen()
    fs.manager.gallery_screen.wallpapers = wallpapers

    fs.update_images(index=1)

    slides = fs.carousel.slides
    assert slides[0].higher_format == wallpapers[0]
    assert slides[0]._high_res_loaded is False
    assert slides[1].higher_format == wallpapers[1]
    assert slides[2].higher_format == wallpapers[2]
    assert fs.current_image == wallpapers[1]