# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Tests for Symbol/Choice/MenuNode __str__(), custom_str(), orig_*,
# and __repr__().

import pytest

from kconfiglib import Kconfig, expr_str
from conftest import verify_str

BRACKET_FMT = lambda sc: f"[{sc.name}]"


def verify_custom_str(item, expected):
    """Verify item.custom_str() with bracket formatter matches expected."""
    assert item.custom_str(BRACKET_FMT) == expected[1:-1]


def verify_deps(elms, dep_index, expected):
    """Join the expr_str of element[dep_index] across all elements."""
    assert " ".join(expr_str(elm[dep_index]) for elm in elms) == expected


@pytest.fixture
def kstr_config():
    """Load tests/Kstr with modules=m."""
    c = Kconfig("tests/Kstr", warn=False)
    c.modules.set_value(2)
    return c


@pytest.fixture
def krepr_config():
    """Load tests/Krepr."""
    return Kconfig("tests/Krepr", warn=False)


# -- Symbol.__str__() / custom_str() ----------------------------------------


class TestSymbolStr:
    @pytest.fixture(autouse=True)
    def _setup(self, kstr_config):
        self.c = kstr_config

    def test_undefined(self):
        assert str(self.c.syms["UNDEFINED"]) == ""

    def test_basic_no_prompt(self):
        # Blank help lines contain tab + two spaces; build explicitly to
        # prevent editors from stripping trailing whitespace.
        expected = (
            "config BASIC_NO_PROMPT\n"
            "\tbool\n"
            "\thelp\n"
            "\t  blah blah\n"
            "\t  \n"
            "\t    blah blah blah\n"
            "\t  \n"
            "\t   blah"
        )
        assert str(self.c.syms["BASIC_NO_PROMPT"]) == expected

    def test_basic_prompt(self):
        verify_str(
            self.c.syms["BASIC_PROMPT"],
            """
config BASIC_PROMPT
\tbool "basic"
""",
        )

    def test_advanced(self):
        verify_str(
            self.c.syms["ADVANCED"],
            """
config ADVANCED
\ttristate "prompt" if DEP
\tdefault DEFAULT_1
\tdefault DEFAULT_2 if DEP
\tselect SELECTED_1
\tselect SELECTED_2 if DEP
\timply IMPLIED_1
\timply IMPLIED_2 if DEP
\thelp
\t  first help text

config ADVANCED
\ttristate "prompt 2"

menuconfig ADVANCED
\ttristate "prompt 3"

config ADVANCED
\ttristate
\tdepends on (A || !B || (C && D) || !(E && F) || G = H || (I && !J && (K || L) && !(M || N) && O = P)) && DEP4 && DEP3
\thelp
\t  second help text

config ADVANCED
\ttristate "prompt 4" if VIS
\tdepends on DEP4 && DEP3
""",
        )

    def test_advanced_custom_str(self):
        verify_custom_str(
            self.c.syms["ADVANCED"],
            """
config ADVANCED
\ttristate "prompt" if [DEP]
\tdefault [DEFAULT_1]
\tdefault [DEFAULT_2] if [DEP]
\tselect [SELECTED_1]
\tselect [SELECTED_2] if [DEP]
\timply [IMPLIED_1]
\timply [IMPLIED_2] if [DEP]
\thelp
\t  first help text

config ADVANCED
\ttristate "prompt 2"

menuconfig ADVANCED
\ttristate "prompt 3"

config ADVANCED
\ttristate
\tdepends on ([A] || ![B] || ([C] && [D]) || !([E] && [F]) || [G] = [H] || ([I] && ![J] && ([K] || [L]) && !([M] || [N]) && [O] = [P])) && [DEP4] && [DEP3]
\thelp
\t  second help text

config ADVANCED
\ttristate "prompt 4" if [VIS]
\tdepends on [DEP4] && [DEP3]
""",
        )

    def test_only_direct_deps(self):
        verify_str(
            self.c.syms["ONLY_DIRECT_DEPS"],
            """
config ONLY_DIRECT_DEPS
\tint
\tdepends on DEP1 && DEP2
""",
        )

    def test_string(self):
        verify_str(
            self.c.syms["STRING"],
            """
config STRING
\tstring
\tdefault "foo"
\tdefault "bar" if DEP
\tdefault STRING2
\tdefault STRING3 if DEP
""",
        )

    def test_int(self):
        verify_str(
            self.c.syms["INT"],
            """
config INT
\tint
\trange 1 2
\trange FOO BAR
\trange BAZ QAZ if DEP
\tdefault 7 if DEP
""",
        )

    def test_hex(self):
        verify_str(
            self.c.syms["HEX"],
            """
config HEX
\thex
\trange 0x100 0x200
\trange FOO BAR
\trange BAZ QAZ if DEP
\tdefault 0x123
""",
        )

    def test_modules(self):
        verify_str(
            self.c.modules,
            """
config MODULES
\tbool "MODULES"
\toption modules
""",
        )

    def test_options(self):
        verify_str(
            self.c.syms["OPTIONS"],
            """
config OPTIONS
\toption allnoconfig_y
\toption defconfig_list
\toption env="ENV"
""",
        )

    def test_correct_prop_locs_bool(self):
        verify_str(
            self.c.syms["CORRECT_PROP_LOCS_BOOL"],
            """
config CORRECT_PROP_LOCS_BOOL
\tbool "prompt 1"
\tdefault DEFAULT_1
\tdefault DEFAULT_2
\tselect SELECT_1
\tselect SELECT_2
\timply IMPLY_1
\timply IMPLY_2
\tdepends on LOC_1
\thelp
\t  help 1

menuconfig CORRECT_PROP_LOCS_BOOL
\tbool "prompt 2"
\tdefault DEFAULT_3
\tdefault DEFAULT_4
\tselect SELECT_3
\tselect SELECT_4
\timply IMPLY_3
\timply IMPLY_4
\tdepends on LOC_2
\thelp
\t  help 2

config CORRECT_PROP_LOCS_BOOL
\tbool "prompt 3"
\tdefault DEFAULT_5
\tdefault DEFAULT_6
\tselect SELECT_5
\tselect SELECT_6
\timply IMPLY_5
\timply IMPLY_6
\tdepends on LOC_3
\thelp
\t  help 2
""",
        )

    def test_correct_prop_locs_int(self):
        verify_str(
            self.c.syms["CORRECT_PROP_LOCS_INT"],
            """
config CORRECT_PROP_LOCS_INT
\tint
\trange 1 2
\trange 3 4
\tdepends on LOC_1

config CORRECT_PROP_LOCS_INT
\tint
\trange 5 6
\trange 7 8
\tdepends on LOC_2
""",
        )

    def test_prompt_only(self):
        verify_str(
            self.c.syms["PROMPT_ONLY"],
            """
config PROMPT_ONLY
\tprompt "prompt only"
""",
        )

    def test_correct_prop_locs_int_custom_str(self):
        verify_custom_str(
            self.c.syms["CORRECT_PROP_LOCS_INT"],
            """
config CORRECT_PROP_LOCS_INT
\tint
\trange [1] [2]
\trange [3] [4]
\tdepends on [LOC_1]

config CORRECT_PROP_LOCS_INT
\tint
\trange [5] [6]
\trange [7] [8]
\tdepends on [LOC_2]
""",
        )


