# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Imply and choice semantics tests.

from kconfiglib import Kconfig, BOOL, TRISTATE
from conftest import (
    verify_value,
    assign_and_verify,
    assign_and_verify_value,
)

# ---------------------------------------------------------------------------
# Imply semantics
# ---------------------------------------------------------------------------


def test_imply_default_values():
    c = Kconfig("tests/Kimply")

    verify_value(c, "IMPLY_DIRECT_DEPS", "y")
    verify_value(c, "UNMET_DIRECT_1", "n")
    verify_value(c, "UNMET_DIRECT_2", "n")
    verify_value(c, "UNMET_DIRECT_3", "n")
    verify_value(c, "MET_DIRECT_1", "y")
    verify_value(c, "MET_DIRECT_2", "y")
    verify_value(c, "MET_DIRECT_3", "y")
    verify_value(c, "MET_DIRECT_4", "y")
    verify_value(c, "IMPLY_COND", "y")
    verify_value(c, "IMPLIED_N_COND", "n")
    verify_value(c, "IMPLIED_M_COND", "m")
    verify_value(c, "IMPLIED_Y_COND", "y")
    verify_value(c, "IMPLY_N_1", "n")
    verify_value(c, "IMPLY_N_2", "n")
    verify_value(c, "IMPLIED_FROM_N_1", "n")
    verify_value(c, "IMPLIED_FROM_N_2", "n")
    verify_value(c, "IMPLY_M", "m")
    verify_value(c, "IMPLIED_M", "m")
    verify_value(c, "IMPLIED_M_BOOL", "y")
    verify_value(c, "IMPLY_M_TO_Y", "y")
    verify_value(c, "IMPLIED_M_TO_Y", "y")


def test_imply_user_values():
    c = Kconfig("tests/Kimply")

    # Verify that IMPLIED_TRISTATE is invalidated if the direct
    # dependencies change

    assign_and_verify(c, "IMPLY", 2)
    assign_and_verify(c, "DIRECT_DEP", 2)
    verify_value(c, "IMPLIED_TRISTATE", 2)
    assign_and_verify(c, "DIRECT_DEP", 0)
    verify_value(c, "IMPLIED_TRISTATE", 0)
    # Set back for later tests
    assign_and_verify(c, "DIRECT_DEP", 2)

    # Verify that IMPLIED_TRISTATE can be set to anything when IMPLY has value
    # n, and that it gets the value n by default (for non-imply-related
    # reasons)

    assign_and_verify(c, "IMPLY", 0)
    assign_and_verify(c, "IMPLIED_TRISTATE", 0)
    assign_and_verify(c, "IMPLIED_TRISTATE", 1)
    assign_and_verify(c, "IMPLIED_TRISTATE", 2)
    c.syms["IMPLIED_TRISTATE"].unset_value()
    verify_value(c, "IMPLIED_TRISTATE", "n")

    # Same as above for m. Anything still goes, but m by default now.

    assign_and_verify(c, "IMPLY", 1)
    assign_and_verify(c, "IMPLIED_TRISTATE", 0)
    assign_and_verify(c, "IMPLIED_TRISTATE", 1)
    assign_and_verify(c, "IMPLIED_TRISTATE", 2)
    c.syms["IMPLIED_TRISTATE"].unset_value()
    verify_value(c, "IMPLIED_TRISTATE", 1)

    # Same as above for y. Only n and y should be accepted. m gets promoted to
    # y. Default should be y.

    assign_and_verify(c, "IMPLY", 2)
    assign_and_verify(c, "IMPLIED_TRISTATE", 0)
    assign_and_verify_value(c, "IMPLIED_TRISTATE", 1, 2)
    assign_and_verify(c, "IMPLIED_TRISTATE", 2)
    c.syms["IMPLIED_TRISTATE"].unset_value()
    verify_value(c, "IMPLIED_TRISTATE", 2)

    # Being implied to either m or y should give a bool the value y

    c.syms["IMPLY"].unset_value()
    verify_value(c, "IMPLIED_BOOL", 0)
    assign_and_verify(c, "IMPLY", 0)
    verify_value(c, "IMPLIED_BOOL", 0)
    assign_and_verify(c, "IMPLY", 1)
    verify_value(c, "IMPLIED_BOOL", 2)
    assign_and_verify(c, "IMPLY", 2)
    verify_value(c, "IMPLIED_BOOL", 2)

    # A bool implied to m or y can take the values n and y

    c.syms["IMPLY"].set_value(1)
    assign_and_verify(c, "IMPLIED_BOOL", 0)
    assign_and_verify(c, "IMPLIED_BOOL", 2)

    c.syms["IMPLY"].set_value(2)
    assign_and_verify(c, "IMPLIED_BOOL", 0)
    assign_and_verify(c, "IMPLIED_BOOL", 2)


