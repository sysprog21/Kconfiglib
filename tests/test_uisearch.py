# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Jump-to search tests, driving the *real* guiconfig._update_jump_to_matches()
# rather than a reimplementation of it.
#
# This replaces tests/test_ui.py, which covered the same ground against a local
# reimplementation of the prefix-stripping and matching. A copy cannot catch a
# change to the original, which is the same reason tests/test_ui_ranges.py
# gives for calling the real _range_info(). Every case from that file is kept
# below, driven through the shipped function with a stubbed Treeview, so the
# regex handling, the multi-token AND, the menu/comment pass and the error
# paths are all exercised the way users hit them.
#
# Both tools are covered. menuconfig's copy used to be inlined in
# _jump_to_dialog(), unreachable without a terminal; it now lives in
# menuconfig._jump_to_matches(), so the same cases run against both and the two
# copies cannot drift apart unnoticed.

import pytest

import menuconfig
from kconfiglib import Kconfig

# guiconfig pulls in tkinter, which is an optional part of a Python
# installation. Skip only its tests so menuconfig stays covered headlessly.
#
# ImportError rather than ModuleNotFoundError: a half-installed Tk is present
# but unloadable, and the C extension loader reports that as a plain
# ImportError. Both carry .name, so an unrelated import bug inside guiconfig
# still propagates instead of being silently turned into a skip.
try:
    import guiconfig
except ImportError as e:
    if e.name not in ("tkinter", "_tkinter"):
        raise
    guiconfig = None


def _names(nodes):
    """How a matched node is identified in the assertions below.

    Shared by both fixtures: test_the_two_tools_agree compares their outputs,
    so two copies drifting would turn that check into a false pass.
    """
    return [
        getattr(n.item, "name", None) or (n.prompt[0] if n.prompt else None)
        for n in nodes
    ]


class FakeTree:
    """The few Treeview methods _update_jump_to_matches() actually calls."""

    def __init__(self):
        self.children = ()
        self.selection = None
        self.focused = None
        self.items = {}

    def selection_set(self, *args):
        self.selection = args

    def set_children(self, _parent, *ids):
        self.children = ids

    def focus(self, item):
        self.focused = item

    def item(self, item, **kwargs):
        self.items[item] = kwargs


@pytest.fixture
def search(monkeypatch):
    """Returns (run, msglabel, tree) for driving the real search."""
    if guiconfig is None:
        pytest.skip("guiconfig requires tkinter")
    kconf = Kconfig("tests/Kuirender", warn=False)
    tree = FakeTree()
    msglabel = {"text": ""}

    monkeypatch.setattr(guiconfig, "_kconf", kconf, raising=False)
    monkeypatch.setattr(guiconfig, "_show_all", True, raising=False)
    monkeypatch.setattr(guiconfig, "_single_menu", False, raising=False)
    monkeypatch.setattr(guiconfig, "_jump_to_tree", tree, raising=False)
    monkeypatch.setattr(guiconfig, "_jump_to_matches", [], raising=False)
    # Cleared so one test's sort order can't leak into the next
    monkeypatch.setattr(guiconfig, "_cached_sc_nodes", [], raising=False)
    monkeypatch.setattr(guiconfig, "_cached_menu_comment_nodes", [], raising=False)

    def run(text):
        guiconfig._update_jump_to_matches(msglabel, text)
        return _names(guiconfig._jump_to_matches)

    return run, msglabel, tree


def test_matches_symbol_by_name(search):
    run, msglabel, _ = search
    assert run("BOOL_SYM") == ["BOOL_SYM"]
    assert msglabel["text"] == ""


def test_search_is_case_insensitive(search):
    run, _, _ = search
    assert run("bool_sym") == ["BOOL_SYM"]


def test_config_prefix_is_stripped(search):
    """Typing the CONFIG_ prefix still finds the symbol."""
    run, _, _ = search
    assert run("CONFIG_BOOL_SYM") == ["BOOL_SYM"]


def test_custom_config_prefix_is_stripped(search, monkeypatch):
    run, _, _ = search
    monkeypatch.setattr(guiconfig._kconf, "config_prefix", "BR2_")
    assert run("BR2_BOOL_SYM") == ["BOOL_SYM"]


def test_prefix_is_stripped_only_at_the_start_of_a_token(search):
    """CONFIG_ inside a token is part of the pattern, not a prefix to remove."""
    run, _, _ = search
    assert run("MY_CONFIG_BOOL_SYM") == []


def test_each_token_is_stripped_independently(search):
    """Both tokens lose their prefix, then all of them must match."""
    run, _, _ = search
    assert run("CONFIG_SEL CONFIG_A") == ["MANY_SELECTED", "SEL_A"]


def test_regex_after_the_prefix_is_preserved(search):
    """Stripping CONFIG_ must not disturb the pattern that follows it."""
    run, _, _ = search
    assert run("CONFIG_SEL_.*") == ["SEL_A", "SEL_B", "SEL_C"]


def test_bare_prefix_becomes_an_empty_pattern(search):
    """ "CONFIG_" alone strips to "", which matches everything."""
    run, _, _ = search
    assert len(run("CONFIG_")) == len(run(""))


