from pathlib import Path
from unittest import mock

import image_samples

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
    fs.clock_for_higher_format = None
    fs.high_res_proxy = None
    fs.high_res_on_load = None
    for k, v in attrs.items():
        setattr(fs, k, v)
    return fs


def _patch_carousel_deps(monkeypatch):
    monkeypatch.setattr(fs_module, "MyImage", _FakeImage)
    # on_current_slide uses the module-level import, update_images a local one
    monkeypatch.setattr(io, "thumbnail_path_for", lambda p: str(p))
    monkeypatch.setattr(fs_module, "thumbnail_path_for", lambda p: str(p))


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
        self.unbound_callbacks = []

    def bind(self, **kwargs):
        self.on_load_callbacks.append(kwargs["on_load"])

    def unbind(self, **kwargs):
        callback = kwargs["on_load"]
        self.unbound_callbacks.append(callback)
        if callback in self.on_load_callbacks:
            self.on_load_callbacks.remove(callback)

    @property
    def listener_count(self):
        return len(self.on_load_callbacks)


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


def _wallpaper(tmp_path, name):
    """A wallpaper path that is genuinely decodable.

    ``_load_high_res`` bails out on a path it cannot read (a wallpaper deleted behind
    our back, or one truncated on disk), so a test that wants to exercise the load
    path has to hand it a real file. A bare ``"w0"`` makes the test pass for the
    wrong reason: nothing loads, so nothing can be asserted about the listener.
    """
    return image_samples.write_png(tmp_path / f"{name}.png")


def _wallpapers(tmp_path, count):
    return [_wallpaper(tmp_path, f"w{i}") for i in range(count)]


def _scaled(tmp_path, src):
    """The path a real scaled-down cache entry would have for ``src``.

    ``_load_high_res`` now checks that what ``get_or_create_scaled_down_image``
    returned is readable before it goes near the loader, so a stub returning a
    ``"scaled/w0.png"`` string that was never written makes the test pass for the
    wrong reason: the load is skipped and the assertions are vacuous.
    """
    return str(tmp_path / f"scaled_{Path(src).name}")


def _scaled_stub(tmp_path):
    """``get_or_create_scaled_down_image`` that writes the file it claims to return."""

    def get_or_create(src, size):
        path = tmp_path / f"scaled_{Path(src).name}"
        if not path.exists():
            image_samples.write_png(path)
        return str(path)

    return get_or_create


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


def test_load_high_res_applies_immediately_when_proxy_already_loaded(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = fs.carousel.slides[0]
    slide.higher_format = w0
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=True)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})

    fs._load_high_res(slide)

    assert slide.texture == "tex"
    assert slide.source == ""


def test_load_high_res_defers_to_on_load_when_not_loaded(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = fs.carousel.slides[0]
    slide.higher_format = w0
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})

    fs._load_high_res(slide)
    assert slide.texture is None

    proxy.loaded = True
    proxy.on_load_callbacks[0](proxy)
    assert slide.texture == "tex"


def test_load_high_res_ignores_load_that_finished_after_swiping(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = fs.carousel.slides[0]
    slide.higher_format = w0
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})

    fs._load_high_res(slide)
    # user swipes on while the load is still in flight
    fs.carousel.index = 1
    fs.carousel.slides[1].higher_format = _wallpaper(tmp_path, "w1")
    proxy.on_load_callbacks[0](proxy)

    assert slide.texture is None


def test_load_high_res_keeps_high_res_texture_when_swiping_back(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = _CountingSlide()
    slide.higher_format = w0
    fs.carousel.index = 0
    fs.carousel.slides[0] = slide
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=True)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})

    fs._load_high_res(slide)
    writes_after_first = slide.texture_writes
    # swiping away sets the neighbour's source back to the thumbnail path
    slide.source = f"thumb/{w0}"
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


def test_apply_high_res_skips_a_different_slide_showing_the_requested_path():
    """CodeRabbit #107: the requested path can be on screen on another slide.

    Two wallpapers means the slide on screen and the slide we asked for can end
    up pointing at the same wallpaper, so comparing paths alone is not enough.
    """
    fs = _high_res_screen()
    slides = fs.carousel.slides
    captured = slides[0]
    captured.higher_format = "w1"
    slides[1].higher_format = "w0"
    fs.carousel.index = 1
    slides[1].higher_format = "w1"  # current slide now shows the requested path
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))

    fs._apply_high_res(proxy, captured, "w1")

    assert captured.texture is None


def test_apply_high_res_skips_when_the_slide_moved_on_to_another_wallpaper():
    """Same widget, different wallpaper: the path check has to catch that."""
    fs = _high_res_screen()
    slide = fs.carousel.slides[0]
    slide.higher_format = "w0"
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))
    slide.higher_format = "w1"  # re-pointed while the user stayed put

    fs._apply_high_res(proxy, slide, "w0")

    assert slide.texture is None


def test_apply_high_res_without_a_slide_does_not_raise():
    """No current slide and no captured slide must not read attributes off None."""
    fs = _high_res_screen()
    fs.carousel.index = 3  # out of range, so current_slide is None
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"))

    fs._apply_high_res(proxy, None, "w0")

    assert fs.carousel.current_slide is None


