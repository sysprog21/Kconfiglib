# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Symbol tests: visibility, assignable,
# object relations, hex/int ranges, defconfig_filename, mainmenu_text,
# user_value, is_menuconfig, option env, defined/undefined, Symbol.choice,
# and is_allnoconfig_y.

import os

import pytest

from kconfiglib import Kconfig, MENU, HEX
from conftest import (
    verify_value,
    assign_and_verify_value,
    assign_and_verify,
    assign_and_verify_user_value,
)

# -- visibility -------------------------------------------------------------


def test_visibility():
    c = Kconfig("tests/Kvisibility")

    def verify_visibility(item, no_module_vis, module_vis):
        c.modules.set_value(0)
        assert (
            item.visibility == no_module_vis
        ), f"{item.name} visibility without modules"

        c.modules.set_value(2)
        assert item.visibility == module_vis, f"{item.name} visibility with modules"

    # Symbol visibility

    verify_visibility(c.syms["NO_PROMPT"], 0, 0)
    verify_visibility(c.syms["BOOL_N"], 0, 0)
    verify_visibility(c.syms["BOOL_M"], 0, 2)
    verify_visibility(c.syms["BOOL_MOD"], 2, 2)
    verify_visibility(c.syms["BOOL_Y"], 2, 2)
    verify_visibility(c.syms["TRISTATE_M"], 0, 1)
    verify_visibility(c.syms["TRISTATE_MOD"], 2, 1)
    verify_visibility(c.syms["TRISTATE_Y"], 2, 2)
    verify_visibility(c.syms["BOOL_IF_N"], 0, 0)
    verify_visibility(c.syms["BOOL_IF_M"], 0, 2)
    verify_visibility(c.syms["BOOL_IF_Y"], 2, 2)
    verify_visibility(c.syms["BOOL_MENU_N"], 0, 0)
    verify_visibility(c.syms["BOOL_MENU_M"], 0, 2)
    verify_visibility(c.syms["BOOL_MENU_Y"], 2, 2)
    verify_visibility(c.syms["BOOL_CHOICE_N"], 0, 0)

    # Non-tristate symbols in tristate choices are only visible if the choice
    # is in y mode

    # The choice can't be brought to y mode because of the 'if m'
    verify_visibility(c.syms["BOOL_CHOICE_M"], 0, 0)
    c.syms["BOOL_CHOICE_M"].choice.set_value(2)
    verify_visibility(c.syms["BOOL_CHOICE_M"], 0, 0)

    # The choice gets y mode only when running without modules, because it
    # defaults to m mode
    verify_visibility(c.syms["BOOL_CHOICE_Y"], 2, 0)
    c.syms["BOOL_CHOICE_Y"].choice.set_value(2)
    # When set to y mode, the choice symbol becomes visible both with and
    # without modules
    verify_visibility(c.syms["BOOL_CHOICE_Y"], 2, 2)

    verify_visibility(c.syms["TRISTATE_IF_N"], 0, 0)
    verify_visibility(c.syms["TRISTATE_IF_M"], 0, 1)
    verify_visibility(c.syms["TRISTATE_IF_Y"], 2, 2)
    verify_visibility(c.syms["TRISTATE_MENU_N"], 0, 0)
    verify_visibility(c.syms["TRISTATE_MENU_M"], 0, 1)
    verify_visibility(c.syms["TRISTATE_MENU_Y"], 2, 2)
    verify_visibility(c.syms["TRISTATE_CHOICE_N"], 0, 0)
    verify_visibility(c.syms["TRISTATE_CHOICE_M"], 0, 1)
    verify_visibility(c.syms["TRISTATE_CHOICE_Y"], 2, 2)

    verify_visibility(c.named_choices["BOOL_CHOICE_N"], 0, 0)
    verify_visibility(c.named_choices["BOOL_CHOICE_M"], 0, 2)
    verify_visibility(c.named_choices["BOOL_CHOICE_Y"], 2, 2)
    verify_visibility(c.named_choices["TRISTATE_CHOICE_N"], 0, 0)
    verify_visibility(c.named_choices["TRISTATE_CHOICE_M"], 0, 1)
    verify_visibility(c.named_choices["TRISTATE_CHOICE_Y"], 2, 2)

    verify_visibility(c.named_choices["TRISTATE_CHOICE_IF_M_AND_Y"], 0, 1)
    verify_visibility(c.named_choices["TRISTATE_CHOICE_MENU_N_AND_Y"], 0, 0)

    # Verify that 'visible if' visibility gets propagated to prompts

    verify_visibility(c.syms["VISIBLE_IF_N"], 0, 0)
    verify_visibility(c.syms["VISIBLE_IF_M"], 0, 1)
    verify_visibility(c.syms["VISIBLE_IF_Y"], 2, 2)
    verify_visibility(c.syms["VISIBLE_IF_M_2"], 0, 1)

    # Verify that string/int/hex symbols with m visibility accept a user value

    assign_and_verify(c, "STRING_m", "foo bar")
    assign_and_verify(c, "INT_m", "123")
    assign_and_verify(c, "HEX_m", "0x123")


