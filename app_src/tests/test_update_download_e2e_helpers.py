"""Helpers from ``update_download_e2e``, tested without a device or a build.

The E2E driver rewrites ``buildozer.spec`` for the duration of a build and restores it
afterwards. Getting that wrong is invisible until the phone refuses to install the APK,
so the spec rewriting and version arithmetic are pinned here.
"""

import pytest
import update_download_e2e as e2e

SPEC_WITH_NUMERIC = "version = 1.0.10\nandroid.numeric_version = 102410011\nrequirements = kivy\n"
SPEC_WITHOUT_NUMERIC = "version = 1.0.10\nrequirements = kivy\n"
SPEC_NO_TRAILING_NEWLINE = "version = 1.0.10\nrequirements = kivy"


def test_spec_numeric_version_reads_the_line():
    assert e2e.spec_numeric_version(SPEC_WITH_NUMERIC) == 102410011


def test_spec_numeric_version_is_none_when_the_project_omits_it():
    assert e2e.spec_numeric_version(SPEC_WITHOUT_NUMERIC) is None


def test_bumped_spec_replaces_an_existing_numeric_version():
    bumped = e2e.bumped_spec(SPEC_WITH_NUMERIC, "1.0.16", 102410017)
    assert "version = 1.0.16" in bumped
    assert "android.numeric_version = 102410017" in bumped
    assert bumped.count("android.numeric_version") == 1


def test_bumped_spec_adds_the_line_when_the_project_does_not_carry_one():
    """buildozer.spec has no android.numeric_version, so the test build has to add it."""
    bumped = e2e.bumped_spec(SPEC_WITHOUT_NUMERIC, "1.0.16", 102410017)
    assert bumped.endswith("android.numeric_version = 102410017\n")


def test_bumped_spec_adds_a_newline_before_the_injected_line_when_needed():
    bumped = e2e.bumped_spec(SPEC_NO_TRAILING_NEWLINE, "1.0.16", 102410017)
    assert bumped == "version = 1.0.16\nrequirements = kivy\nandroid.numeric_version = 102410017\n"


def test_bumped_spec_leaves_every_other_line_alone():
    bumped = e2e.bumped_spec(SPEC_WITHOUT_NUMERIC, "1.0.16", 102410017)
    assert "requirements = kivy" in bumped


def test_bumped_spec_complains_when_there_is_no_version_line():
    with pytest.raises(e2e.E2EFailure, match="version"):
        e2e.bumped_spec("requirements = kivy\n", "1.0.16", 102410017)


def test_next_version_code_stays_above_the_spec():
    assert e2e.next_version_code(SPEC_WITH_NUMERIC) == 102410012


def test_next_version_code_stays_above_the_phone_when_it_is_ahead_of_the_spec():
    """The phone can outrun buildozer.spec, since the E2E restores the spec every run."""
    assert e2e.next_version_code(SPEC_WITH_NUMERIC, installed_code=102410099) == 102410100


def test_next_version_code_works_when_neither_the_spec_nor_the_phone_says_anything():
    assert e2e.next_version_code(SPEC_WITHOUT_NUMERIC) == 1
    assert e2e.next_version_code(SPEC_WITHOUT_NUMERIC, installed_code=None) == 1


def test_the_real_buildozer_spec_round_trips_without_gaining_a_leaked_line():
    """The injected line must not survive the restore, or it lands in a commit."""
    with open(e2e.os.path.join(e2e.ROOT, "buildozer.spec"), encoding="utf-8") as handle:
        original = handle.read()
    bumped = e2e.bumped_spec(original, "9.9.9", e2e.next_version_code(original))
    assert "version = 9.9.9" in bumped
    # build_new_apk writes `original` back verbatim, so nothing else can leak.
    assert "version = 9.9.9" not in original


def test_the_advertised_version_is_above_both_the_source_and_the_phone():
    """The served APK has to be a genuine upgrade or the install leg proves nothing."""
    assert e2e.next_version(e2e.newer_version("1.0.10", "1.0.16")) == "1.0.17"


def test_the_advertised_version_is_above_the_phone_when_the_source_lags():
    assert e2e.next_version(e2e.newer_version("1.0.10", "1.0.9")) == "1.0.11"


def test_installed_version_code_parses_dumpsys():
    class _Adb:
        def shell(self, _command):
            return "versionCode=102410012 minSdk=24 targetSdk=36\n  versionName=1.0.16\n"

    assert e2e.installed_version_code(_Adb()) == 102410012
    assert e2e.installed_version(_Adb()) == "1.0.16"


def test_installed_version_code_is_none_when_the_app_is_not_installed():
    class _Adb:
        def shell(self, _command):
            return "Unable to find package: org.wally.waller"

    assert e2e.installed_version_code(_Adb()) is None
    assert e2e.installed_version(_Adb()) is None