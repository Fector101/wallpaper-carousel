"""Real image files for tests that need one.

The screens refuse to hand an unreadable path to ``kivy.loader.Loader``, so a test
that wants to exercise a load has to give it a genuinely decodable file -- writing
``b"not really an image"`` and stubbing the check is how a test ends up passing
because the code did nothing.

Kept as a module (rather than in one test file) so every suite that needs a wallpaper
builds the same bytes.
"""

import struct
import zlib

# Enough bytes of each signature for a magic-byte sniff to be fooled, which is why
# these fixtures exist: a truncated PNG still starts with a valid 8-byte PNG header.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_bytes(width=4, height=4):
    """A complete, decodable, single-frame truecolour PNG."""

    def chunk(kind, payload):
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    scanlines = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return PNG_SIGNATURE + ihdr + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b"")


def write_png(path, width=4, height=4):
    """Write a decodable PNG to ``path`` and return it as a str."""
    path.write_bytes(png_bytes(width=width, height=height))
    return str(path)


def write_truncated_png(path, keep=20):
    """A PNG cut off after ``keep`` bytes -- present, non-empty, correctly signed.

    Rejected by a header parse, accepted by ``os.path.exists`` and by any check that
    only looks at the first few bytes.
    """
    path.write_bytes(png_bytes()[:keep])
    return str(path)


def write_garbage(path):
    """A file with a .png name and nothing usable inside."""
    path.write_bytes(b"this is definitely not a png")
    return str(path)


def write_empty(path):
    path.write_bytes(b"")
    return str(path)


#: Every way a file can be present but unreadable. Each one used to reach
#: ``Loader.image`` and take the app down from a Clock callback.
def write_broken_variants(directory):
    """Write one of each broken file into ``directory``; returns ``{label: path}``."""
    return {
        "missing": str(directory / "never_existed.png"),
        "empty": write_empty(directory / "empty.png"),
        "garbage": write_garbage(directory / "garbage.png"),
        "truncated": write_truncated_png(directory / "truncated.png"),
    }
