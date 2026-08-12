import logging
import sys

import pytest

import utils.helper as helper
from utils.service_helper import prevent_log_file_overflow
from utils.logger import app_logger

DEFAULT_MAX_BYTES = 512 * 1024


class FakeTee:
    """Mimics utils.helper.Tee: one open fd held for the whole session."""

    def __init__(self, path):
        self.file = open(path, "a", encoding="utf-8")

    def write(self, message):
        self.file.write(message)
        self.file.flush()

    def flush(self):
        self.file.flush()


@pytest.fixture
def log_setup(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "app_external_storage_path", lambda: str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    file_path = log_dir / "all_output1.txt"
    tee = FakeTee(str(file_path))
    old_stdout = sys.stdout
    sys.stdout = tee
    handler = app_logger.handlers[0]
    old_stream = handler.stream
    handler.stream = tee
    try:
        yield tee, file_path
    finally:
        sys.stdout = old_stdout
        handler.stream = old_stream
        tee.file.close()


def test_does_nothing_when_log_file_missing(log_setup):
    _, file_path = log_setup
    file_path.unlink()
    prevent_log_file_overflow()
    assert not file_path.exists()


def test_leaves_small_file_untouched(log_setup):
    _, file_path = log_setup
    content = b"small log content"
    file_path.write_bytes(content)
    prevent_log_file_overflow()
    assert file_path.read_bytes() == content


def test_leaves_file_just_under_threshold_untouched(log_setup):
    _, file_path = log_setup
    content = b"a" * (DEFAULT_MAX_BYTES - 1)
    file_path.write_bytes(content)
    prevent_log_file_overflow()
    assert file_path.read_bytes() == content


def test_truncates_file_over_threshold(log_setup):
    _, file_path = log_setup
    file_path.write_bytes(b"a" * (DEFAULT_MAX_BYTES + 1))
    prevent_log_file_overflow()
    assert file_path.read_bytes() == b""


def test_truncates_exactly_at_threshold(log_setup):
    _, file_path = log_setup
    file_path.write_bytes(b"a" * DEFAULT_MAX_BYTES)
    prevent_log_file_overflow()
    assert file_path.read_bytes() == b""


def test_truncation_keeps_tee_fd_in_sync(log_setup):
    """Regression: truncating through a fresh handle leaves the Tee's fd past
    EOF and the next write re-extends the file with a null-byte gap."""
    tee, file_path = log_setup
    file_path.write_bytes(b"a" * (DEFAULT_MAX_BYTES + 1))
    prevent_log_file_overflow()
    tee.write("FRESH")
    tee.flush()
    assert file_path.read_bytes() == b"FRESH"


def test_custom_max_bytes_truncates(log_setup):
    _, file_path = log_setup
    file_path.write_bytes(b"a" * 100)
    prevent_log_file_overflow(max_bytes=50)
    assert file_path.read_bytes() == b""


def test_custom_max_bytes_leaves_smaller_file(log_setup):
    _, file_path = log_setup
    content = b"a" * 49
    file_path.write_bytes(content)
    prevent_log_file_overflow(max_bytes=50)
    assert file_path.read_bytes() == content


def test_does_not_crash_without_tee_on_stdout(tmp_path, monkeypatch):
    monkeypatch.setattr(helper, "app_external_storage_path", lambda: str(tmp_path))
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    file_path = log_dir / "all_output1.txt"
    file_path.write_bytes(b"a" * (DEFAULT_MAX_BYTES + 1))
    prevent_log_file_overflow()
