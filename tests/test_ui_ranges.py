# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Regression tests for the INT/HEX range helpers in menuconfig and guiconfig.
#
# These call the *real* _range_info()/_check_valid() functions (not a
# reimplementation) so that a mis-count of the sym.ranges tuples is caught here
# instead of by a user. sym.ranges yields 4-tuples (low, high, cond, loc);
# unpacking them as 3-tuples was the root cause of issue #41, which shipped
# because nothing exercised these paths.

import pytest

import menuconfig
from kconfiglib import Kconfig


@pytest.fixture(scope="module")
def kconf():
    return Kconfig("tests/Krange", warn=False)


# ---------------------------------------------------------------------------
# menuconfig
# ---------------------------------------------------------------------------


def test_menuconfig_range_info_active(kconf):
    # Active range -> the loop body unpacks a 4-tuple. This is the #41 path.
    assert menuconfig._range_info(kconf.syms["INT_RANGE_10_20"]) == "Range: 10-20"
    assert menuconfig._range_info(kconf.syms["HEX_RANGE_10_20"]) == "Range: 0x10-0x20"


def test_menuconfig_range_info_none(kconf):
    # No range, and all-ranges-disabled (cond is n): still iterates and unpacks
    # every tuple, but reports no active range.
    assert menuconfig._range_info(kconf.syms["INT_NO_RANGE"]) is None
    assert menuconfig._range_info(kconf.syms["INT_ALL_RANGES_DISABLED"]) is None
    assert menuconfig._range_info(kconf.syms["HEX_ALL_RANGES_DISABLED"]) is None


def test_menuconfig_check_valid(kconf, monkeypatch):
    errors = []
    monkeypatch.setattr(menuconfig, "_error", errors.append)

    sym = kconf.syms["INT_RANGE_10_20"]
    assert menuconfig._check_valid(sym, "15") is True  # in range
    assert menuconfig._check_valid(sym, "5") is False  # below
    assert menuconfig._check_valid(sym, "25") is False  # above
    assert menuconfig._check_valid(sym, "abc") is False  # malformed

    hex_sym = kconf.syms["HEX_RANGE_10_20"]
    assert menuconfig._check_valid(hex_sym, "0x15") is True
    assert menuconfig._check_valid(hex_sym, "0x5") is False

    # No active range -> any well-formed value passes.
    assert menuconfig._check_valid(kconf.syms["INT_NO_RANGE"], "999") is True
    assert menuconfig._check_valid(kconf.syms["INT_ALL_RANGES_DISABLED"], "999") is True

    assert errors, "expected at least one error to be reported"


# ---------------------------------------------------------------------------
# guiconfig (skipped where tkinter is unavailable)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def guiconfig():
    return pytest.importorskip("guiconfig")


def test_guiconfig_range_info_active(guiconfig, kconf):
    assert guiconfig._range_info(kconf.syms["INT_RANGE_10_20"]) == "Range: 10-20"
    assert guiconfig._range_info(kconf.syms["HEX_RANGE_10_20"]) == "Range: 0x10-0x20"


def test_guiconfig_range_info_none(guiconfig, kconf):
    assert guiconfig._range_info(kconf.syms["INT_NO_RANGE"]) is None
    assert guiconfig._range_info(kconf.syms["INT_ALL_RANGES_DISABLED"]) is None


def test_guiconfig_check_valid(guiconfig, kconf, monkeypatch):
    errors = []

    class FakeEntry:
        def focus_set(self):
            pass

    monkeypatch.setattr(
        guiconfig.messagebox,
        "showerror",
        lambda *a, **k: errors.append(a),
    )

    entry = FakeEntry()
    sym = kconf.syms["INT_RANGE_10_20"]
    assert guiconfig._check_valid(None, entry, sym, "15") is True
    assert guiconfig._check_valid(None, entry, sym, "5") is False
    assert guiconfig._check_valid(None, entry, sym, "abc") is False
    assert (
        guiconfig._check_valid(None, entry, kconf.syms["INT_NO_RANGE"], "999") is True
    )

    assert errors, "expected at least one error to be reported"
