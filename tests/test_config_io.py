# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Config I/O tests: load_config, write_config, write_min_config,
# header strings, symbol order in generated files, config_string,
# and missing_syms.

import os
import tempfile

from kconfiglib import Kconfig
from conftest import verify_value


def verify_file_contents(fname, expected):
    with open(fname) as f:
        actual = f.read()
    assert actual == expected, f"{fname} contains '{actual}'. Expected '{expected}'."


# -- .config escape roundtrip --------------------------------------------------


def test_config_escape_roundtrip():
    config_test_file = "tests/config_test"

    c = Kconfig("tests/Kescape")

    # Test the default value
    c.write_config(config_test_file + "_from_def")
    verify_file_contents(
        config_test_file + "_from_def", r'''CONFIG_STRING="\"\\"''' "\n"
    )

    # Write our own value
    c.syms["STRING"].set_value(r"""\"a'\\""")
    c.write_config(config_test_file + "_from_user")
    verify_file_contents(
        config_test_file + "_from_user", r'''CONFIG_STRING="\\\"a'\\\\"''' "\n"
    )

    # Read back the two configs and verify the respective values
    c.load_config(config_test_file + "_from_def")
    verify_value(c, "STRING", '"\\')
    c.load_config(config_test_file + "_from_user")
    verify_value(c, "STRING", r"""\"a'\\""")


# -- .config append loading ----------------------------------------------------


def test_config_append():
    c = Kconfig("tests/Kappend")

    # Values before assigning
    verify_value(c, "BOOL", "n")
    verify_value(c, "STRING", "")

    # Assign BOOL
    c.load_config("tests/config_set_bool", replace=False)
    verify_value(c, "BOOL", "y")
    verify_value(c, "STRING", "")

    # Assign STRING
    c.load_config("tests/config_set_string", replace=False)
    verify_value(c, "BOOL", "y")
    verify_value(c, "STRING", "foo bar")

    # Reset BOOL
    c.load_config("tests/config_set_string")
    verify_value(c, "BOOL", "n")
    verify_value(c, "STRING", "foo bar")

    # Loading a completely empty .config should reset values
    c.load_config("tests/empty")
    verify_value(c, "STRING", "")

    # An indented assignment in a .config should be ignored
    c.load_config("tests/config_indented")
    verify_value(c, "IGNOREME", "y")


# -- symbol order in autoconf and minimal config -------------------------------


def test_symbol_order():
    config_test_file = "tests/config_test"

    c = Kconfig("tests/Korder")

    c.write_autoconf(config_test_file)
    verify_file_contents(
        config_test_file,
        """\
#define CONFIG_O 0
#define CONFIG_R 1
#define CONFIG_D 2
#define CONFIG_E 3
#define CONFIG_R2 4
#define CONFIG_I 5
#define CONFIG_N 6
#define CONFIG_G 7
""",
    )

    # Differs from defaults
    c.syms["O"].set_value("-1")
    c.syms["R"].set_value("-1")
    c.syms["E"].set_value("-1")
    c.syms["R2"].set_value("-1")
    c.syms["N"].set_value("-1")
    c.syms["G"].set_value("-1")
    c.write_min_config(config_test_file)
    verify_file_contents(
        config_test_file,
        """\
CONFIG_O=-1
CONFIG_R=-1
CONFIG_E=-1
CONFIG_R2=-1
CONFIG_N=-1
CONFIG_G=-1
""",
    )


# -- header strings in configuration files ------------------------------------


def test_header_strings(monkeypatch):
    config_test_file = "tests/config_test"

    monkeypatch.setenv("KCONFIG_CONFIG_HEADER", "config header from env.\n")
    monkeypatch.setenv("KCONFIG_AUTOHEADER_HEADER", "header header from env.\n")

    c = Kconfig("tests/Kheader")

    c.write_config(config_test_file, header="config header from param\n")
    verify_file_contents(
        config_test_file,
        """\
config header from param
CONFIG_FOO=y
""",
    )

    c.write_min_config(config_test_file, header="min. config header from param\n")
    verify_file_contents(
        config_test_file,
        """\
min. config header from param
""",
    )

    c.write_config(config_test_file)
    verify_file_contents(
        config_test_file,
        """\
config header from env.
CONFIG_FOO=y
""",
    )

    c.write_min_config(config_test_file)
    verify_file_contents(
        config_test_file,
        """\
config header from env.
""",
    )

    c.write_autoconf(config_test_file, header="header header from param\n")
    verify_file_contents(
        config_test_file,
        """\
header header from param
#define CONFIG_FOO 1
""",
    )

    c.write_autoconf(config_test_file)
    verify_file_contents(
        config_test_file,
        """\
header header from env.
#define CONFIG_FOO 1
""",
    )


