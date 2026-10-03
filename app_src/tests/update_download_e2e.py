#!/usr/bin/env python3
"""Device end-to-end test for the new-release download flow.

Serves a fake release from this laptop and makes the phone download it, then checks the
bytes that landed on the device against the bytes that were served. No GitHub, no PyPI.

    # 1. build a debug APK whose versionCode is above the installed one
    venv/bin/python app_src/tests/update_download_e2e.py --build-new-apk --install

    # 2. run it again against the APK that is already built
    venv/bin/python app_src/tests/update_download_e2e.py

Requires a debug build: the app is debug-signed, so an APK signed with
``my-release-key.jks`` cannot update it (``INSTALL_FAILED_UPDATE_INCOMPATIBLE``).
Cleartext HTTP must be enabled first -- see the "Local release server" section of
app_src/android/DEV.md.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from io import BytesIO

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from local_release_server import PortInUseError, ReleaseServer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PACKAGE = "org.wally.waller"
ACTIVITY = f"{PACKAGE}/org.kivy.android.PythonActivity"
APP_FILES_DIR = f"/data/user/0/{PACKAGE}/files"
DEFAULT_ADB = os.path.expanduser(
    "~/.buildozer/android/platform/android-sdk/platform-tools/adb"
)
BUILD_TOOLS_GLOB = os.path.expanduser("~/.buildozer/android/platform/android-sdk/build-tools")
ENDPOINT_FILE = "update_endpoint.json"
OK, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"


class E2EFailure(Exception):
    pass


def step(message):
    print(f"\n\033[1m==> {message}\033[0m", flush=True)


def check(label, condition, detail=""):
    if condition:
        print(f"  [{OK}] {label}", flush=True)
        return True
    print(f"  [{FAIL}] {label}", flush=True)
    raise E2EFailure(f"{label}{' -- ' + detail if detail else ''}")


def newest_source_mtime(apk):
    """Newest app source file, if it is newer than the APK, so we can warn about a stale serve."""
    source_root = os.path.join(ROOT, "app_src")
    apk_mtime = os.path.getmtime(apk)
    newest = None
    for dirpath, _dirnames, filenames in os.walk(source_root):
        if os.sep + "tests" in dirpath or os.sep + "android_notify" in dirpath:
            continue
        for name in filenames:
            if not name.endswith((".py", ".kv", ".json", ".xml")):
                continue
            path = os.path.join(dirpath, name)
            mtime = os.path.getmtime(path)
            if mtime > apk_mtime and (newest is None or mtime > newest[0]):
                newest = (mtime, os.path.relpath(path, ROOT))
    return newest[1] if newest else None


def tail(path, lines):
    """Last few lines of a text file, for build failures."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError as failure:
        return f"could not read {path}: {failure}"


class Adb:
    def __init__(self, binary, serial=None):
        self.binary = binary
        self.serial = serial

    def _base(self):
        return [self.binary] + (["-s", self.serial] if self.serial else [])

    def run(self, *args, binary=False):
        cmd = self._base() + [str(a) for a in args]
        result = subprocess.run(cmd, capture_output=True, check=False)
        if binary:
            return result.stdout
        return result.stdout.decode("utf-8", "replace")

    def shell(self, command, **kwargs):
        """Run a command inside a shell on the device."""
        return self.run("shell", command, **kwargs)

    def stream(self, args):
        return subprocess.Popen(self._base() + [str(a) for a in args], stdout=subprocess.PIPE)

    def push(self, local, remote):
        return self.run("push", local, remote)

    def run_as(self, command, **kwargs):
        return self.run("shell", f"run-as {PACKAGE} sh -c '{command}'", **kwargs)

    def require_device(self):
        out = self.run("devices")
        entries = [line for line in out.splitlines()[1:] if line.strip() and "unauthorized" not in line]
        if not entries:
            raise E2EFailure(
                "no device connected. Plug the phone in, enable USB debugging, "
                'and confirm with "adb devices".'
            )
        if self.serial is None and len(entries) > 1:
            print(f"  note: {len(entries)} devices attached, using the first")
        print(f"  device: {entries[0].split()[0]}")


