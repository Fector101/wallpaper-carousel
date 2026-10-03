"""A laptop-hosted stand-in for the GitHub Releases API, so the app-update flow can be
tested without touching the network.

Only the subset the app actually uses is implemented:

- ``GET /repos/<owner>/<repo>/releases/latest`` -> the release JSON shape that
  ``check_update`` reads (``tag_name`` plus ``assets[].name/size/browser_download_url``)
- ``GET /releases/download/v<version>/<asset>`` -> the APK and the ``update-note-v*.txt``

Release assets honour ``Range`` with a ``206`` so ``download_apk``'s resume path can be
exercised for real. ``range_mode`` can force the misbehaving variants that a live server
may also produce ("ignore" answers ``200`` to a range request, "reject" answers ``416``).

Used two ways:

- in-process by ``test_release_download_local.py``
- as a CLI by ``update_download_e2e.py`` to serve a real APK to a phone over the LAN
"""

import argparse
import errno
import json
import os
import re
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_API_PATH = "/repos/Fector101/wallpaper-carousel/releases/latest"
ASSET_PREFIX = "/releases/download"
DEFAULT_NOTES = "[b]Local test release[/b]\n\n• Served from a laptop, not GitHub\n"
RANGE_RE = re.compile(r"bytes=(\d+)-")


class PortInUseError(RuntimeError):
    """Raised instead of a bare OSError when the port is already taken."""


class ReleaseServer:
    """A fake release host. Call ``start()``, use ``base_url``, then ``stop()``."""

    def __init__(
        self,
        version="1.0.11",
        apk_path=None,
        notes=DEFAULT_NOTES,
        api_path=DEFAULT_API_PATH,
        range_mode="honor",
        stall_seconds=0.0,
        host="127.0.0.1",
        port=0,
    ):
        self.version = version
        self.apk_path = apk_path
        self.notes = notes
        self.api_path = api_path
        self.range_mode = range_mode
        self.stall_seconds = stall_seconds
        self.host = host
        self.port = port

        self.apk_name = f"waller-v{version}.apk"
        self.notes_name = f"update-note-v{version}.txt"
        self.requests = []
        self._httpd = None
        self._thread = None
        self._tmpdir = tempfile.mkdtemp(prefix="local-release-")
        self._notes_path = os.path.join(self._tmpdir, self.notes_name)
        with open(self._notes_path, "w", encoding="utf-8") as f:
            f.write(notes)

    @property
    def apk_size(self):
        return os.path.getsize(self.apk_path) if self.apk_path else 0

    @property
    def base_url(self):
        host = "127.0.0.1" if self.host in ("0.0.0.0", "") else self.host
        return f"http://{host}:{self.port}{ASSET_PREFIX}"

    @property
    def api_url(self):
        return f"http://{'127.0.0.1' if self.host in ('0.0.0.0', '') else self.host}:{self.port}{self.api_path}"

    def endpoint_config(self):
        """The ``update_endpoint.json`` payload that points the app at this server."""
        return {"api_url": self.api_url, "base_url": self.base_url}

    def latest_release_json(self):
        assets = []
        if self.apk_path:
            assets.append(
                {
                    "name": self.apk_name,
                    "size": self.apk_size,
                    "browser_download_url": f"{self.base_url}/v{self.version}/{self.apk_name}",
                }
            )
        if self.notes:
            assets.append(
                {
                    "name": self.notes_name,
                    "size": len(self.notes.encode("utf-8")),
                    "browser_download_url": f"{self.base_url}/v{self.version}/{self.notes_name}",
                }
            )
        return {"tag_name": f"v{self.version}", "name": f"Release v{self.version}", "assets": assets}

    def record(self, path, range_header):
        self.requests.append({"path": path, "range": range_header})

    def paths_requested(self):
        return [r["path"] for r in self.requests]

    def reset_log(self):
        self.requests = []

    def start(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *_args):
                pass

            def do_GET(self):
                if server.stall_seconds:
                    import time

                    time.sleep(server.stall_seconds)
                path = self.path.split("?")[0]
                server.record(path, self.headers.get("Range"))
                if path == server.api_path:
                    return self.send_json(server.latest_release_json())
                if path.startswith(f"{ASSET_PREFIX}/v{server.version}/"):
                    name = path.rsplit("/", 1)[-1]
                    return self.send_asset(server.asset_path(name))
                self.send_error(404, "No such release asset")

            def send_json(self, payload):
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def send_asset(self, asset_path):
                if asset_path is None:
                    return self.send_error(404, "No such release asset")
                size = os.path.getsize(asset_path)
                range_header = self.headers.get("Range")
                start = 0
                if range_header and server.range_mode == "reject":
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if range_header and server.range_mode == "honor":
                    match = RANGE_RE.match(range_header)
                    if match and int(match.group(1)) < size:
                        start = int(match.group(1))
                with open(asset_path, "rb") as f:
                    f.seek(start)
                    body = f.read()
                self.send_response(206 if start else 200)
                self.send_header("Content-Type", "application/vnd.android.package-archive")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(len(body)))
                if start:
                    self.send_header("Content-Range", f"bytes {start}-{size - 1}/{size}")
                self.end_headers()
                self.wfile.write(body)

        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        except OSError as failure:
            if failure.errno != errno.EADDRINUSE:
                raise
            raise PortInUseError(
                f"port {self.port} is already in use, so no fake GitHub could start. "
                f"Another test run is probably still going -- wait for it, or pass --port to use a "
                f"different one."
            ) from failure
        self._httpd.release_server = self
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def __enter__(self):
        return self.start()

    def __exit__(self, *_exc):
        self.stop()

    def asset_path(self, name):
        if name == self.apk_name and self.apk_path:
            return self.apk_path
        if name == self.notes_name:
            return self._notes_path
        return None


def main():
    parser = argparse.ArgumentParser(description="Serve a fake GitHub release to a phone.")
    parser.add_argument("--apk", required=True, help="APK to serve as the new version")
    parser.add_argument("--version", required=True, help="version string, e.g. 1.0.11")
    parser.add_argument("--notes", help="release notes text file")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--range-mode", default="honor", choices=("honor", "ignore", "reject"))
    args = parser.parse_args()

    notes = DEFAULT_NOTES
    if args.notes:
        with open(args.notes, encoding="utf-8") as f:
            notes = f.read()

    server = ReleaseServer(
        version=args.version,
        apk_path=os.path.abspath(args.apk),
        notes=notes,
        range_mode=args.range_mode,
        host=args.host,
        port=args.port,
    )
    server.start()
    print(f"serving v{args.version} on {server.base_url}")
    print(f"  api  {server.api_url}")
    print(f"  apk  {server.base_url}/v{args.version}/{server.apk_name} ({server.apk_size} bytes)")
    print("ctrl-c to stop")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()