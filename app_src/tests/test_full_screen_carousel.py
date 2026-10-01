from unittest import mock

from ui.screens import full_screen as fs_module
from ui.screens.full_screen import FullscreenScreen
from utils import image_operations as io


class _FakeSlide:
    def __init__(self, path="", source=""):
        self.higher_format = path
        self.source = source
        self.texture = None


class _FakeImage:
    def __init__(self, **kwargs):
        self.source = kwargs.get("source")
        self.fit_mode = kwargs.get("fit_mode")
        self.higher_format = kwargs.get("higher_format")
        self.texture = None


class _FakeCarousel:
    def __init__(self, n_slides=3):
        self.slides = [_FakeSlide() for _ in range(n_slides)]
        self.index = 0
        self.size = (100, 200)

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
    assert slides[1].higher_format == wallpapers[1]
    assert slides[2].higher_format == wallpapers[2]
    assert fs.current_image == wallpapers[1]


class _FakeProxy:
    def __init__(self, image=None, loaded=False):
        self.image = image
        self.loaded = loaded
        self.on_load_callbacks = []

    def bind(self, **kwargs):
        self.on_load_callbacks.append(kwargs["on_load"])


class _FakeImageLoader:
    def __init__(self, texture=None):
        self.texture = texture


def _patch_loader(monkeypatch, proxies):
    """Hand out pre-built proxies from a fake kivy.loader.Loader.

    An empty ``proxies`` map makes any ``Loader.image`` call fail loudly, which is
    how the "already loaded, nothing to do" test proves it skips the loader.
    """
    import sys
    import types

    def image(path, **_kwargs):
        if path not in proxies:
            raise AssertionError(f"Loader.image unexpectedly called for {path}")
        return proxies[path]

    loader_module = types.ModuleType("kivy.loader")
    loader_module.Loader = types.SimpleNamespace(image=image)
    monkeypatch.setitem(sys.modules, "kivy.loader", loader_module)


def _high_res_screen(**attrs):
    """A screen that keeps the real _load_high_res/_apply_high_res."""
    fs = _bare_screen(**attrs)
    fs._load_high_res = FullscreenScreen._load_high_res.__get__(fs)
    fs._apply_high_res = FullscreenScreen._apply_high_res.__get__(fs)
    return fs


class _CountingSlide(_FakeSlide):
    """A slide that records how often its texture is written."""

    def __init__(self, path="", source=""):
        self._texture = None
        self.texture_writes = 0
        super().__init__(path=path, source=source)

    @property
    def texture(self):
        return self._texture

    @texture.setter
    def texture(self, value):
        self.texture_writes += 1
        self._texture = value


def test_apply_high_res_sets_texture_and_leaves_source_alone():
    fs = _high_res_screen()
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    slide.source = "thumb/w0"
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))

    fs._apply_high_res(proxy, slide, "w0")

    assert slide.texture == "tex"
    # the slide keeps pointing at the thumbnail: rendering follows the texture
    assert slide.source == "thumb/w0"


def test_apply_high_res_skips_slide_user_swiped_past():
    fs = _high_res_screen()
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    fs.carousel.index = 1
    fs.carousel.slides[1].higher_format = "w1"
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))

    fs._apply_high_res(proxy, slide, "w0")

    assert slide.texture is None
    assert slide.source == ""


def test_apply_high_res_without_current_slide_does_not_raise():
    fs = _high_res_screen()
    fs.carousel = _FakeCarousel(n_slides=0)
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))

    fs._apply_high_res(proxy, _FakeSlide(path="w0"), "w0")


def test_apply_high_res_without_texture_leaves_slide_untouched():
    fs = _high_res_screen()
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    proxy = _FakeProxy(image=_FakeImageLoader(texture=None))

    fs._apply_high_res(proxy, slide, "w0")

    assert slide.texture is None
    assert slide.source == ""


def test_apply_high_res_skips_when_slide_already_has_that_texture():
    fs = _high_res_screen()
    slide = _CountingSlide()
    slide.higher_format = "w0"
    slide.texture = "tex"
    writes_before = slide.texture_writes
    fs.carousel.index = 0
    fs.carousel.slides[0] = slide
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))

    fs._apply_high_res(proxy, slide, "w0")

    assert slide.texture_writes == writes_before


def test_apply_high_res_replaces_a_texture_from_another_wallpaper():
    fs = _high_res_screen()
    slide = _CountingSlide()
    slide.higher_format = "w1"
    slide.texture = "tex_of_w0"
    fs.carousel.index = 0
    fs.carousel.slides[0] = slide
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex_of_w1"))

    fs._apply_high_res(proxy, slide, "w1")

    assert slide.texture == "tex_of_w1"


def test_load_high_res_applies_immediately_when_proxy_already_loaded(monkeypatch):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", lambda src, size: f"scaled/{src}")
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=True)
    _patch_loader(monkeypatch, {"scaled/w0": proxy})

    fs._load_high_res(slide)

    assert slide.texture == "tex"
    assert slide.source == ""


def test_load_high_res_defers_to_on_load_when_not_loaded(monkeypatch):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", lambda src, size: f"scaled/{src}")
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {"scaled/w0": proxy})

    fs._load_high_res(slide)
    assert slide.texture is None

    proxy.loaded = True
    proxy.on_load_callbacks[0](proxy)
    assert slide.texture == "tex"


def test_load_high_res_ignores_load_that_finished_after_swiping(monkeypatch):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", lambda src, size: f"scaled/{src}")
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {"scaled/w0": proxy})

    fs._load_high_res(slide)
    # user swipes on while the load is still in flight
    fs.carousel.index = 1
    fs.carousel.slides[1].higher_format = "w1"
    proxy.on_load_callbacks[0](proxy)

    assert slide.texture is None


def test_load_high_res_keeps_high_res_texture_when_swiping_back(monkeypatch):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", lambda src, size: f"scaled/{src}")
    slide = _CountingSlide()
    slide.higher_format = "w0"
    fs.carousel.index = 0
    fs.carousel.slides[0] = slide
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=True)
    _patch_loader(monkeypatch, {"scaled/w0": proxy})

    fs._load_high_res(slide)
    writes_after_first = slide.texture_writes
    # swiping away sets the neighbour's source back to the thumbnail path
    slide.source = "thumb/w0"
    # swiping back loads the same image again
    fs._load_high_res(slide)

    assert slide.texture == "tex"
    assert slide.texture_writes == writes_after_first


def test_apply_high_res_keeps_existing_texture_when_proxy_has_none():
    fs = _high_res_screen()
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    slide.texture = "tex"
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture=None))

    fs._apply_high_res(proxy, slide, "w0")

    assert slide.texture == "tex"
