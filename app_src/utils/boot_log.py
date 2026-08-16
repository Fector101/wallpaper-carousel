import os
import threading
import time as _time

_BOOT_START = _time.perf_counter()
_BOOT_LAST = _BOOT_START
_lock = threading.Lock()

_ENABLED = os.environ.get("WALLER_BOOT_LOG", "1") == "1"


def boot_log(tag):
    if not _ENABLED:
        return
    global _BOOT_LAST
    now = _time.perf_counter()
    with _lock:
        dt = now - _BOOT_LAST
        _BOOT_LAST = now
    print(f"[BOOT] {tag}: +{dt:.3f}s (total {now - _BOOT_START:.3f}s)")