# -- Choice.__str__() / custom_str() ----------------------------------------


class TestChoiceStr:
    @pytest.fixture(autouse=True)
    def _setup(self, kstr_config):
        self.c = kstr_config

    def test_choice_named(self):
        verify_str(
            self.c.named_choices["CHOICE"],
            """
choice CHOICE
\ttristate "foo"
\tdefault CHOICE_1
\tdefault CHOICE_2 if dep
""",
        )

    def test_choice_unnamed(self):
        verify_str(
            self.c.named_choices["CHOICE"].nodes[0].next.item,
            """
choice
\ttristate "no name"
\toptional
""",
        )

    def test_choice_correct_prop_locs(self):
        verify_str(
            self.c.named_choices["CORRECT_PROP_LOCS_CHOICE"],
            """
choice CORRECT_PROP_LOCS_CHOICE
\tbool
\tdefault CHOICE_3
\tdepends on LOC_1

choice CORRECT_PROP_LOCS_CHOICE
\tbool
\tdefault CHOICE_4
\tdepends on LOC_2

choice CORRECT_PROP_LOCS_CHOICE
\tbool
\tdefault CHOICE_5
\tdepends on LOC_3
""",
        )

    def test_choice_correct_prop_locs_custom_str(self):
        verify_custom_str(
            self.c.named_choices["CORRECT_PROP_LOCS_CHOICE"],
            """
choice CORRECT_PROP_LOCS_CHOICE
\tbool
\tdefault [CHOICE_3]
\tdepends on [LOC_1]

choice CORRECT_PROP_LOCS_CHOICE
\tbool
\tdefault [CHOICE_4]
\tdepends on [LOC_2]

choice CORRECT_PROP_LOCS_CHOICE
\tbool
\tdefault [CHOICE_5]
\tdepends on [LOC_3]
""",
        )