def resolve_adb(explicit):
    binary = explicit or os.environ.get("ADB") or DEFAULT_ADB
    if not os.path.exists(binary):
        raise E2EFailure(f"adb not found at {binary}. Pass --adb or set $ADB.")
    return binary


def app_version():
    """Read VERSION out of utils/constants.py without importing the app."""
    path = os.path.join(ROOT, "app_src", "utils", "constants.py")
    with open(path, encoding="utf-8") as f:
        match = VERSION_RE.search(f.read())
    if not match:
        raise E2EFailure(f"could not find VERSION in {path}")
    return match.group(1)


def next_version(current):
    parts = current.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def newer_version(left, right):
    """The higher of two dotted versions. Non-numeric segments sort as 0."""
    def key(value):
        return tuple(int(part) if part.isdigit() else 0 for part in value.split("."))

    return left if key(left) >= key(right) else right


def find_aapt2():
    if not os.path.isdir(BUILD_TOOLS_GLOB):
        return None
    for name in sorted(os.listdir(BUILD_TOOLS_GLOB), reverse=True):
        candidate = os.path.join(BUILD_TOOLS_GLOB, name, "aapt2")
        if os.path.exists(candidate):
            return candidate
    return None


def apk_badging(apk_path):
    aapt2 = find_aapt2()
    if not aapt2:
        return {}
    out = subprocess.run([aapt2, "dump", "badging", apk_path], capture_output=True, check=False)
    text = out.stdout.decode("utf-8", "replace")
    found = {}
    for key in ("versionName", "versionCode"):
        match = re.search(rf"{key}='([^']+)'", text)
        if match:
            found[key] = match.group(1)
    return found


def pick_apk(explicit, version):
    if explicit:
        return os.path.abspath(explicit)
    bin_dir = os.path.join(ROOT, "bin")
    if not os.path.isdir(bin_dir):
        return None
    candidates = sorted(
        (os.path.join(bin_dir, n) for n in os.listdir(bin_dir) if n.endswith(".apk")),
        key=os.path.getmtime,
        reverse=True,
    )
    for path in candidates:
        badging = apk_badging(path)
        if badging.get("versionName") == version:
            return path
    return None


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


VERSION_RE = re.compile(r'^\s*VERSION\s*=\s*"([^"]+)"', re.MULTILINE)
SPEC_VERSION_RE = re.compile(r"^version\s*=\s*\S+$", re.MULTILINE)
SPEC_NUMERIC_RE = re.compile(r"^android\.numeric_version\s*=\s*\d+$", re.MULTILINE)
SPEC_NUMERIC_VALUE_RE = re.compile(r"^android\.numeric_version\s*=\s*(\d+)", re.MULTILINE)


def spec_numeric_version(spec_text):
    """The android.numeric_version in a buildozer.spec, or None when the line is absent."""
    match = SPEC_NUMERIC_VALUE_RE.search(spec_text)
    return int(match.group(1)) if match else None


def next_version_code(spec_text, installed_code=None):
    """A versionCode guaranteed to sit above both the spec's and the phone's.

    Whichever way the installed build got its versionCode -- an explicit
    android.numeric_version, or one p4a derived from `version` -- staying above both is
    what stops Android treating the test build as a downgrade.
    """
    return max(spec_numeric_version(spec_text) or 0, installed_code or 0) + 1


def bumped_spec(spec_text, version, numeric_version):
    """Return spec_text with version and android.numeric_version set for a test build.

    android.numeric_version is optional in buildozer.spec -- when it is missing, p4a
    derives a versionCode from `version` instead. We still need to pin an exact code so
    the served APK is guaranteed to be above whatever the phone has, so add the line.
    """
    if not SPEC_VERSION_RE.search(spec_text):
        raise E2EFailure("could not find a 'version = ...' line in buildozer.spec")
    bumped = SPEC_VERSION_RE.sub(f"version = {version}", spec_text, count=1)
    if SPEC_NUMERIC_RE.search(bumped):
        return SPEC_NUMERIC_RE.sub(f"android.numeric_version = {numeric_version}", bumped, count=1)
    separator = "" if bumped.endswith("\n") else "\n"
    return f"{bumped}{separator}android.numeric_version = {numeric_version}\n"