def test_prefix_of_a_different_project_is_not_stripped(search, monkeypatch):
    """With BR2_ configured, CONFIG_ is just text and matches nothing here."""
    run, _, _ = search
    monkeypatch.setattr(guiconfig._kconf, "config_prefix", "BR2_")
    assert run("CONFIG_BOOL_SYM") == []


def test_empty_prefix_strips_nothing(search, monkeypatch):
    run, _, _ = search
    monkeypatch.setattr(guiconfig._kconf, "config_prefix", "")
    assert run("CONFIG_BOOL_SYM") == []
    assert run("BOOL_SYM") == ["BOOL_SYM"]


def test_matches_on_prompt_text(search):
    run, _, _ = search
    assert "STR_SYM" in run("A string")


def test_multiple_tokens_are_anded(search):
    """Every token must match, so an impossible pair yields nothing."""
    run, msglabel, _ = search
    assert run("selector a") == ["SEL_A"]
    assert run("bool_sym hex_sym") == []
    assert msglabel["text"] == "No matches"


def test_menus_and_comments_are_searched(search):
    run, _, _ = search
    assert run("Empty menu") == ["Empty menu"]
    assert run("A comment") == ["A comment"]


def test_regex_syntax_is_supported(search):
    run, _, _ = search
    assert run("^sel_[abc]$") == ["SEL_A", "SEL_B", "SEL_C"]


def test_bad_regex_reports_instead_of_raising(search):
    """An unbalanced bracket is a message, not a traceback."""
    run, msglabel, tree = search
    assert run("[unterminated") == []
    assert msglabel["text"].startswith("Bad regular expression: ")
    # The result list is cleared rather than left stale
    assert tree.children == ()


def test_empty_search_matches_everything(search):
    """No tokens means no filters, so every node qualifies."""
    run, _, _ = search
    assert len(run("")) > 10


def test_no_matches_sets_the_message(search):
    run, msglabel, _ = search
    assert run("zzz_no_such_symbol") == []
    assert msglabel["text"] == "No matches"


def test_first_match_is_selected_and_focused(search):
    """The dialog opens with the first hit selected, ready for Enter."""
    run, _, tree = search
    names = run("sel_")
    assert names
    assert tree.selection == (id(guiconfig._jump_to_matches[0]),)
    assert tree.focused == id(guiconfig._jump_to_matches[0])


def test_matches_are_pushed_to_the_tree(search):
    """_update_jump_to_display() renders each match into the tree."""
    run, _, tree = search
    run("BOOL_SYM")
    assert len(tree.children) == 1
    (rendered,) = tree.items.values()
    assert rendered["text"] == "A bool (NEW)"


# --- the same cases, against menuconfig's copy of the logic ------------------


@pytest.fixture
def mc_search(monkeypatch):
    """Returns a run() driving the real menuconfig._jump_to_matches()."""
    kconf = Kconfig("tests/Kuirender", warn=False)
    monkeypatch.setattr(menuconfig, "_kconf", kconf, raising=False)
    monkeypatch.setattr(menuconfig, "_show_all", True, raising=False)
    monkeypatch.setattr(menuconfig, "_cached_sc_nodes", [], raising=False)
    monkeypatch.setattr(menuconfig, "_cached_menu_comment_nodes", [], raising=False)

    def run(text):
        matches, bad_re = menuconfig._jump_to_matches(text)
        return _names(matches), bad_re

    return run


@pytest.mark.parametrize(
    "query, expected",
    [
        ("BOOL_SYM", ["BOOL_SYM"]),
        ("bool_sym", ["BOOL_SYM"]),
        ("CONFIG_BOOL_SYM", ["BOOL_SYM"]),
        ("MY_CONFIG_BOOL_SYM", []),
        ("CONFIG_SEL CONFIG_A", ["MANY_SELECTED", "SEL_A"]),
        ("CONFIG_SEL_.*", ["SEL_A", "SEL_B", "SEL_C"]),
        ("^sel_[abc]$", ["SEL_A", "SEL_B", "SEL_C"]),
        ("Empty menu", ["Empty menu"]),
        ("A comment", ["A comment"]),
        ("zzz_no_such_symbol", []),
    ],
)
def test_menuconfig_search(mc_search, query, expected):
    matches, bad_re = mc_search(query)
    assert matches == expected
    assert bad_re is None


def test_menuconfig_bad_regex_reports_instead_of_raising(mc_search):
    matches, bad_re = mc_search("[unterminated")
    assert matches == []
    assert bad_re.startswith("Bad regular expression: ")


def test_menuconfig_bare_prefix_matches_everything(mc_search):
    assert len(mc_search("CONFIG_")[0]) == len(mc_search("")[0])


def test_the_two_tools_agree(mc_search, search):
    """The whole point of extracting menuconfig's copy: catch drift.

    A bad regex is in the list deliberately -- guiconfig used to leave the
    previous matches in _jump_to_matches on that path while menuconfig returned
    an empty list.
    """
    gui_run, _, _ = search
    for query in (
        "BOOL_SYM",
        "sel_",
        "^sel_[abc]$",
        "A string",
        "A comment",
        "CONFIG_SEL CONFIG_A",
        "",
        # Deliberately straight after a query that matched, so a tool leaving
        # its previous results behind on the error path is caught
        "[unterminated",
        "zzz_no_such_symbol",
        "[also bad",
    ):
        assert mc_search(query)[0] == gui_run(query), f"tools disagree on {query!r}"