def test_late_load_never_paints_a_slide_that_is_not_current(monkeypatch, tmp_path):
    """A load that finishes after swiping must never touch an off-screen slide.

    Walks the real ``on_current_slide`` over many library sizes and swipe orders
    (Kivy's carousel wraps its index modulo the slide count) and replays every
    request made along the way against the real ``_apply_high_res``.
    """
    import itertools

    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    monkeypatch.setattr(fs_module, "app_logger", mock.MagicMock())  # this rejects thousands of loads
    monkeypatch.setattr(fs_module, "Clock", mock.MagicMock())  # real Clock is slow, we never need the timer
    _patch_carousel_deps(monkeypatch)
    applied = 0

    for size in range(2, 6):
        wallpapers = [f"w{i}" for i in range(size)]
        for start in range(size):
            fs = _bare_screen()
            fs._apply_high_res = FullscreenScreen._apply_high_res.__get__(fs)
            for length in range(size + 2):
                for order in itertools.product("+-", repeat=length):
                    fs.wallpapers_data = wallpapers
                    fs.manager.gallery_screen.wallpapers = wallpapers
                    fs.carousel_index = start
                    fs.update_images(index=start)  # fresh slides for every order

                    requests = [(fs.carousel.current_slide, fs.carousel.current_slide.higher_format)]
                    for swipe in order:
                        index = fs.carousel.index + (1 if swipe == "+" else -1)
                        fs.carousel.index = index % 3  # kivy: _index % len(slides)
                        fs.on_current_slide(fs.carousel, fs.carousel.index)
                        requests.append((fs.carousel.current_slide, fs.carousel.current_slide.higher_format))

                        for slide, path in requests:
                            marker = object()  # unique, so a real paint is visible
                            proxy = _FakeProxy(image=_FakeImageLoader(texture=marker))
                            fs._apply_high_res(proxy, slide, path)
                            if slide is fs.carousel.current_slide:
                                applied += 1
                            else:
                                assert slide.texture is not marker, (
                                    f"stale load painted an off-screen slide "
                                    f"(wallpapers={size}, start={start}, swipes={''.join(order)})"
                                )

    assert applied, "no load was ever accepted, so the loop proved nothing"


def test_load_high_res_stores_one_listener_for_a_cold_proxy(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = fs.carousel.slides[0]
    slide.higher_format = w0
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})

    fs._load_high_res(slide)

    assert proxy.listener_count == 1
    assert fs.high_res_proxy is proxy
    assert fs.high_res_on_load in proxy.on_load_callbacks


def test_load_high_res_binds_nothing_when_already_loaded(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = fs.carousel.slides[0]
    slide.higher_format = w0
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=True)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})

    fs._load_high_res(slide)

    assert slide.texture == "tex"
    assert proxy.listener_count == 0
    assert fs.high_res_proxy is None
    assert fs.high_res_on_load is None


def test_load_high_res_drops_the_previous_listener(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    w1 = _wallpaper(tmp_path, "w1")
    fs.carousel.index = 0
    first = fs.carousel.slides[0]
    first.higher_format = w0
    second = fs.carousel.slides[1]
    second.higher_format = w1
    fs.carousel.index = 1
    stale_proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): stale_proxy, _scaled(tmp_path, w1): stale_proxy})

    fs._load_high_res(first)
    fs._load_high_res(second)

    assert stale_proxy.listener_count == 1
    assert fs.high_res_proxy is stale_proxy


def test_cancel_high_res_unbinds_and_clears(monkeypatch, tmp_path):
    fs = _high_res_screen()
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    w0 = _wallpaper(tmp_path, "w0")
    slide = fs.carousel.slides[0]
    slide.higher_format = w0
    fs.carousel.index = 0
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, w0): proxy})
    clock = mock.MagicMock()
    fs.clock_for_higher_format = clock

    fs._load_high_res(slide)
    fs._cancel_high_res()

    assert clock.cancel.called
    assert proxy.listener_count == 0
    assert proxy.unbound_callbacks
    assert fs.high_res_proxy is None
    assert fs.high_res_on_load is None
    assert fs.clock_for_higher_format is None


def test_cancel_high_res_without_a_pending_load_is_safe():
    fs = _high_res_screen()

    fs._cancel_high_res()

    assert fs.high_res_proxy is None
    assert fs.clock_for_higher_format is None


def test_on_current_slide_unbinds_the_previous_listener(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    wallpapers = _wallpapers(tmp_path, 3)
    fs = _high_res_screen()
    fs.wallpapers_data = wallpapers
    fs.manager.gallery_screen.wallpapers = wallpapers
    fs.carousel_index = 0
    fs.update_images(index=0)
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, p): proxy for p in wallpapers})

    fs._load_high_res(fs.carousel.current_slide)
    assert proxy.listener_count == 1

    fs.carousel.index = 2
    fs.on_current_slide(fs.carousel, 2)

    assert proxy.listener_count == 0
    assert fs.high_res_proxy is None


def test_update_images_unbinds_before_dropping_the_slides(monkeypatch, tmp_path):
    _patch_carousel_deps(monkeypatch)
    monkeypatch.setattr(fs_module, "get_or_create_scaled_down_image", _scaled_stub(tmp_path))
    wallpapers = _wallpapers(tmp_path, 3)
    fs = _high_res_screen()
    fs.wallpapers_data = wallpapers
    fs.manager.gallery_screen.wallpapers = wallpapers
    fs.carousel_index = 0
    fs.update_images(index=0)
    proxy = _FakeProxy(image=_FakeImageLoader(texture="tex"), loaded=False)
    _patch_loader(monkeypatch, {_scaled(tmp_path, p): proxy for p in wallpapers})
    fs._load_high_res(fs.carousel.current_slide)
    dropped = fs.carousel.current_slide
    listeners_when_dropped = []
    clear_widgets = fs.carousel.clear_widgets

    def spy_clear_widgets():
        listeners_when_dropped.append(proxy.listener_count)
        clear_widgets()

    fs.carousel.clear_widgets = spy_clear_widgets

    fs.update_images(index=1)

    assert listeners_when_dropped == [0], "listener was still attached while the slides went away"
    assert proxy.listener_count == 0
    assert fs.high_res_proxy is None
    assert dropped not in fs.carousel.slides
