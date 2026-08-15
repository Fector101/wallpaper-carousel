#!/usr/bin/env python3
"""Waller cold-start boot timing test (Python version of boot_test.sh).

Usage:
    python app_src/tests/boot_test.py [runs]
    python3 app_src/tests/boot_test.py 1       # 1 runs

Runs `runs` cold starts against a connected Android device via adb,
captures [BOOT] markers from logcat, prints per-run timings and a
costliest-operations breakdown, and tars the results into
.buildozer/scratch/.
"""

import argparse
import math
import os
import re
import subprocess
import sys
import tarfile
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PKG = "org.wally.waller"
ACTIVITY = f"{PKG}/org.kivy.android.PythonActivity"
WAIT_BOOT = 35
COOLDOWN = 3
TOP_N = 12

BOOT_MARKER = "[BOOT]"
DELTA_RE = re.compile(r"\+\s*(\d+\.\d+)s")
TOTAL_RE = re.compile(r"total\s+(\d+\.\d+)s")
LABEL_RE = re.compile(r"^.*\[BOOT\]\s+(.*?):\s+\+\d+\.\d+s\s*\(.*")

DEFAULT_ADB = Path.home() / ".buildozer/android/platform/android-sdk/platform-tools/adb"


def find_adb():
    """Locate the adb binary: env var, PATH, or the default buildozer path."""
    env = os.environ.get("ADB")
    if env:
        return Path(env)
    which = subprocess.run(["which", "adb"], capture_output=True, text=True)
    if which.returncode == 0 and which.stdout.strip():
        return Path(which.stdout.strip())
    if DEFAULT_ADB.exists():
        return DEFAULT_ADB
    raise FileNotFoundError(
        "Could not locate adb. Set ADB env var or pass the path."
    )


