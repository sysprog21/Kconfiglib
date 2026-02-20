"""Tests for the 'transitional' keyword (Linux >= 6.18).

Transitional symbols are read from old .config files to populate new symbol
defaults.  The 'transitional' flag only affects UI display (menuconfig) --
transitional symbols are still written to .config, autoconf.h, and min-config
output, matching the C tools behavior.
"""

import os
import tempfile

import kconfiglib

KCONFIG_PATH = "tests/Ktransitional"
CONFIG_PATH = "tests/config_transitional"


def _load(config_path=None):
    """Load the transitional test Kconfig, optionally with a .config."""
    kconf = kconfiglib.Kconfig(KCONFIG_PATH, warn=False)
    if config_path:
        kconf.load_config(config_path)
    return kconf


def test_transitional_flag():
    """is_transitional is True for transitional syms, False for normal."""
    kconf = _load()

    assert kconf.syms["LEGACY_BOOL"].is_transitional is True
    assert kconf.syms["LEGACY_INT"].is_transitional is True
    assert kconf.syms["NEW_BOOL"].is_transitional is False
    assert kconf.syms["NEW_INT"].is_transitional is False
    assert kconf.syms["NORMAL_BOOL"].is_transitional is False
    assert kconf.syms["NORMAL_INT"].is_transitional is False


def test_transitional_migration():
    """Loading old .config with LEGACY_BOOL=y causes NEW_BOOL to default to y."""
    kconf = _load(CONFIG_PATH)

    # LEGACY_BOOL=y was loaded, so NEW_BOOL (default LEGACY_BOOL) should be y
    assert kconf.syms["NEW_BOOL"].str_value == "y"
    # LEGACY_INT=99 was loaded, so NEW_INT (default LEGACY_INT) should be 99
    assert kconf.syms["NEW_INT"].str_value == "99"


def test_transitional_write_config():
    """Transitional symbols appear in write_config output (matching C tools)."""
    kconf = _load(CONFIG_PATH)

    with tempfile.NamedTemporaryFile(mode="r", suffix=".config", delete=False) as f:
        tmppath = f.name
    try:
        kconf.write_config(tmppath)
        with open(tmppath) as f:
            content = f.read()
    finally:
        os.unlink(tmppath)

    assert "LEGACY_BOOL" in content
    assert "LEGACY_INT" in content
    assert "NEW_BOOL" in content
    assert "NORMAL_BOOL" in content
    assert "NORMAL_INT" in content


def test_transitional_write_autoconf():
    """Transitional symbols appear in write_autoconf output (matching C tools)."""
    kconf = _load(CONFIG_PATH)

    with tempfile.NamedTemporaryFile(mode="r", suffix=".h", delete=False) as f:
        tmppath = f.name
    try:
        kconf.write_autoconf(tmppath)
        with open(tmppath) as f:
            content = f.read()
    finally:
        os.unlink(tmppath)

    assert "LEGACY_BOOL" in content
    assert "LEGACY_INT" in content
    assert "NEW_BOOL" in content


def test_transitional_write_min_config():
    """Transitional symbols appear in write_min_config output (matching C tools)."""
    kconf = _load(CONFIG_PATH)

    with tempfile.NamedTemporaryFile(mode="r", suffix=".config", delete=False) as f:
        tmppath = f.name
    try:
        kconf.write_min_config(tmppath)
        with open(tmppath) as f:
            content = f.read()
    finally:
        os.unlink(tmppath)

    assert "LEGACY_BOOL" in content
    assert "LEGACY_INT" in content


def test_transitional_config_string():
    """config_string returns normal output for transitional symbols."""
    kconf = _load(CONFIG_PATH)

    assert kconf.syms["LEGACY_BOOL"].config_string != ""
    assert kconf.syms["LEGACY_INT"].config_string != ""
    assert kconf.syms["NORMAL_BOOL"].config_string != ""
    assert kconf.syms["NORMAL_INT"].config_string != ""


def test_transitional_repr():
    """repr() includes 'transitional' for flagged symbols."""
    kconf = _load()

    # Use ", transitional," to avoid false-matching the filename Ktransitional
    assert ", transitional," in repr(kconf.syms["LEGACY_BOOL"])
    assert ", transitional," in repr(kconf.syms["LEGACY_INT"])
    assert ", transitional," not in repr(kconf.syms["NEW_BOOL"])
    assert ", transitional," not in repr(kconf.syms["NORMAL_BOOL"])