# -- Kconfig fetching and separation ------------------------------------------


def test_kconfig_fetching():
    for c in (
        Kconfig("tests/Kmisc", warn=False),
        Kconfig("tests/Kmisc", warn=False),
    ):
        for item in (
            c.syms["BOOL"],
            c.syms["BOOL"].nodes[0],
            c.named_choices["OPTIONAL"],
            c.named_choices["OPTIONAL"].nodes[0],
            c.syms["MENU_HOOK"].nodes[0].next,
            c.syms["COMMENT_HOOK"].nodes[0].next,
        ):
            assert item.kconfig is c, f".kconfig not properly set for {item!r}"


# -- Symbol.config_string ----------------------------------------------------


def test_config_string():
    c = Kconfig("tests/Kassignable", warn=False)
    c.modules.set_value(2)

    # Bool y -> "CONFIG_...=y"
    c.syms["Y_VIS_BOOL"].set_value(2)
    assert c.syms["Y_VIS_BOOL"].config_string == "CONFIG_Y_VIS_BOOL=y\n"

    # Bool n -> "# CONFIG_... is not set"
    c.syms["Y_VIS_BOOL"].set_value(0)
    assert c.syms["Y_VIS_BOOL"].config_string == "# CONFIG_Y_VIS_BOOL is not set\n"

    # Tristate m -> "CONFIG_...=m"
    c.syms["Y_VIS_TRI"].set_value(1)
    assert c.syms["Y_VIS_TRI"].config_string == "CONFIG_Y_VIS_TRI=m\n"

    # Symbol with no visibility -> empty string (_write_to_conf false)
    assert c.syms["N_VIS_BOOL"].config_string == ""

    # String symbol: "CONFIG_...=\"value\""
    c2 = Kconfig("tests/Kescape")
    c2.syms["STRING"].set_value("hello world")
    assert c2.syms["STRING"].config_string == 'CONFIG_STRING="hello world"\n'

    # String with characters needing escaping
    c2.syms["STRING"].set_value('a"b\\c')
    assert c2.syms["STRING"].config_string == 'CONFIG_STRING="a\\"b\\\\c"\n'

    # Int symbol: "CONFIG_...=value"
    c3 = Kconfig("tests/Krange", warn=False)
    c3.syms["INT_RANGE_10_20"].set_value("15")
    assert c3.syms["INT_RANGE_10_20"].config_string == "CONFIG_INT_RANGE_10_20=15\n"

    # Hex symbol: "CONFIG_...=value"
    c3.syms["HEX_RANGE_10_20"].set_value("0x15")
    assert c3.syms["HEX_RANGE_10_20"].config_string == "CONFIG_HEX_RANGE_10_20=0x15\n"


# -- Kconfig.missing_syms ---------------------------------------------------


def test_missing_syms():
    c = Kconfig("tests/Kappend", warn=False)

    # Initially empty
    assert c.missing_syms == []

    # Write configs with unknown symbols
    with tempfile.NamedTemporaryFile(mode="w", suffix=".config", delete=False) as f:
        f.write("CONFIG_UNKNOWN_A=y\n")
        f.write("CONFIG_UNKNOWN_B=42\n")
        tmppath = f.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".config", delete=False) as f:
        f.write("CONFIG_UNKNOWN_C=m\n")
        tmppath2 = f.name

    try:
        c.load_config(tmppath)
        assert ("UNKNOWN_A", "y") in c.missing_syms
        assert ("UNKNOWN_B", "42") in c.missing_syms
        assert len(c.missing_syms) == 2

        # replace=True (default) clears missing_syms before loading
        c.load_config(tmppath2)
        assert c.missing_syms == [("UNKNOWN_C", "m")]

        # replace=False appends to missing_syms
        c.load_config(tmppath, replace=False)
        assert ("UNKNOWN_C", "m") in c.missing_syms
        assert ("UNKNOWN_A", "y") in c.missing_syms
        assert ("UNKNOWN_B", "42") in c.missing_syms
        assert len(c.missing_syms) == 3
    finally:
        os.unlink(tmppath)
        os.unlink(tmppath2)