def adb(adb_path: Path, *args) -> str:
    """Run an adb command and return stdout."""
    proc = subprocess.run(
        [str(adb_path), *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout


def adb_silent(adb_path: Path, *args) -> bool:
    """Run an adb command, ignore errors, return success."""
    proc = subprocess.run(
        [str(adb_path), *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def parse_log(log: str):
    """Parse [BOOT] lines into a list of (label, delta_s, total_s)."""
    entries = []
    for line in log.splitlines():
        if BOOT_MARKER not in line:
            continue
        m = DELTA_RE.search(line)
        if not m:
            continue
        delta = float(m.group(1))
        total_m = TOTAL_RE.search(line)
        total = float(total_m.group(1)) if total_m else None
        label_m = LABEL_RE.match(line)
        label = label_m.group(1) if label_m else line.split(BOOT_MARKER, 1)[-1].strip()
        entries.append((label, delta, total))
    return entries


def breakdown(entries, top_n=TOP_N):
    """Return the costliest operations as (label, avg_delta)."""
    by_label = defaultdict(list)
    for label, delta, _total in entries:
        by_label[label].append(delta)
    return sorted(
        ((label, sum(ds) / len(ds)) for label, ds in by_label.items()),
        key=lambda t: t[1],
        reverse=True,
    )[:top_n]


def print_breakdown(title, rows):
    print(f"\n{title}")
    for label, avg in rows:
        print(f"  +{avg:.3f}s  {label}")


def main():
    parser = argparse.ArgumentParser(description="Waller cold-start boot timing test")
    parser.add_argument("runs", nargs="?", type=int, default=5)
    parser.add_argument("--adb", help="Path to adb binary")
    args = parser.parse_args()

    runs = args.runs
    adb_path = Path(args.adb) if args.adb else find_adb()

    if not adb_silent(adb_path, "get-state"):
        print("ERROR: No device connected")
        sys.exit(1)

    scratch = Path(__file__).resolve().parent.parent.parent / ".buildozer" / "scratch"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = scratch / f"boot_test-{timestamp}"
    outdir.mkdir(parents=True, exist_ok=True)

    build_times = []
    full_times = []
    all_entries = []

    for i in range(1, runs + 1):
        print(f"\n===== Run {i} / {runs} =====")

        adb_silent(adb_path, "shell", "am", "force-stop", PKG)
        adb_silent(adb_path, "logcat", "-c")
        adb_silent(adb_path, "shell", "am", "start", "-n", ACTIVITY)

        time.sleep(WAIT_BOOT)

        try:
            raw = adb(adb_path, "logcat", "-d")
        except RuntimeError:
            raw = ""
        (outdir / f"run{i}-logcat.txt").write_text(raw, encoding="utf-8", errors="replace")

        boot_lines = [l for l in raw.splitlines() if BOOT_MARKER in l]
        if not boot_lines:
            print(f"  WARNING: No [BOOT] markers found — see run{i}-logcat.txt")
            continue

        clean = [re.sub(r"^.*\[BOOT\]\s+", "[BOOT] ", l) for l in boot_lines]
        for line in clean:
            print(line)
        (outdir / f"run{i}-boot.log").write_text("\n".join(clean) + "\n", encoding="utf-8")

        entries = parse_log("\n".join(boot_lines))
        all_entries.extend(entries)

        by_label_total = {label: total for label, _d, total in entries if total is not None}
        build_done = next(
            (t for label, t in by_label_total.items()
             if "build: build_ui done" in label),
            None,
        )
        full_done = next(
            (t for label, t in by_label_total.items()
             if "setup_service: done" in label),
            None,
        )

        bs = f"{build_done:.3f}" if build_done is not None else "?"
        fs = f"{full_done:.3f}" if full_done is not None else "?"
        print(f"\n  -> build_ui visible at: {bs}s")
        print(f"  -> full boot (incl service): {fs}s")

        rows = breakdown(entries)
        (outdir / f"run{i}-breakdown.txt").write_text(
            "\n".join(f"+{a:.3f}s  {l}" for l, a in rows) + "\n",
            encoding="utf-8",
        )
        print_breakdown("  Costliest operations:", rows)

        if build_done is not None:
            build_times.append(build_done)
        if full_done is not None:
            full_times.append(full_done)

        adb_silent(adb_path, "shell", "am", "force-stop", PKG)
        if i < runs:
            time.sleep(COOLDOWN)

    # Summary
    print(f"\n===== Summary ({runs} runs) =====")
    print(f"Build_ui times (s): {' '.join(f'{t:.3f}' for t in build_times) or '?'}")
    print(f"Full boot times (s): {' '.join(f'{t:.3f}' for t in full_times) or '?'}")

    if build_times:
        print(f"Average build_ui time: {sum(build_times) / len(build_times):.2f}s")
    if full_times:
        print(f"Average full boot time: {sum(full_times) / len(full_times):.2f}s")

    if all_entries:
        print_breakdown("===== Aggregate breakdown (avg per operation, top 12) =====", breakdown(all_entries))

    # Write summary.txt
    summary = (
        f"Waller cold-start boot test — {runs} runs — {datetime.now()}\n"
        f"Build_ui times (s): {' '.join(f'{t:.3f}' for t in build_times) or '?'}\n"
        f"Full boot times (s): {' '.join(f'{t:.3f}' for t in full_times) or '?'}\n"
        f"Average build_ui: {sum(build_times) / len(build_times):.2f}s\n"
        f"Average full boot: {sum(full_times) / len(full_times):.2f}s\n"
    )
    (outdir / "summary.txt").write_text(summary, encoding="utf-8")

    # Tar it up
    tarfile_path = scratch / f"boot_test-{timestamp}.tar.gz"
    with tarfile.open(tarfile_path, "w:gz") as tar:
        tar.add(outdir, arcname=outdir.name)

    print(f"\nLogs saved to: {outdir}")
    print(f"Tar: {tarfile_path}")


if __name__ == "__main__":
    main()
