import pytest

from utils.helper import format_time_remaining


@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00"),
    (1, "00:01"),
    (59, "00:59"),
    (90, "01:30"),
    (1800, "30:00"),
])
def test_countdown_is_always_precise_mm_ss(seconds, expected):
    """The notification title is built straight from this, so it has to read as a
    live MM:SS countdown rather than a rounded '30 mins' that drifts from the
    countdown shown inside the app."""
    assert format_time_remaining(seconds) == expected


def test_interval_sized_values():
    assert format_time_remaining(3 * 3600) == "180:00"