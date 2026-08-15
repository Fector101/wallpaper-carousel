import time as _time

_BOOT_START = _time.perf_counter()
_BOOT_LAST = _BOOT_START


def boot_log(tag):
    global _BOOT_LAST
    now = _time.perf_counter()
    dt = now - _BOOT_LAST
    _BOOT_LAST = now
    print(f"[BOOT] {tag}: +{dt:.3f}s (total {now - _BOOT_START:.3f}s)")