# -- MenuNode.__str__() / custom_str() for menus and comments ---------------


class TestMenuNodeStr:
    @pytest.fixture(autouse=True)
    def _setup(self, kstr_config):
        self.c = kstr_config

    def test_simple_menu(self):
        verify_str(
            self.c.syms["SIMPLE_MENU_HOOK"].nodes[0].next,
            """
menu "simple menu"
""",
        )

    def test_advanced_menu(self):
        verify_str(
            self.c.syms["ADVANCED_MENU_HOOK"].nodes[0].next,
            """
menu "advanced menu"
\tdepends on A
\tvisible if B && (C || D)
""",
        )

    def test_advanced_menu_custom_str(self):
        verify_custom_str(
            self.c.syms["ADVANCED_MENU_HOOK"].nodes[0].next,
            """
menu "advanced menu"
\tdepends on [A]
\tvisible if [B] && ([C] || [D])
""",
        )

    def test_simple_comment(self):
        verify_str(
            self.c.syms["SIMPLE_COMMENT_HOOK"].nodes[0].next,
            """
comment "simple comment"
""",
        )

    def test_advanced_comment(self):
        verify_str(
            self.c.syms["ADVANCED_COMMENT_HOOK"].nodes[0].next,
            """
comment "advanced comment"
\tdepends on A && B
""",
        )

    def test_advanced_comment_custom_str(self):
        verify_custom_str(
            self.c.syms["ADVANCED_COMMENT_HOOK"].nodes[0].next,
            """
comment "advanced comment"
\tdepends on [A] && [B]
""",
        )


# -- {MenuNode,Symbol,Choice}.orig_* ----------------------------------------


class TestOrigProperties:
    @pytest.fixture(autouse=True)
    def _setup(self, kstr_config):
        self.c = kstr_config

    def test_dep_rem_corner_cases(self):
        verify_str(
            self.c.syms["DEP_REM_CORNER_CASES"],
            """
config DEP_REM_CORNER_CASES
\tbool
\tdefault A
\tdepends on n

config DEP_REM_CORNER_CASES
\tbool
\tdefault B if n

config DEP_REM_CORNER_CASES
\tbool
\tdefault C
\tdepends on m && MODULES

config DEP_REM_CORNER_CASES
\tbool
\tdefault D if A

config DEP_REM_CORNER_CASES
\tbool
\tdefault E if !E1
\tdefault F if F1 = F2
\tdefault G if G1 || H1
\tdepends on !H

config DEP_REM_CORNER_CASES
\tbool
\tdefault H
\tdepends on "foo" = "bar"

config DEP_REM_CORNER_CASES
\tbool "prompt" if FOO || BAR
\tdepends on BAZ && QAZ
""",
        )

    def test_symbol_orig_defaults(self):
        verify_deps(self.c.syms["BOOL_SYM_ORIG"].orig_defaults, 1, "DEP y y")

    def test_symbol_orig_selects(self):
        verify_deps(self.c.syms["BOOL_SYM_ORIG"].orig_selects, 1, "y DEP y")

    def test_symbol_orig_implies(self):
        verify_deps(self.c.syms["BOOL_SYM_ORIG"].orig_implies, 1, "y y DEP")

    def test_int_sym_orig_ranges(self):
        verify_deps(self.c.syms["INT_SYM_ORIG"].orig_ranges, 2, "DEP y DEP")

    def test_choice_orig_defaults(self):
        verify_deps(self.c.named_choices["CHOICE_ORIG"].orig_defaults, 1, "y DEP DEP")


# -- Symbol.__repr__() ------------------------------------------------------


