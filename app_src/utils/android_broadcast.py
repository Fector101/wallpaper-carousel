"""p4a's BroadcastReceiver with the Android 14+ receiver-export flag.

p4a's `android.broadcast.BroadcastReceiver` (still unfixed on p4a master) registers with
`Context.registerReceiver(receiver, filter, None, handler)`, i.e. implicit `flags = 0`.
Apps targeting API 34+ that register a receiver for non-system broadcasts must pass
RECEIVER_EXPORTED / RECEIVER_NOT_EXPORTED, otherwise the platform throws
    java.lang.SecurityException: One of RECEIVER_EXPORTED or RECEIVER_NOT_EXPORTED should
    be specified when a receiver isn't being registered exclusively for system broadcasts
and the service that registered it dies right there (wallpaper.py `br.start()`).

Only `start()` differs from p4a's class; `__init__`, `stop()` and `context` are inherited.
"""

from android.broadcast import BroadcastReceiver as _P4ABroadcastReceiver
from android_notify.config import on_android_platform

if on_android_platform():
    from android_notify.internal.java_classes import autoclass, BuildVersion

    # Module level: autoclass is expensive the first time a class is resolved and cheap
    # afterwards, and `Context.RECEIVER_NOT_EXPORTED` must NOT be read at import time
    # (the field only exists on API 33+, minSdk here is 24).
    _Context = autoclass('android.content.Context')
    _Handler = autoclass('android.os.Handler')
    _HandlerThread = autoclass('android.os.HandlerThread')


class BroadcastReceiver(_P4ABroadcastReceiver):
    """p4a's receiver, but registered with RECEIVER_NOT_EXPORTED on API 33+."""

    def start(self):
        if hasattr(self, 'handlerthread') and self.handlerthread.isAlive():
            return
        self.handlerthread = _HandlerThread('handlerthread')
        self.handlerthread.start()
        if self._is_registered:
            return
        self.handler = _Handler(self.handlerthread.getLooper())
        if BuildVersion.SDK_INT >= 33:
            # Our actions (`<pkg>.ACTION_STOP`/`ACTION_SKIP`) are not system broadcasts,
            # so U+ enforces the export flag. They are only ever sent by this app's own
            # notification PendingIntents -> NOT_EXPORTED, and the sender's own UID is
            # always allowed to reach a NOT_EXPORTED receiver.
            self.context.registerReceiver(
                self.receiver, self.receiver_filter, None, self.handler,
                _Context.RECEIVER_NOT_EXPORTED)
        else:
            # Pre-13 has no RECEIVER_* constants and no enforcement: legacy 4-arg call.
            self.context.registerReceiver(
                self.receiver, self.receiver_filter, None, self.handler)
        self._is_registered = True
