# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Shared fixtures and assertion helpers for the Kconfiglib pytest suite.

import glob
import os
import sys

import pytest

# Ensure kconfiglib is importable from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kconfiglib import TRI_TO_STR  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Save and restore environment variables between tests.

    Also removes KCONFIG_ALLCONFIG to prevent accidental config loading.
    """
    monkeypatch.delenv("KCONFIG_ALLCONFIG", raising=False)
    yield


@pytest.fixture(autouse=True)
def _cleanup_config_files():
    """Remove config_test* files after each test."""
    yield
    tests_dir = os.path.join(os.path.dirname(__file__))
    for f in glob.glob(os.path.join(tests_dir, "config_test*")):
        os.remove(f)
    # Also clean from project root (some tests write there)
    project_root = os.path.join(os.path.dirname(__file__), "..")
    for f in glob.glob(os.path.join(project_root, "config_test*")):
        os.remove(f)


# ---------------------------------------------------------------------------
# Assertion helpers
#
# These take an explicit Kconfig instance `c` rather than closing over one.
# ---------------------------------------------------------------------------


def verify_value(c, sym_name, val):
    """Verify that a symbol has a particular value."""
    if isinstance(val, int):
        val = TRI_TO_STR[val]

    sym = c.syms[sym_name]
    assert sym.str_value == val, f"{sym_name} value mismatch"


def assign_and_verify_value(c, sym_name, val, new_val):
    """Assign val to a symbol and verify its value becomes new_val."""
    if isinstance(new_val, int):
        new_val = TRI_TO_STR[new_val]

    sym = c.syms[sym_name]
    assert sym.set_value(val), f"Failed to assign '{val}' to {sym_name}"
    assert sym.str_value == new_val, f"{sym_name} value after assignment"


def assign_and_verify(c, sym_name, user_val):
    """Like assign_and_verify_value(), with the expected value being the
    value just set."""
    assign_and_verify_value(c, sym_name, user_val, user_val)


def assign_and_verify_user_value(c, sym_name, val, user_val, valid):
    """Assign a user value and verify the new user value and validity."""
    sym = c.syms[sym_name]
    assert sym.set_value(val) == valid, f"{sym_name} validity mismatch for '{val}'"
    assert sym.user_value == user_val, f"{sym_name} user_value mismatch"


def verify_str(item, expected):
    """Verify str(item) matches expected (strip leading/trailing newline)."""
    assert str(item) == expected[1:-1]
