import pytest

from utils.helper import format_countdown, format_time_remaining


@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00"),
    (1, "00:01"),
    (59, "00:59"),
])
def test_under_a_minute_uses_precise_mm_ss(seconds, expected):
    assert format_countdown(seconds) == expected


@pytest.mark.parametrize("seconds,expected", [
    (60, "1 min"),
    (61, "1 min"),
    (119, "1 min"),
    (120, "2 mins"),
])
def test_mins_updates_once_per_minute(seconds, expected):
    assert format_countdown(seconds) == expected


def test_interval_sized_values():
    assert format_countdown(1800) == "30 mins"


def test_hours_intervals_stay_minute_based():
    assert format_countdown(3 * 3600) == "180 mins"
    assert format_countdown(10 * 3600 + 45 * 60) == "645 mins"


def test_format_time_remaining_unchanged():
    assert format_time_remaining(90) == "01:30"