# -- .assignable ------------------------------------------------------------


def test_assignable():
    c = Kconfig("tests/Kassignable")

    def verify_assignable_imp(item, assignable_no_modules, assignable_modules):
        for modules_val, assignable in (
            (0, assignable_no_modules),
            (2, assignable_modules),
        ):
            c.modules.set_value(modules_val)
            module_msg = "without modules" if modules_val == 0 else "with modules"

            assert item.assignable == assignable, f"{item.name} assignable {module_msg}"

            # Verify that the values can actually be assigned too
            for val in item.assignable:
                item.set_value(val)
                assert item.tri_value == val, f"{item.name} set to {val} {module_msg}"

    def verify_assignable(sym_name, assignable_no_modules, assignable_modules):
        verify_assignable_imp(
            c.syms[sym_name], assignable_no_modules, assignable_modules
        )

    def verify_const_unassignable(sym_name):
        verify_assignable_imp(c.const_syms[sym_name], (), ())

    # Things that shouldn't be .assignable
    verify_const_unassignable("n")
    verify_const_unassignable("m")
    verify_const_unassignable("y")
    verify_const_unassignable("const")
    verify_assignable("UNDEFINED", (), ())
    verify_assignable("NO_PROMPT", (), ())
    verify_assignable("STRING", (), ())
    verify_assignable("INT", (), ())
    verify_assignable("HEX", (), ())

    # Non-selected symbols
    verify_assignable("Y_VIS_BOOL", (0, 2), (0, 2))
    verify_assignable("M_VIS_BOOL", (), (0, 2))  # Vis. promoted
    verify_assignable("N_VIS_BOOL", (), ())
    verify_assignable("Y_VIS_TRI", (0, 2), (0, 1, 2))
    verify_assignable("M_VIS_TRI", (), (0, 1))
    verify_assignable("N_VIS_TRI", (), ())

    # Symbols selected to y
    verify_assignable("Y_SEL_Y_VIS_BOOL", (2,), (2,))
    verify_assignable("Y_SEL_M_VIS_BOOL", (), (2,))  # Vis. promoted
    verify_assignable("Y_SEL_N_VIS_BOOL", (), ())
    verify_assignable("Y_SEL_Y_VIS_TRI", (2,), (2,))
    verify_assignable("Y_SEL_M_VIS_TRI", (), (2,))
    verify_assignable("Y_SEL_N_VIS_TRI", (), ())

    # Symbols selected to m
    verify_assignable("M_SEL_Y_VIS_BOOL", (2,), (2,))  # Value promoted
    verify_assignable("M_SEL_M_VIS_BOOL", (), (2,))  # Vis./value promoted
    verify_assignable("M_SEL_N_VIS_BOOL", (), ())
    verify_assignable("M_SEL_Y_VIS_TRI", (2,), (1, 2))
    verify_assignable("M_SEL_M_VIS_TRI", (), (1,))
    verify_assignable("M_SEL_N_VIS_TRI", (), ())

    # Symbols implied to y
    verify_assignable("Y_IMP_Y_VIS_BOOL", (0, 2), (0, 2))
    verify_assignable("Y_IMP_M_VIS_BOOL", (), (0, 2))  # Vis. promoted
    verify_assignable("Y_IMP_N_VIS_BOOL", (), ())
    verify_assignable("Y_IMP_Y_VIS_TRI", (0, 2), (0, 2))  # m removed by imply
    verify_assignable("Y_IMP_M_VIS_TRI", (), (0, 2))  # m promoted to y by imply
    verify_assignable("Y_IMP_N_VIS_TRI", (), ())

    # Symbols implied to m (never affects assignable values)
    verify_assignable("M_IMP_Y_VIS_BOOL", (0, 2), (0, 2))
    verify_assignable("M_IMP_M_VIS_BOOL", (), (0, 2))  # Vis. promoted
    verify_assignable("M_IMP_N_VIS_BOOL", (), ())
    verify_assignable("M_IMP_Y_VIS_TRI", (0, 2), (0, 1, 2))
    verify_assignable("M_IMP_M_VIS_TRI", (), (0, 1))
    verify_assignable("M_IMP_N_VIS_TRI", (), ())

    # Symbols in y-mode choice
    verify_assignable("Y_CHOICE_BOOL", (2,), (2,))
    verify_assignable("Y_CHOICE_TRISTATE", (2,), (2,))
    verify_assignable("Y_CHOICE_N_VIS_TRISTATE", (), ())

    # Symbols in m/y-mode choice, starting out in m mode, or y mode when
    # running without modules
    verify_assignable("MY_CHOICE_BOOL", (2,), ())
    verify_assignable("MY_CHOICE_TRISTATE", (2,), (0, 1))
    verify_assignable("MY_CHOICE_N_VIS_TRISTATE", (), ())

    c.named_choices["MY_CHOICE"].set_value(2)

    # Symbols in m/y-mode choice, now in y mode
    verify_assignable("MY_CHOICE_BOOL", (2,), (2,))
    verify_assignable("MY_CHOICE_TRISTATE", (2,), (2,))
    verify_assignable("MY_CHOICE_N_VIS_TRISTATE", (), ())

    def verify_choice_assignable(
        choice_name, assignable_no_modules, assignable_modules
    ):
        verify_assignable_imp(
            c.named_choices[choice_name], assignable_no_modules, assignable_modules
        )

    # Choices with various possible modes
    verify_choice_assignable("Y_CHOICE", (2,), (2,))
    verify_choice_assignable("MY_CHOICE", (2,), (1, 2))
    verify_choice_assignable("NMY_CHOICE", (0, 2), (0, 1, 2))
    verify_choice_assignable("NY_CHOICE", (0, 2), (0, 2))
    verify_choice_assignable("NM_CHOICE", (), (0, 1))
    verify_choice_assignable("M_CHOICE", (), (1,))
    verify_choice_assignable("N_CHOICE", (), ())


