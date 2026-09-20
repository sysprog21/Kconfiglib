# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Row-rendering tests for menuconfig and guiconfig.
#
# _node_str()/_value_str()/_get_force_info() produce every line the user reads,
# they are the most branch-dense functions in either tool (complexity 14 in
# guiconfig), and nothing exercised them. They are pure functions of a MenuNode
# plus a few module globals, so they test directly -- no terminal, no Tk.
#
# The expected strings below were taken from the real functions and checked by
# hand against tests/Kuirender, which is built to reach every branch: each
# symbol type, pinned and unpinned values, select/imply annotations including
# the "+N" truncation, y-mode choices, empty versus non-empty menus, comments,
# and promptless symbols in show-all mode.

import pytest

import menuconfig
import uicommon
from conftest import named_menu, node
from kconfiglib import Kconfig


@pytest.fixture(scope="module")
def kconf():
    return Kconfig("tests/Kuirender", warn=False)


@pytest.fixture
def mc(kconf, monkeypatch):
    """menuconfig with its interface state set up for rendering."""
    state = menuconfig._State()
    state.kconf = kconf
    state.show_all = True
    state.show_name = False
    monkeypatch.setattr(menuconfig, "_s", state)
    return menuconfig


@pytest.fixture
def gc_(kconf, monkeypatch):
    """guiconfig with its module globals set up for rendering.

    Imported here rather than at the top of the module: guiconfig pulls in
    tkinter, which is an optional part of a Python installation. A hard import
    would turn a missing tkinter into a collection error that takes down the
    whole file, menuconfig tests included.
    """
    guiconfig = pytest.importorskip("guiconfig")
    monkeypatch.setattr(guiconfig, "_kconf", kconf, raising=False)
    monkeypatch.setattr(guiconfig, "_show_all", True, raising=False)
    monkeypatch.setattr(guiconfig, "_single_menu", False, raising=False)
    return guiconfig


@pytest.fixture
def ui(request):
    return request.getfixturevalue("mc" if request.param == "menuconfig" else "gc_")


# --- menuconfig._value_str: one case per branch -----------------------------


@pytest.mark.parametrize(
    "sym, expected",
    [
        ("BOOL_SYM", "[ ]"),
        ("MODULES", "[*]"),
        ("TRI_SYM", "< >"),
        ("IMPLIED", "<*>"),
        ("STR_SYM", "(hello)"),
        ("INT_SYM", "(7)"),
        ("HEX_SYM", "(0x1f)"),
        # Pinned to a single assignable value by a select
        ("SELECTED", "-*-"),
        # y-mode choice symbols
        ("CHOICE_A", "( )"),
        ("CHOICE_B", "(X)"),
    ],
)
def test_value_str(mc, kconf, sym, expected):
    assert mc._value_str(node(kconf, sym)) == expected


def test_value_str_is_empty_for_menus_and_comments(mc, kconf):
    assert mc._value_str(named_menu(kconf, "A menu")) == ""
    assert mc._value_str(kconf.comments[0]) == ""


# --- _get_force_info, in both tools -----------------------------------------


@pytest.mark.parametrize("ui", ("menuconfig", "guiconfig"), indirect=True)
@pytest.mark.parametrize(
    "sym, expected",
    [
        ("SELECTED", " [selected by SELECTOR]"),
        ("IMPLIED", " [implied by IMPLIER]"),
        # More than two sources is truncated with a count
        ("MANY_SELECTED", " [selected by SEL_A, SEL_B, +1]"),
        # Not forced by anything
        ("SELECTOR", None),
        # Not a bool/tristate
        ("STR_SYM", None),
    ],
)
def test_get_force_info(ui, kconf, sym, expected):
    assert ui._get_force_info(kconf.syms[sym]) == expected


# --- menuconfig._node_str ---------------------------------------------------