# ---------------------------------------------------------------------------
# Choice semantics
# ---------------------------------------------------------------------------


def test_choice_types():
    c = Kconfig("tests/Kchoice", warn=False)

    for name in "BOOL", "BOOL_OPT", "BOOL_M", "DEFAULTS":
        assert c.named_choices[name].orig_type == BOOL, f"choice {name} type"

    for name in "TRISTATE", "TRISTATE_OPT", "TRISTATE_M":
        assert c.named_choices[name].orig_type == TRISTATE, f"choice {name} type"


def test_choice_modes():
    c = Kconfig("tests/Kchoice", warn=False)

    def verify_mode(choice_name, no_modules_mode, modules_mode):
        choice = c.named_choices[choice_name]
        c.modules.set_value(0)
        assert (
            choice.tri_value == no_modules_mode
        ), f"{choice.name} mode without modules"
        c.modules.set_value(2)
        assert choice.tri_value == modules_mode, f"{choice.name} mode with modules"

    verify_mode("BOOL", 2, 2)
    verify_mode("BOOL_OPT", 0, 0)
    verify_mode("TRISTATE", 2, 1)
    verify_mode("TRISTATE_OPT", 0, 0)
    verify_mode("BOOL_M", 0, 2)
    verify_mode("TRISTATE_M", 0, 1)


def test_choice_defaults():
    c = Kconfig("tests/Kchoice", warn=False)

    choice = c.named_choices["DEFAULTS"]

    c.syms["TRISTATE_SYM"].set_value(0)
    assert choice.selection is c.syms["OPT_4"], "choice default with TRISTATE_SYM = n"

    c.syms["TRISTATE_SYM"].set_value(2)
    assert choice.selection is c.syms["OPT_2"], "choice default with TRISTATE_SYM = y"

    c.syms["OPT_1"].set_value(2)
    assert choice.selection is c.syms["OPT_1"], "user selection override"

    assert (
        c.named_choices["DEFAULTS_NOT_VISIBLE"].selection is c.syms["OPT_8"]
    ), "non-visible choice symbols default"


def test_choice_selection():
    c = Kconfig("tests/Kchoice", warn=False)

    def select_and_verify(sym):
        choice = sym.nodes[0].parent.item
        choice.set_value(2)
        sym.set_value(2)
        assert sym.choice.selection is sym, f"{sym.name} selected symbol"
        assert choice.user_selection is sym, f"{sym.name} user selection"
        assert sym.tri_value == 2, f"{sym.name} value when selected"
        assert sym.user_value == 2, f"{sym.name} user value when selected"
        for sibling in choice.syms:
            if sibling is not sym:
                assert sibling.tri_value == 0, f"{sibling.name} not selected"

    def select_and_verify_all(choice_name):
        choice = c.named_choices[choice_name]
        for sym in choice.syms:
            select_and_verify(sym)
        for sym in reversed(choice.syms):
            select_and_verify(sym)

    c.modules.set_value(2)

    select_and_verify_all("BOOL")
    select_and_verify_all("BOOL_OPT")
    select_and_verify_all("TRISTATE")
    select_and_verify_all("TRISTATE_OPT")
    # For BOOL_M, the mode should have been promoted
    select_and_verify_all("BOOL_M")


def test_choice_m_mode():
    c = Kconfig("tests/Kchoice", warn=False)
    tristate = c.named_choices["TRISTATE"]

    c.modules.set_value(2)
    tristate.set_value(1)

    assert (
        tristate.tri_value == 1
    ), "TRISTATE choice should have mode m after explicit mode assignment"

    # In v6.18, sym_calc_choice() in scripts/kconfig/symbol.c (Linux)
    # always assigns y/n to visible members based on selection, regardless
    # of the choice's mode.  Setting a member to n (0) removes it from
    # default selection consideration; setting to y (2) makes it the user
    # selection.

    # Setting T_1 to n moves selection to T_2
    assign_and_verify_value(c, "T_1", 0, 0)
    # T_2 is now selected; setting it to n triggers step-4 fallback
    # (last visible member = T_2), so T_2 stays y
    assign_and_verify_value(c, "T_2", 0, 2)
    # Setting T_1 to y makes it the user selection
    c.syms["T_1"].set_value(2)
    verify_value(c, "T_1", 2)
    verify_value(c, "T_2", 0)
    # Setting T_2 to y makes it the user selection
    c.syms["T_2"].set_value(2)
    verify_value(c, "T_1", 0)
    verify_value(c, "T_2", 2)

    # Switching to y mode keeps T_2 as the user selection
    tristate.set_value(2)
    verify_value(c, "T_1", 0)
    verify_value(c, "T_2", 2)