# -- object relations -------------------------------------------------------


def test_object_relations():
    c = Kconfig("tests/Krelation")

    assert (
        c.syms["A"].nodes[0].parent is c.top_node
    ), "A's parent should be the top node"

    assert (
        c.syms["B"].nodes[0].parent.item is c.named_choices["CHOICE_1"]
    ), "B's parent should be the first choice"

    assert (
        c.syms["C"].nodes[0].parent.item is c.syms["B"]
    ), "C's parent should be B (due to auto menus)"

    assert c.syms["E"].nodes[0].parent.item == MENU, "E's parent should be a menu"

    assert (
        c.syms["E"].nodes[0].parent.parent is c.top_node
    ), "E's grandparent should be the top node"

    assert (
        c.syms["G"].nodes[0].parent.item is c.named_choices["CHOICE_2"]
    ), "G's parent should be the second choice"

    assert (
        c.syms["G"].nodes[0].parent.parent.item == MENU
    ), "G's grandparent should be a menu"


# -- hex/int ranges ---------------------------------------------------------


def test_ranges():
    c = Kconfig("tests/Krange", warn=False)

    for sym_name in "HEX_NO_RANGE", "INT_NO_RANGE", "HEX_40", "INT_40":
        assert not c.syms[sym_name].ranges, f"{sym_name} should not have ranges"

    for sym_name in (
        "HEX_ALL_RANGES_DISABLED",
        "INT_ALL_RANGES_DISABLED",
        "HEX_RANGE_10_20_LOW_DEFAULT",
        "INT_RANGE_10_20_LOW_DEFAULT",
    ):
        assert c.syms[sym_name].ranges, f"{sym_name} should have ranges"

    # hex/int symbols without defaults should get no default value
    verify_value(c, "HEX_NO_RANGE", "")
    verify_value(c, "INT_NO_RANGE", "")
    # And neither if all ranges are disabled
    verify_value(c, "HEX_ALL_RANGES_DISABLED", "")
    verify_value(c, "INT_ALL_RANGES_DISABLED", "")
    # Make sure they are assignable though, and test that the form of the user
    # value is reflected in the value for hex symbols
    assign_and_verify(c, "HEX_NO_RANGE", "0x123")
    assign_and_verify(c, "HEX_NO_RANGE", "123")
    assign_and_verify(c, "INT_NO_RANGE", "123")

    # Defaults outside of the valid range should be clamped
    verify_value(c, "HEX_RANGE_10_20_LOW_DEFAULT", "0x10")
    verify_value(c, "HEX_RANGE_10_20_HIGH_DEFAULT", "0x20")
    verify_value(c, "INT_RANGE_10_20_LOW_DEFAULT", "10")
    verify_value(c, "INT_RANGE_10_20_HIGH_DEFAULT", "20")
    # Defaults inside the valid range should be preserved. For hex symbols,
    # they should additionally use the same form as in the assignment.
    verify_value(c, "HEX_RANGE_10_20_OK_DEFAULT", "0x15")
    verify_value(c, "HEX_RANGE_10_20_OK_DEFAULT_ALTERNATE", "15")
    verify_value(c, "INT_RANGE_10_20_OK_DEFAULT", "15")

    # hex/int symbols with no defaults but valid ranges should default to the
    # lower end of the range if it's > 0
    verify_value(c, "HEX_RANGE_10_20", "0x10")
    verify_value(c, "HEX_RANGE_0_10", "")
    verify_value(c, "INT_RANGE_10_20", "10")
    verify_value(c, "INT_RANGE_0_10", "")
    verify_value(c, "INT_RANGE_NEG_10_10", "")

    # User values and dependent ranges

    # Avoid warnings for assigning values outside the active range
    c.warn = False

    def verify_range(sym_name, low, high, default):
        # Verifies that all values in the range low-high can be assigned,
        # and that assigning values outside the range reverts the value back to
        # default (None if it should revert back to "").

        is_hex = c.syms[sym_name].type == HEX

        for i in range(low, high + 1):
            assign_and_verify_user_value(c, sym_name, str(i), str(i), True)
            if is_hex:
                # The form of the user value should be preserved for hex
                # symbols
                assign_and_verify_user_value(c, sym_name, hex(i), hex(i), True)

        # Verify that assigning a user value just outside the range causes
        # defaults to be used

        if default is None:
            default_str = ""
        elif is_hex:
            default_str = hex(default)
        else:
            default_str = str(default)

        if is_hex:
            too_low_str = hex(low - 1)
            too_high_str = hex(high + 1)
        else:
            too_low_str = str(low - 1)
            too_high_str = str(high + 1)

        assign_and_verify_value(c, sym_name, too_low_str, default_str)
        assign_and_verify_value(c, sym_name, too_high_str, default_str)

    verify_range("HEX_RANGE_10_20_LOW_DEFAULT", 0x10, 0x20, 0x10)
    verify_range("HEX_RANGE_10_20_HIGH_DEFAULT", 0x10, 0x20, 0x20)
    verify_range("HEX_RANGE_10_20_OK_DEFAULT", 0x10, 0x20, 0x15)

    verify_range("INT_RANGE_10_20_LOW_DEFAULT", 10, 20, 10)
    verify_range("INT_RANGE_10_20_HIGH_DEFAULT", 10, 20, 20)
    verify_range("INT_RANGE_10_20_OK_DEFAULT", 10, 20, 15)

    verify_range("HEX_RANGE_10_20", 0x10, 0x20, 0x10)

    verify_range("INT_RANGE_10_20", 10, 20, 10)
    verify_range("INT_RANGE_0_10", 0, 10, None)
    verify_range("INT_RANGE_NEG_10_10", -10, 10, None)

    # Dependent ranges

    verify_value(c, "HEX_40", "40")
    verify_value(c, "INT_40", "40")

    c.syms["HEX_RANGE_10_20"].unset_value()
    c.syms["INT_RANGE_10_20"].unset_value()
    verify_value(c, "HEX_RANGE_10_40_DEPENDENT", "0x10")
    verify_value(c, "INT_RANGE_10_40_DEPENDENT", "10")
    c.syms["HEX_RANGE_10_20"].set_value("15")
    c.syms["INT_RANGE_10_20"].set_value("15")
    verify_value(c, "HEX_RANGE_10_40_DEPENDENT", "0x15")
    verify_value(c, "INT_RANGE_10_40_DEPENDENT", "15")
    c.unset_values()
    verify_range("HEX_RANGE_10_40_DEPENDENT", 0x10, 0x40, 0x10)
    verify_range("INT_RANGE_10_40_DEPENDENT", 10, 40, 10)

    # Ranges and symbols defined in multiple locations

    verify_value(c, "INACTIVE_RANGE", "2")
    verify_value(c, "ACTIVE_RANGE", "1")