class TestSymbolRepr:
    @pytest.fixture(autouse=True)
    def _setup(self, krepr_config):
        self.c = krepr_config

    def test_n(self):
        assert repr(self.c.n) == "<symbol n, tristate, value n, constant>"

    def test_m(self):
        assert repr(self.c.m) == "<symbol m, tristate, value m, constant>"

    def test_y(self):
        assert repr(self.c.y) == "<symbol y, tristate, value y, constant>"

    def test_undefined(self):
        assert (
            repr(self.c.syms["UNDEFINED"])
            == '<symbol UNDEFINED, unknown, value "UNDEFINED", visibility n, direct deps n, undefined>'
        )

    def test_basic(self):
        assert (
            repr(self.c.syms["BASIC"])
            == "<symbol BASIC, bool, value y, visibility n, direct deps y, tests/Krepr:9>"
        )

    def test_visible(self):
        assert (
            repr(self.c.syms["VISIBLE"])
            == '<symbol VISIBLE, bool, "visible", value n, visibility y, direct deps y, tests/Krepr:14>'
        )

    def test_visible_set_value(self):
        self.c.syms["VISIBLE"].set_value(2)
        assert (
            repr(self.c.syms["VISIBLE"])
            == '<symbol VISIBLE, bool, "visible", value y, user value y, visibility y, direct deps y, tests/Krepr:14>'
        )

    def test_string_set_value(self):
        self.c.syms["STRING"].set_value("foo")
        assert (
            repr(self.c.syms["STRING"])
            == '<symbol STRING, string, "visible", value "foo", user value "foo", visibility y, direct deps y, tests/Krepr:17>'
        )

    def test_dir_dep_n(self):
        assert (
            repr(self.c.syms["DIR_DEP_N"])
            == '<symbol DIR_DEP_N, unknown, value "DIR_DEP_N", visibility n, direct deps n, tests/Krepr:20>'
        )

    def test_options(self):
        assert (
            repr(self.c.syms["OPTIONS"])
            == '<symbol OPTIONS, unknown, value "OPTIONS", visibility n, allnoconfig_y, is the defconfig_list symbol, from environment variable ENV, direct deps y, tests/Krepr:23>'
        )

    def test_multi_def(self):
        assert (
            repr(self.c.syms["MULTI_DEF"])
            == '<symbol MULTI_DEF, unknown, value "MULTI_DEF", visibility n, direct deps y, tests/Krepr:28, tests/Krepr:29>'
        )

    def test_choice_sym(self):
        assert (
            repr(self.c.syms["CHOICE_1"])
            == '<symbol CHOICE_1, tristate, "choice sym", value n, visibility m, choice symbol, direct deps m, tests/Krepr:36>'
        )

    def test_modules(self):
        assert (
            repr(self.c.modules)
            == "<symbol MODULES, bool, value y, visibility n, is the modules symbol, direct deps y, tests/Krepr:1>"
        )


# -- Choice.__repr__() ------------------------------------------------------


class TestChoiceRepr:
    @pytest.fixture(autouse=True)
    def _setup(self, krepr_config):
        self.c = krepr_config

    def test_choice_basic(self):
        assert (
            repr(self.c.named_choices["CHOICE"])
            == '<choice CHOICE, tristate, "choice", mode m, visibility y, tests/Krepr:33>'
        )

    def test_choice_set_value_y(self):
        self.c.named_choices["CHOICE"].set_value(2)
        assert (
            repr(self.c.named_choices["CHOICE"])
            == '<choice CHOICE, tristate, "choice", mode y, user mode y, CHOICE_1 selected, visibility y, tests/Krepr:33>'
        )

    def test_choice_user_selection(self):
        self.c.named_choices["CHOICE"].set_value(2)
        self.c.syms["CHOICE_2"].set_value(2)
        assert (
            repr(self.c.named_choices["CHOICE"])
            == '<choice CHOICE, tristate, "choice", mode y, user mode y, CHOICE_2 selected, CHOICE_2 selected by user, visibility y, tests/Krepr:33>'
        )

    def test_choice_user_selection_overridden(self):
        self.c.named_choices["CHOICE"].set_value(2)
        self.c.syms["CHOICE_2"].set_value(2)
        self.c.named_choices["CHOICE"].set_value(1)
        assert (
            repr(self.c.named_choices["CHOICE"])
            == '<choice CHOICE, tristate, "choice", mode m, user mode m, CHOICE_2 selected by user (overridden), visibility y, tests/Krepr:33>'
        )

    def test_choice_optional_unnamed(self):
        assert (
            repr(self.c.syms["CHOICE_HOOK"].nodes[0].next.item)
            == '<choice, tristate, "optional choice", mode n, visibility n, optional, tests/Krepr:46>'
        )