@pytest.mark.parametrize(
    "sym, expected",
    [
        ("BOOL_SYM", "[ ] A bool (NEW)"),
        ("TRI_SYM", "< > A tristate (NEW)"),
        ("STR_SYM", "(hello) A string (NEW)"),
        ("SELECTED", "-*- Selected one (NEW) [selected by SELECTOR]"),
        (
            "MANY_SELECTED",
            "-*- Selected by several (NEW) [selected by SEL_A, SEL_B, +1]",
        ),
        # Promptless symbols show their name instead, in show-all mode
        ("PROMPTLESS", "-*- <PROMPTLESS>"),
        # A menuconfig with visible children gets the enter arrow
        ("MENUCONFIG_SYM", "[*] A menuconfig (NEW)  --->"),
        # Choice symbols in a y-mode choice get no "(NEW)"
        ("CHOICE_B", "(X) Choice B"),
    ],
)
def test_menuconfig_node_str(mc, kconf, sym, expected):
    assert mc._node_str(node(kconf, sym)) == expected


def test_menuconfig_node_str_menus_and_comments(mc, kconf):
    assert mc._node_str(named_menu(kconf, "A menu")) == "    A menu  --->"
    # An empty menu is drawn with "----", since it cannot be entered
    assert mc._node_str(named_menu(kconf, "Empty menu")) == "    Empty menu  ----"
    assert mc._node_str(kconf.comments[0]) == "    *** A comment ***"


def test_menuconfig_node_str_y_mode_choice_shows_selection(mc, kconf):
    assert mc._node_str(kconf.choices[0].nodes[0]) == "    A choice (Choice B)  --->"


def test_menuconfig_show_name_appends_symbol_name(mc, kconf, monkeypatch):
    monkeypatch.setattr(mc._s, "show_name", True)
    assert mc._node_str(node(kconf, "BOOL_SYM")) == "[ ] <BOOL_SYM> A bool (NEW)"


def test_menuconfig_node_str_indents_inside_an_implicit_submenu(mc, kconf):
    """Children of a plain 'config' are indented; a 'menuconfig' owns the level.

    IMPLICIT_CHILD depends on IMPLICIT_PARENT, which puts it in the implicit
    submenu of a node that is not a menuconfig, so the indent applies.
    UNDER_MENUCONFIG sits under a real menuconfig and gets none.
    """
    indent = " " * mc._SUBMENU_INDENT
    assert (
        mc._node_str(node(kconf, "IMPLICIT_CHILD"))
        == f"[ ] {indent}Implicit child (NEW)"
    )
    assert not mc._node_str(node(kconf, "BOOL_SYM")).startswith("[ ] " + indent)
    assert not mc._node_str(node(kconf, "UNDER_MENUCONFIG")).startswith("[ ] " + indent)


# --- guiconfig._node_str ----------------------------------------------------
#
# Same tree, different conventions: no value prefix (the GUI draws an image
# instead), strings appended after a colon, int/hex still parenthesized.


@pytest.mark.parametrize(
    "sym, expected",
    [
        ("BOOL_SYM", "A bool (NEW)"),
        ("STR_SYM", "A string (NEW): hello"),
        ("INT_SYM", "(7) An int (NEW)"),
        ("HEX_SYM", "(0x1f) A hex (NEW)"),
        ("SELECTED", "Selected one (NEW) [selected by SELECTOR]"),
        ("PROMPTLESS", "<PROMPTLESS>"),
        ("CHOICE_B", "Choice B"),
    ],
)
def test_guiconfig_node_str(gc_, kconf, sym, expected):
    assert gc_._node_str(node(kconf, sym)) == expected


def test_guiconfig_node_str_comment_and_choice(gc_, kconf):
    assert gc_._node_str(kconf.comments[0]) == "*** A comment ***"
    assert gc_._node_str(kconf.choices[0].nodes[0]) == "A choice (Choice B)"