def build_new_apk(version, installed_code=None):
    """Build a debug APK whose versionCode is above the installed build.

    Deliberately does not deploy: the phone has to keep the older version so the served
    APK is a genuine upgrade. Bumps buildozer.spec only for the duration of the build
    and always restores it byte for byte, including any android.numeric_version line the
    project does not normally carry.
    """
    spec = os.path.join(ROOT, "buildozer.spec")
    buildozer = os.path.join(ROOT, "venv", "bin", "buildozer")
    if not os.path.exists(buildozer):
        raise E2EFailure(f"buildozer not found at {buildozer}")
    with open(spec, encoding="utf-8") as f:
        original = f.read()
    # Whichever way the installed build got its versionCode, stay above it, otherwise
    # Android treats the test build as a downgrade and refuses to install it.
    numeric = next_version_code(original, installed_code)
    bumped = bumped_spec(original, version, numeric)
    injected = SPEC_NUMERIC_VALUE_RE.search(original) is None
    print(f"  temporarily setting buildozer.spec to version={version} android.numeric_version={numeric}")
    if injected:
        print("  (android.numeric_version is not in buildozer.spec; injecting it for this build only)")
    log_path = os.path.join(ROOT, "bin", "e2e-build.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    try:
        with open(spec, "w", encoding="utf-8") as f:
            f.write(bumped)
        with open(log_path, "wb") as log:
            subprocess.run(
                [buildozer, "android", "debug"],
                cwd=ROOT,
                check=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                env={
                    **os.environ,
                    "VIRTUAL_ENV": os.path.join(ROOT, "venv"),
                    "PATH": os.path.join(ROOT, "venv", "bin") + os.pathsep + os.environ.get("PATH", ""),
                },
            )
    except subprocess.CalledProcessError as failure:
        print(f"  buildozer failed (exit {failure.returncode}), tail of {os.path.relpath(log_path, ROOT)}:")
        print(tail(log_path, 25), flush=True)
        raise
    finally:
        with open(spec, "w", encoding="utf-8") as f:
            f.write(original)
        print("  buildozer.spec restored", flush=True)
    print(f"  full build log: {os.path.relpath(log_path, ROOT)}")
    return pick_apk(None, version)


def push_endpoint(adb, server):
    payload = json.dumps({"api_url": server.api_url, "base_url": server.base_url}, indent=2)
    local = "/tmp/waller_update_endpoint.json"
    with open(local, "w", encoding="utf-8") as f:
        f.write(payload)
    print(f"  api_url  {server.api_url}")
    print(f"  base_url {server.base_url}")
    adb.push(local, "/data/local/tmp/" + ENDPOINT_FILE)
    adb.run_as(f"cp /data/local/tmp/{ENDPOINT_FILE} files/{ENDPOINT_FILE}")
    listing = adb.run_as("ls files")
    if ENDPOINT_FILE not in listing:
        raise E2EFailure(f"{ENDPOINT_FILE} did not land in the app's files dir: {listing!r}")
    back = json.loads(adb.run_as(f"cat files/{ENDPOINT_FILE}"))
    if back != {"api_url": server.api_url, "base_url": server.base_url}:
        raise E2EFailure(f"endpoint file on the device does not match the server: {back!r}")


def clear_cached_apks(adb):
    listing = adb.run_as("ls files")
    for line in listing.splitlines():
        name = line.split()[-1] if line.split() else ""
        if name.endswith(".apk"):
            adb.run_as(f"rm -f files/{name}")
            print(f"  removed cached {name}")


def start_logcat(adb):
    adb.run("logcat", "-c")


def read_logcat(adb):
    return adb.run("logcat", "-d", "-v", "brief")


def wait_for_request(server, needle, timeout, poll=0.5):
    """Poll the server's own request log; proves what actually left the phone."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if any(needle in path for path in server.paths_requested()):
            return True
        time.sleep(poll)
    return False


def wait_for_log(adb, needle, timeout, poll=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if needle in read_logcat(adb):
            return True
        time.sleep(poll)
    return False


def installed_version(adb):
    out = adb.shell(f"dumpsys package {PACKAGE}")
    match = re.search(r"versionName=(\S+)", out)
    return match.group(1) if match else None


def installed_version_code(adb):
    """The installed versionCode, or None when the app is not installed."""
    out = adb.shell(f"dumpsys package {PACKAGE}")
    match = re.search(r"versionCode=(\d+)", out)
    return int(match.group(1)) if match else None


def pull_file(adb, name):
    """Stream one file out of the app's private dir using run-as + tar."""
    process = adb.stream(["exec-out", "run-as", PACKAGE, "tar", "-cf", "-", "-C", APP_FILES_DIR, name])
    payload = process.stdout.read()
    process.wait()
    with tarfile.open(fileobj=BytesIO(payload), mode="r") as tar:
        for member in tar.getmembers():
            if os.path.basename(member.name) == name:
                return tar.extractfile(member).read()
    return None


def send_intent(adb, action, version):
    adb.run(
        "shell",
        "am",
        "start",
        "-n",
        ACTIVITY,
        "--es",
        "action",
        action,
        "--es",
        "version",
        version,
    )


def restart_app(adb):
    adb.run("shell", "am", "force-stop", PACKAGE)
    start_logcat(adb)
    adb.run("shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(6)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--version", help="version to advertise as the new release")
    parser.add_argument("--apk", help="APK to serve; defaults to the newest matching bin/*.apk")
    parser.add_argument("--host", default="127.0.0.1", help="host the phone uses (127.0.0.1 with adb reverse)")
    parser.add_argument("--lan", action="store_true", help="reach the laptop by LAN IP instead of adb reverse")
    parser.add_argument("--range-mode", default="honor", choices=("honor", "ignore", "reject"))
    parser.add_argument("--build-new-apk", action="store_true", help="build a debug APK with a higher versionCode")
    parser.add_argument("--install", action="store_true", help="also fire the install intent and verify the version bump")
    parser.add_argument("--verify-installed", action="store_true", help="only check the installed version, then exit")
    parser.add_argument("--timeout", type=int, default=180, help="seconds to wait for each stage")
    parser.add_argument("--adb", help="path to adb")
    parser.add_argument("--serial", help="device serial when several are attached")
    parser.add_argument("--keep-endpoint", action="store_true", help="leave the endpoint override on the device")
    args = parser.parse_args()

    adb = Adb(resolve_adb(args.adb), args.serial)
    current = app_version()

    step("Checking the device")
    adb.require_device()
    print(f"  app VERSION in source: {current}")
    found = installed_version(adb)
    print(f"  installed versionName: {found}")

    if args.verify_installed:
        if not args.version:
            raise E2EFailure(
                "--verify-installed needs --version X.Y.Z, the version you expect the phone to be running. "
                f"The phone currently reports {found}."
            )
        check(
            f"the phone is running {args.version}",
            found == args.version,
            f"found {found}. The install may not be confirmed yet -- check the system installer on the phone, "
            f"or re-run --verify-installed --version {found} if it already landed.",
        )
        print(f"\n\033[1m{OK} installed version verified\033[0m")
        return 0

    # --build-new-apk only bumps buildozer.spec, so constants.VERSION can lag behind
    # what is on the phone. Advertise something above both, or the "upgrade" is a no-op.
    version = args.version or next_version(newer_version(current, found))
    print(f"  advertising as new:    {version}")

    apk = pick_apk(args.apk, version)
    if args.build_new_apk and not apk:
        apk = build_new_apk(version, installed_version_code(adb))
    if not apk:
        raise E2EFailure(
            f"no APK found for version {version}.\n"
            f"  Build one:  venv/bin/python {os.path.basename(__file__)} --build-new-apk --install\n"
            "  Or pass --apk path/to.apk --version X.Y.Z"
        )

    badging = apk_badging(apk)
    check(
        "the served APK really is the version we advertise",
        badging.get("versionName") == version,
        f"serving {os.path.basename(apk)} = {badging.get('versionName')}, advertised {version}",
    )
    served_size = os.path.getsize(apk)
    served_sha = sha256_file(apk)
    print(f"  {os.path.basename(apk)}  {served_size} bytes  sha256={served_sha[:16]}...")
    stale = newest_source_mtime(apk)
    if stale:
        print(f"  warning: {os.path.basename(apk)} is older than {stale} -- it was served as-is, not rebuilt")

    step("Starting the local release server")
    server = ReleaseServer(
        version=version, apk_path=apk, host="0.0.0.0", port=args.port, range_mode=args.range_mode
    )
    try:
        server.start()
    except PortInUseError as failure:
        raise E2EFailure(str(failure)) from failure
    if not args.lan:
        adb.run("reverse", f"tcp:{args.port}", f"tcp:{args.port}")
        print(f"  adb reverse tcp:{args.port} -> this machine")
    else:
        print(f"  the phone must reach {args.host}:{args.port}")

    try:
        step("Clearing cached APKs so the download really runs")
        clear_cached_apks(adb)

        step("Pointing the app at the local server")
        push_endpoint(adb, server)

        step("Restarting the app -- the auto-check runs because an override is present")
        restart_app(adb)
        check(
            "the app fetched the release JSON from this laptop",
            wait_for_request(server, "/releases/latest", args.timeout),
            f"the laptop saw no request for {server.api_path} within {args.timeout}s",
        )
        check(
            "the app then fetched the release notes from this laptop",
            wait_for_request(server, server.notes_name, 30),
            f"the laptop saw no request for {server.notes_name}",
        )

        step("Asking the app to download the new release")
        server.reset_log()
        send_intent(adb, "download_update", version)
        check(
            f"the app downloaded from {server.base_url}",
            wait_for_request(server, server.apk_name, args.timeout),
            f"the laptop saw no request for {server.apk_name} within {args.timeout}s",
        )
        check(
            "the app reported the download finished",
            wait_for_log(adb, "Download completed:", 30),
            "no 'Download completed:' line in logcat",
        )

        step("Comparing what landed on the phone against what was served")
        name = f"waller-v{version}.apk"
        pulled = pull_file(adb, name)
        check(f"{name} is in the app's files dir", pulled is not None)
        check("size matches", len(pulled) == served_size, f"device {len(pulled)} vs served {served_size}")
        device_sha = hashlib.sha256(pulled).hexdigest()
        check(
            "sha256 matches",
            device_sha == served_sha,
            f"device {device_sha[:16]}... vs served {served_sha[:16]}...",
        )
        ranges = [r["range"] for r in server.requests if r["path"].endswith(".apk")]
        sent = [r for r in ranges if r]
        print(f"  {'Range headers sent: ' + ', '.join(sent) if sent else 'fresh download, no Range header sent'}")
        if sent:
            print("  note: the partial-file/Range path was exercised on this run")

        if args.install:
            step("Firing the install intent")
            send_intent(adb, "install_update", version)
            check(
                "the app asked the system installer to open",
                wait_for_log(adb, "Called do_android_install", 30),
                "no 'Called do_android_install' line in logcat",
            )
            print("\n  Confirm the update in the system installer on the phone, then run:")
            print(f"    venv/bin/python {os.path.basename(__file__)} --verify-installed --version {version}")

        print(f"\n\033[1m{OK} end-to-end release download verified\033[0m")
        return 0

    finally:
        server.stop()
        if not args.lan:
            adb.run("reverse", "--remove", f"tcp:{args.port}")
        if not args.keep_endpoint:
            adb.run_as(f"rm -f files/{ENDPOINT_FILE}")
            print("removed the endpoint override from the device")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except E2EFailure as failure:
        print(f"\n\033[1m{FAIL} {failure}\033[0m", flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)