# -- MenuNode.__repr__() ----------------------------------------------------


class TestMenuNodeRepr:
    @pytest.fixture(autouse=True)
    def _setup(self, krepr_config):
        self.c = krepr_config

    def test_basic_node(self):
        assert (
            repr(self.c.syms["BASIC"].nodes[0])
            == "<menu node for symbol BASIC, deps y, has help, has next, tests/Krepr:9>"
        )

    def test_dir_dep_n_node(self):
        assert (
            repr(self.c.syms["DIR_DEP_N"].nodes[0])
            == "<menu node for symbol DIR_DEP_N, deps n, has next, tests/Krepr:20>"
        )

    def test_multi_def_node_0(self):
        assert (
            repr(self.c.syms["MULTI_DEF"].nodes[0])
            == "<menu node for symbol MULTI_DEF, deps y, has next, tests/Krepr:28>"
        )

    def test_multi_def_node_1(self):
        assert (
            repr(self.c.syms["MULTI_DEF"].nodes[1])
            == "<menu node for symbol MULTI_DEF, deps y, has next, tests/Krepr:29>"
        )

    def test_menuconfig_node(self):
        assert (
            repr(self.c.syms["MENUCONFIG"].nodes[0])
            == "<menu node for symbol MENUCONFIG, is menuconfig, deps y, has next, tests/Krepr:31>"
        )

    def test_choice_node(self):
        assert (
            repr(self.c.named_choices["CHOICE"].nodes[0])
            == '<menu node for choice CHOICE, prompt "choice" (visibility y), deps y, has child, has next, tests/Krepr:33>'
        )

    def test_optional_choice_node(self):
        assert (
            repr(self.c.syms["CHOICE_HOOK"].nodes[0].next)
            == '<menu node for choice, prompt "optional choice" (visibility n), deps y, has next, tests/Krepr:46>'
        )

    def test_menu_no_visible_if(self):
        expected = (
            '<menu node for menu, prompt "no visible if" (visibility y), '
            "deps y, 'visible if' deps y, has next, tests/Krepr:53>"
        )
        assert repr(self.c.syms["NO_VISIBLE_IF_HOOK"].nodes[0].next) == expected

    def test_menu_visible_if(self):
        expected = (
            '<menu node for menu, prompt "visible if" (visibility y), '
            "deps y, 'visible if' deps m, has next, tests/Krepr:58>"
        )
        assert repr(self.c.syms["VISIBLE_IF_HOOK"].nodes[0].next) == expected

    def test_comment_node(self):
        assert (
            repr(self.c.syms["COMMENT_HOOK"].nodes[0].next)
            == '<menu node for comment, prompt "comment" (visibility y), deps y, tests/Krepr:64>'
        )


# -- Kconfig.__repr__() -----------------------------------------------------


class TestKconfigRepr:
    def test_kconfig_repr_default(self):
        c = Kconfig("tests/Krepr", warn=False)
        assert repr(c) == (
            '<configuration with 15 symbols, main menu prompt "Main menu", '
            'srctree is current directory, config symbol prefix "CONFIG_", '
            "warnings disabled, printing of warnings to stderr enabled, "
            "undef. symbol assignment warnings disabled, "
            "overriding symbol assignment warnings enabled, "
            "redundant symbol assignment warnings enabled>"
        )

    def test_kconfig_repr_with_srctree(self, monkeypatch):
        monkeypatch.setenv("srctree", ".")
        monkeypatch.setenv("CONFIG_", "CONFIG_ value")
        c = Kconfig("tests/Krepr", warn=False)
        c.warn = True
        c.warn_to_stderr = False
        c.warn_assign_override = False
        c.warn_assign_redun = False
        c.warn_assign_undef = True
        assert repr(c) == (
            '<configuration with 15 symbols, main menu prompt "Main menu", '
            'srctree ".", config symbol prefix "CONFIG_ value", '
            "warnings enabled, printing of warnings to stderr disabled, "
            "undef. symbol assignment warnings enabled, "
            "overriding symbol assignment warnings disabled, "
            "redundant symbol assignment warnings disabled>"
        )