def test_choice_no_explicit_type():
    c = Kconfig("tests/Kchoice", warn=False)

    assert (
        c.named_choices["NO_TYPE_BOOL"].orig_type == BOOL
    ), "Expected first choice without explicit type to have type bool"

    assert (
        c.named_choices["NO_TYPE_TRISTATE"].orig_type == TRISTATE
    ), "Expected second choice without explicit type to have type tristate"


def test_choice_symbol_types():
    c = Kconfig("tests/Kchoice", warn=False)

    for name in "MMT_1", "MMT_2", "MMT_4", "MMT_5":
        assert c.syms[name].orig_type == BOOL, f"{name} type"

    assert c.syms["MMT_3"].orig_type == TRISTATE, "MMT_3 type"


def test_choice_default_with_dep():
    c = Kconfig("tests/Kchoice", warn=False)
    choice = c.named_choices["DEFAULT_WITH_DEP"]

    assert choice.selection is c.syms["B"], "choice default with unsatisfied deps"

    c.syms["DEP"].set_value("y")
    assert choice.selection is c.syms["A"], "choice default with satisfied deps"

    c.syms["DEP"].set_value("n")
    assert choice.selection is c.syms["B"], "choice default with unsatisfied deps again"


def test_choice_weird_symbols():
    c = Kconfig("tests/Kchoice", warn=False)

    weird_choice = c.named_choices["WEIRD_SYMS"]

    def verify_is_normal_choice_symbol(name):
        sym = c.syms[name]
        assert (
            sym.choice is not None
            and sym in weird_choice.syms
            and sym.nodes[0].parent.item is weird_choice
        ), f"{sym.name} normal choice symbol"

    def verify_is_weird_choice_symbol(name):
        sym = c.syms[name]
        assert (
            sym.choice is None and sym not in weird_choice.syms
        ), f"{sym.name} weird choice symbol"

    verify_is_normal_choice_symbol("WS1")
    verify_is_weird_choice_symbol("WS2")
    verify_is_weird_choice_symbol("WS3")
    verify_is_weird_choice_symbol("WS4")
    verify_is_weird_choice_symbol("WS5")
    verify_is_normal_choice_symbol("WS6")
    verify_is_weird_choice_symbol("WS7")
    verify_is_weird_choice_symbol("WS8")
    verify_is_normal_choice_symbol("WS9")


def test_choice_optional_n_mode_selection():
    """Test that optional choices in n mode still compute a selection.

    In Linux's sym_calc_choice() (scripts/kconfig/symbol.c), the selection
    is computed for any choice with visible members regardless of the
    choice's own mode.  An optional choice with no user value has mode n,
    but visible members are still assigned y/n based on which one is
    selected (the default or first visible member).
    """
    c = Kconfig("tests/Kchoice", warn=False)

    # BOOL_OPT and TRISTATE_OPT are optional, default mode is n (no user
    # value, is_optional means base reverse dep is 0)
    for choice_name, member_prefix in [("BOOL_OPT", "BO_"), ("TRISTATE_OPT", "TO_")]:
        choice = c.named_choices[choice_name]
        assert choice.is_optional, f"{choice_name} should be optional"
        assert choice.tri_value == 0, f"{choice_name} should have mode n"

        # sym_calc_choice() picks a selection even in n mode
        assert (
            choice.selection is not None
        ), f"{choice_name} should still have a selection in n mode"

        # First visible member is selected (gets y), others get n
        first_sym = c.syms[member_prefix + "1"]
        assert (
            choice.selection is first_sym
        ), f"{choice_name} selection should be {first_sym.name}"
        assert first_sym.tri_value == 2, f"{first_sym.name} should be y (selected)"

        second_sym = c.syms[member_prefix + "2"]
        assert (
            second_sym.tri_value == 0
        ), f"{second_sym.name} should be n (not selected)"

        # All visible members have _write_to_conf set (SYMBOL_WRITE)
        for sym in choice.syms:
            if sym.visibility:
                assert sym._write_to_conf, f"{sym.name} should have _write_to_conf set"
