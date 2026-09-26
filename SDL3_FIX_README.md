# Fix: Kivy master + SDL3 on Ubuntu 24.04 (desktop)

## Problem

Kivy master (3.0.0.dev0) and KivyMD dev are built around SDL3 (`buildozer.spec`:
`kivy==master` + `p4a.bootstrap=sdl3`). On Ubuntu 24.04 there are **no SDL3
packages**, so building Kivy from the master branch skips the SDL3 backend and
you get at runtime:

```
ImportError: libSDL3.so.0: cannot open shared object file: No such file or directory
```

(before that you'd also see `ModuleNotFoundError: No module named
'kivy.core.window._window_sdl3'`).

## Fix (one-time)

1. Install build tools + SDL3 build deps:

   ```bash
   sudo apt-get update
   sudo apt-get install -y ninja-build meson build-essential autoconf automake libtool \
     cmake curl libasound2-dev libpulse-dev libaudio-dev libjack-dev libsndio-dev \
     libsamplerate0-dev libx11-dev libxext-dev libxrandr-dev libxcursor-dev \
     libxfixes-dev libxi-dev libxss-dev libxkbcommon-dev libxext-dev \
     libdrm-dev libgbm-dev libgl1-mesa-dev libgles2-mesa-dev libegl1-mesa-dev \
     libdbus-1-dev libibus-1.0-dev libudev-dev libxtst-dev
   ```

2. Build SDL3 + SDL3_image/ttf/mixer + libpng + ThorVG using Kivy's own script.
   Use a **persistent** dir (NOT `/tmp`), or a reboot wipes it and the
   compiled extensions break again:

   ```bash
   mkdir -p ~/kivy-sdl3-deps
   cd ~/kivy-sdl3-deps
   bash /path/to/kivy/tools/build_linux_dependencies.sh
   ```

3. Reinstall Kivy so the extensions bake the new library path (`RUNPATH`):

   ```bash
   cd /path/to/kivy   # your kivy checkout
   KIVY_DEPS_ROOT=$HOME/kivy-sdl3-deps/kivy-dependencies \
     venv/bin/pip install -e .
   ```

4. Verify the generated extension links SDL3:

   ```bash
   ldd kivy/core/window/_window_sdl3.cpython-312-x86_64-linux-gnu.so | grep SDL3
   ```

5. Run your app:

   ```bash
   venv/bin/python app_src/main.py
   ```

   Success looks like `[Window] Provider: sdl3`, `[GL] Backend used <sdl3>`.
   If it's been a while since your last clean build, KivyMD also needs
   `kivy.core.window.window_sdl3` loadable on desktop even when you'd rather
   use the X11 backend — so this step is required.

## Gotchas we hit

- **`/tmp` deletes itself on reboot** — the first build went into
  `/tmp/opencode/...` and every extension's `RUNPATH` pointed there; reboot →
  `libSDL3.so.0: cannot open shared object file`. Keep deps in `~/kivy-sdl3-deps`.
- **Network flakiness**: the script's vendored git clones (`SDL3_image/ttf/mixer
  external/download.sh`) time out occasionally. Rerun `./external/download.sh`
  (cleaning leftover `external/` dirs first) and continue the cmake steps from
  the script by hand — no need to retry the whole thing.
- **`libxtst-dev`** is needed or SDL3's cmake configure fails with
  `Couldn't find dependency package for XTEST`.
- `venv/bin/pip` (PEP 517 isolation) is used intentionally; `--no-build-isolation`
  fails because Cython only lives in pip's isolated build env.
- The `joystick`/`gamepad` content under `kivy/tests` gets picked up if you run
  pytest from the repo root and shadows the real `kivy` package — run pytest
  from `app_src/` (`../venv/bin/python -m pytest tests`).

Android is unaffected: p4a builds its own `kivy==master` with the SDL3
bootstrap inside the buildozer toolchain.