# -- defconfig_filename -----------------------------------------------------


def test_defconfig_filename(monkeypatch):
    # The Kconfig test-data files (Kdefconfig_existent, etc.) contain hardcoded
    # "Kconfiglib/tests/..." paths.  Compat tests run from a kernel tree root
    # where those paths resolve.  Running from the project root we need a
    # "Kconfiglib" symlink pointing here.
    kconfiglib_link = os.path.join(os.getcwd(), "Kconfiglib")
    created_link = False
    if not os.path.lexists(kconfiglib_link):
        try:
            os.symlink(".", kconfiglib_link)
        except OSError:
            pytest.skip("os.symlink() not supported on this platform")
        created_link = True

    try:
        c = Kconfig("tests/empty")
        assert (
            c.defconfig_filename is None
        ), "defconfig_filename should be None with no defconfig_list symbol"

        c = Kconfig("tests/Kdefconfig_nonexistent")
        assert (
            c.defconfig_filename is None
        ), "defconfig_filename should be None when no listed files exist"

        # Referenced in Kdefconfig_existent(_but_n)
        monkeypatch.setenv("FOO", "defconfig_2")

        c = Kconfig("tests/Kdefconfig_existent_but_n")
        assert (
            c.defconfig_filename is None
        ), "defconfig_filename should be None when all default conditions are n"

        c = Kconfig("tests/Kdefconfig_existent")
        assert (
            c.defconfig_filename == "Kconfiglib/tests/defconfig_2"
        ), "defconfig_filename should return Kconfiglib/tests/defconfig_2"

        # Should also look relative to $srctree if the specified defconfig is a
        # relative path and can't be opened

        c = Kconfig("tests/Kdefconfig_srctree")
        assert (
            c.defconfig_filename == "Kconfiglib/tests/defconfig_2"
        ), "defconfig_filename gave wrong file with $srctree unset"

        monkeypatch.setenv("srctree", "Kconfiglib/tests")
        c = Kconfig("Kdefconfig_srctree")
        assert (
            c.defconfig_filename == "Kconfiglib/tests/sub/defconfig_in_sub"
        ), "defconfig_filename gave wrong file with $srctree set"

        monkeypatch.delenv("srctree", raising=False)
    finally:
        if created_link:
            os.remove(kconfiglib_link)