def test_guiconfig_single_menu_mode_adds_arrows(gc_, kconf, monkeypatch):
    """Only single-menu mode draws the enter arrows; tree mode never does."""
    n = node(kconf, "MENUCONFIG_SYM")
    assert gc_._node_str(n) == "A menuconfig (NEW)"

    monkeypatch.setattr(gc_, "_single_menu", True)
    assert gc_._node_str(n) == "A menuconfig (NEW)  --->"
    assert gc_._node_str(named_menu(kconf, "Empty menu")) == "Empty menu  ----"


def test_guiconfig_choice_sym_prompt_falls_back(gc_, kconf):
    """_choice_sym_prompt() falls back when the symbol isn't at that node."""
    choice_node = kconf.choices[0].nodes[0]
    sym = kconf.syms["CHOICE_B"]
    assert gc_._choice_sym_prompt(sym, choice_node) == "Choice B"
    # A node that is not this symbol's parent still yields some prompt
    assert gc_._choice_sym_prompt(sym, named_menu(kconf, "A menu")) == "Choice B"
    # A symbol with no prompt anywhere yields None
    assert gc_._choice_sym_prompt(kconf.syms["PROMPTLESS"], choice_node) is None


# --- what counts as changeable ----------------------------------------------
#
# These used to be parametrized over both tools, because each carried its own
# copy of changeable(). There is one copy now, in uicommon, so parametrizing
# would run the same function twice and drag tkinter in to do it.


@pytest.mark.parametrize(
    "sym, expected",
    [
        ("BOOL_SYM", True),
        ("STR_SYM", True),
        ("TRI_SYM", True),
        # Pinned to y by a select: nothing left to choose
        ("SELECTED", False),
        # No prompt, so not visible and not changeable
        ("PROMPTLESS", False),
    ],
)
def test_changeable(kconf, sym, expected):
    # 'is' rather than '==': changeable() is documented to return True/False,
    # and it used to leak the None from the end of an 'and' chain instead
    assert uicommon.changeable(node(kconf, sym)) is expected


def test_changeable_rejects_menus_and_comments(kconf):
    for n in (named_menu(kconf, "A menu"), kconf.comments[0]):
        assert uicommon.changeable(n) is False


# --- menuconfig._shown_nodes: what actually reaches the screen --------------


def test_shown_nodes_hides_promptless_symbols_until_show_all(mc, kconf, monkeypatch):
    """PROMPTLESS has no prompt, so it appears only in show-all mode."""
    monkeypatch.setattr(mc._s, "show_all", False)
    hidden = mc._shown_nodes(kconf.top_node)
    monkeypatch.setattr(mc._s, "show_all", True)
    shown = mc._shown_nodes(kconf.top_node)

    promptless = node(kconf, "PROMPTLESS")
    assert promptless not in hidden
    assert promptless in shown
    # show-all only ever adds
    assert set(hidden) < set(shown)


def test_shown_nodes_descends_into_a_menuconfig(mc, kconf, monkeypatch):
    monkeypatch.setattr(mc._s, "show_all", False)
    children = mc._shown_nodes(node(kconf, "MENUCONFIG_SYM"))
    assert children == [node(kconf, "UNDER_MENUCONFIG")]


def test_shown_nodes_of_an_empty_menu_is_empty(mc, kconf, monkeypatch):
    """This is what makes _node_str() draw "----" instead of "--->"."""
    monkeypatch.setattr(mc._s, "show_all", False)
    assert mc._shown_nodes(named_menu(kconf, "Empty menu")) == []
    assert mc._shown_nodes(named_menu(kconf, "A menu")) != []


def test_is_y_mode_choice_sym_returns_a_real_bool(kconf):
    """The predicate feeding changeable() must not leak a None."""
    assert uicommon.is_y_mode_choice_sym(kconf.syms["CHOICE_A"]) is True
    # Not a choice symbol at all
    assert uicommon.is_y_mode_choice_sym(kconf.syms["BOOL_SYM"]) is False
    # Not a Symbol at all
    assert uicommon.is_y_mode_choice_sym(kconf.choices[0]) is False