# -- mainmenu_text ----------------------------------------------------------


def test_mainmenu_text(monkeypatch):
    c = Kconfig("tests/empty")
    assert (
        c.mainmenu_text == "Main menu"
    ), "An empty Kconfig should get a default main menu prompt"

    # Expanded in the mainmenu text
    monkeypatch.setenv("FOO", "bar baz")
    c = Kconfig("tests/Kmainmenu")
    assert c.mainmenu_text == "---bar baz---", "Wrong mainmenu text"


# -- user_value -------------------------------------------------------------


def test_user_value():
    # References undefined env. var. Disable warnings.
    c = Kconfig("tests/Kmisc", warn=False)

    syms = [c.syms[name] for name in ("BOOL", "TRISTATE", "STRING", "INT", "HEX")]

    for sym in syms:
        assert sym.user_value is None, f"{sym.name} initial user_value"

    # Assign valid values for the types

    assign_and_verify_user_value(c, "BOOL", 0, 0, True)
    assign_and_verify_user_value(c, "BOOL", 2, 2, True)
    assign_and_verify_user_value(c, "TRISTATE", 0, 0, True)
    assign_and_verify_user_value(c, "TRISTATE", 1, 1, True)
    assign_and_verify_user_value(c, "TRISTATE", 2, 2, True)
    assign_and_verify_user_value(c, "STRING", "foo bar", "foo bar", True)
    assign_and_verify_user_value(c, "INT", "123", "123", True)
    assign_and_verify_user_value(c, "HEX", "0x123", "0x123", True)

    # Assign invalid values for the types. They should retain their old user
    # value.

    assign_and_verify_user_value(c, "BOOL", 1, 2, False)
    assign_and_verify_user_value(c, "BOOL", "foo", 2, False)
    assign_and_verify_user_value(c, "BOOL", "1", 2, False)
    assign_and_verify_user_value(c, "TRISTATE", "foo", 2, False)
    assign_and_verify_user_value(c, "TRISTATE", "1", 2, False)
    assign_and_verify_user_value(c, "STRING", 0, "foo bar", False)
    assign_and_verify_user_value(c, "INT", "foo", "123", False)
    assign_and_verify_user_value(c, "INT", 0, "123", False)
    assign_and_verify_user_value(c, "HEX", "foo", "0x123", False)
    assign_and_verify_user_value(c, "HEX", 0, "0x123", False)
    assign_and_verify_user_value(c, "HEX", "-0x1", "0x123", False)

    for s in syms:
        s.unset_value()
        assert s.user_value is None, f"{s.name} user_value after reset"


# -- is_menuconfig ----------------------------------------------------------


def test_is_menuconfig():
    c = Kconfig("tests/Kmenuconfig")

    for not_menuconfig in (
        c.syms["NOT_MENUCONFIG_1"].nodes[0],
        c.syms["NOT_MENUCONFIG_2"].nodes[0],
        c.syms["MENUCONFIG_MULTI_DEF"].nodes[0],
        c.syms["COMMENT_HOOK"].nodes[0].next,
    ):
        assert not not_menuconfig.is_menuconfig, f"{not_menuconfig} is_menuconfig"

    for menuconfig in (
        c.top_node,
        c.syms["MENUCONFIG_1"].nodes[0],
        c.syms["MENUCONFIG_MULTI_DEF"].nodes[1],
        c.syms["MENU_HOOK"].nodes[0].next,
        c.syms["CHOICE_HOOK"].nodes[0].next,
    ):
        assert menuconfig.is_menuconfig, f"{menuconfig} is_menuconfig"


# -- option env semantics ---------------------------------------------------


def test_option_env(monkeypatch):
    monkeypatch.setenv("ENV_VAR", "ENV_VAR value")

    # References undefined env. var., so disable warnings
    c = Kconfig("tests/Kmisc", warn=False)

    # Verify that 'option env' is treated like a default
    verify_value(c, "FROM_ENV", "ENV_VAR value")
    verify_value(c, "FROM_ENV_MISSING", "missing")
    verify_value(c, "FROM_ENV_WEIRD", "weird")


# -- defined vs undefined symbols -------------------------------------------


def test_defined_undefined():
    # References undefined env. var., so disable warnings
    c = Kconfig("tests/Kmisc", warn=False)

    for name in "A", "B", "C", "D", "BOOL", "TRISTATE", "STRING", "INT", "HEX":
        assert c.syms[name].nodes, f"{name} should be defined"

    for name in "NOT_DEFINED_1", "NOT_DEFINED_2", "NOT_DEFINED_3", "NOT_DEFINED_4":
        assert not c.syms[name].nodes, f"{name} should not be defined"


# -- Symbol.choice ----------------------------------------------------------


def test_symbol_choice():
    # References undefined env. var., so disable warnings
    c = Kconfig("tests/Kmisc", warn=False)

    for name in "A", "B", "C", "D":
        assert c.syms[name].choice is not None, f"{name} should be choice symbol"

    for name in (
        "Q1",
        "Q2",
        "Q3",
        "BOOL",
        "TRISTATE",
        "STRING",
        "INT",
        "HEX",
        "FROM_ENV",
        "FROM_ENV_MISSING",
        "NOT_DEFINED_1",
        "NOT_DEFINED_2",
        "NOT_DEFINED_3",
        "NOT_DEFINED_4",
    ):
        assert c.syms[name].choice is None, f"{name} should not be choice symbol"


# -- is_allnoconfig_y -------------------------------------------------------


def test_is_allnoconfig_y():
    # References undefined env. var., so disable warnings
    c = Kconfig("tests/Kmisc", warn=False)

    assert not c.syms["NOT_ALLNOCONFIG_Y"].is_allnoconfig_y, "NOT_ALLNOCONFIG_Y flag"
    assert c.syms["ALLNOCONFIG_Y"].is_allnoconfig_y, "ALLNOCONFIG_Y flag"


# -- user_loc ---------------------------------------------------------------


def test_user_loc():
    # References undefined env. var., so disable warnings
    c = Kconfig("tests/Kmisc", warn=False)

    sym = c.syms["STRING"]

    # Before any assignment, user_loc should be None
    assert sym.user_loc is None, "user_loc should be None before set_value()"

    # After set_value() with an explicit loc, user_loc reflects that loc
    sym.set_value("hello", loc=("test_file", 42))
    assert sym.user_loc == (
        "test_file",
        42,
    ), "user_loc should reflect the loc passed to set_value()"

    # After set_value() without loc, user_loc is None (the default)
    sym.set_value("world")
    assert (
        sym.user_loc is None
    ), "user_loc should be None when set_value() called without loc"

    # After set_value() with loc again
    sym.set_value("again", loc=("another_file", 7))
    assert sym.user_loc == ("another_file", 7)

    # After unset_value(), user_loc should be None
    sym.unset_value()
    assert sym.user_loc is None, "user_loc should be None after unset_value()"
