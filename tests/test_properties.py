# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Property tests: help strings,
# locations, origins, source/rsource/gsource/grsource, symlinks,
# node_iter(), include_path, and item lists.

import os

import pytest

from kconfiglib import Kconfig, KconfigError, MenuNode, Symbol

# -- helpers -----------------------------------------------------------------


def _verify_help(node, s):
    """Assert that a node's help text matches *s* with leading/trailing
    newlines stripped (the ``s[1:-1]`` idiom from the original suite)."""
    assert node.help == s[1:-1]


def _verify_locations(nodes, *expected_locs):
    """Assert that *nodes* map to exactly *expected_locs* file:line strings."""
    actual = [f"{n.filename}:{n.linenr}" for n in nodes]
    assert actual == list(expected_locs), "node locations"


def _verify_node_path(node, *expected):
    """Assert that *node.include_path* matches *expected*."""
    assert node.include_path == expected, "node include_path"


def _verify_sym_path(c, sym_name, node_i, *expected):
    """Assert include_path for the *node_i*-th node of symbol *sym_name*."""
    _verify_node_path(c.syms[sym_name].nodes[node_i], *expected)


def _verify_prompts(items, *expected_prompts):
    """Assert that *items* carry exactly *expected_prompts*."""
    actual = []
    for item in items:
        node = item if isinstance(item, MenuNode) else item.nodes[0]
        actual.append(node.prompt[0])
    assert actual == list(expected_prompts), "item prompts"


# -- tricky help strings -----------------------------------------------------


def test_help_strings():
    c = Kconfig("tests/Khelp")

    _verify_help(
        c.syms["TWO_HELP_STRINGS"].nodes[0],
        """
first help string
""",
    )

    _verify_help(
        c.syms["TWO_HELP_STRINGS"].nodes[1],
        """
second help string
""",
    )

    _verify_help(
        c.syms["NO_BLANK_AFTER_HELP"].nodes[0],
        """
help for
NO_BLANK_AFTER_HELP
""",
    )

    _verify_help(
        c.named_choices["CHOICE_HELP"].nodes[0],
        """
help for
CHOICE_HELP
""",
    )

    _verify_help(
        c.syms["HELP_TERMINATED_BY_COMMENT"].nodes[0],
        """
a
b
c
""",
    )

    _verify_help(
        c.syms["TRICKY_HELP"].nodes[0],
        """
a
 b
  c

 d
  e
   f


g
 h
  i
""",
    )


# -- locations, origins, source/rsource/gsource/grsource --------------------


def test_locations_and_origins(monkeypatch):
    # Expanded in the 'source' statement in Klocation
    monkeypatch.setenv("TESTS_DIR_FROM_ENV", "tests")
    monkeypatch.setenv("SUB_DIR_FROM_ENV", "sub")

    monkeypatch.setenv("_SOURCED", "_sourced")
    monkeypatch.setenv("_RSOURCED", "_rsourced")
    monkeypatch.setenv("_GSOURCED", "_gsourced")
    monkeypatch.setenv("_GRSOURCED", "_grsourced")

    # Test twice, with $srctree as a relative and an absolute path,
    # respectively
    for srctree in ".", os.path.abspath("."):
        monkeypatch.setenv("srctree", srctree)

        # Has symbol with empty help text, so disable warnings
        c = Kconfig("tests/Klocation", warn=False)

        _verify_locations(c.syms["UNDEFINED"].nodes)
        assert c.syms["UNDEFINED"].name_and_loc == "UNDEFINED (undefined)"

        _verify_locations(c.syms["ONE_DEF"].nodes, "tests/Klocation:4")
        assert (
            c.syms["ONE_DEF"].name_and_loc == "ONE_DEF (defined at tests/Klocation:4)"
        )

        _verify_locations(
            c.syms["TWO_DEF"].nodes, "tests/Klocation:7", "tests/Klocation:10"
        )
        assert (
            c.syms["TWO_DEF"].name_and_loc
            == "TWO_DEF (defined at tests/Klocation:7, tests/Klocation:10)"
        )

        _verify_locations(
            c.syms["MANY_DEF"].nodes,
            "tests/Klocation:13",
            "tests/Klocation:43",
            "tests/Klocation:45",
            "tests/Klocation_sourced:3",
            "tests/sub/Klocation_rsourced:2",
            "tests/sub/Klocation_gsourced1:1",
            "tests/sub/Klocation_gsourced2:1",
            "tests/sub/Klocation_gsourced1:1",
            "tests/sub/Klocation_gsourced2:1",
            "tests/sub/Klocation_grsourced1:1",
            "tests/sub/Klocation_grsourced2:1",
            "tests/sub/Klocation_grsourced1:1",
            "tests/sub/Klocation_grsourced2:1",
            "tests/Klocation:78",
        )

        _verify_locations(
            c.named_choices["CHOICE_ONE_DEF"].nodes, "tests/Klocation_sourced:5"
        )
        assert (
            c.named_choices["CHOICE_ONE_DEF"].name_and_loc
            == "<choice CHOICE_ONE_DEF> (defined at tests/Klocation_sourced:5)"
        )

        _verify_locations(
            c.named_choices["CHOICE_TWO_DEF"].nodes,
            "tests/Klocation_sourced:9",
            "tests/Klocation_sourced:13",
        )
        assert (
            c.named_choices["CHOICE_TWO_DEF"].name_and_loc
            == "<choice CHOICE_TWO_DEF> (defined at tests/Klocation_sourced:9, tests/Klocation_sourced:13)"
        )

        _verify_locations(
            [c.syms["MENU_HOOK"].nodes[0].next], "tests/Klocation_sourced:20"
        )
        _verify_locations(
            [c.syms["COMMENT_HOOK"].nodes[0].next], "tests/Klocation_sourced:26"
        )

        # Test Kconfig.kconfig_filenames

        assert c.kconfig_filenames == [
            "tests/Klocation",
            "tests/Klocation_sourced",
            "tests/sub/Klocation_rsourced",
            "tests/sub/Klocation_gsourced1",
            "tests/sub/Klocation_gsourced2",
            "tests/sub/Klocation_gsourced1",
            "tests/sub/Klocation_gsourced2",
            "tests/sub/Klocation_grsourced1",
            "tests/sub/Klocation_grsourced2",
            "tests/sub/Klocation_grsourced1",
            "tests/sub/Klocation_grsourced2",
        ]

        # Test recursive 'source' detection

        with pytest.raises(KconfigError, match="recursive 'source'"):
            Kconfig("tests/Krecursive1")

        # Verify that source and rsource throw exceptions for missing files

        with pytest.raises(KconfigError, match="not found"):
            Kconfig("tests/Kmissingsource")

        with pytest.raises(KconfigError, match="not found"):
            Kconfig("tests/Kmissingrsource")

        # Tests origins

        c = Kconfig("tests/Korigins", warn=False)
        c.syms["MAIN_FLAG_SELECT"].set_value(2, "here")

        expected = [
            ("MAIN_FLAG", ("select", ["MAIN_FLAG_SELECT"])),
            (
                "MAIN_FLAG_DEPENDENCY",
                ("default", (os.path.abspath("tests/Korigins"), 6)),
            ),
            ("MAIN_FLAG_SELECT", ("assign", "here")),
            ("SECOND_CHOICE", ("default", None)),
            ("UNSET_FLAG", ("unset", None)),
        ]

        for node in c.node_iter(True):
            if not isinstance(node.item, Symbol):
                continue

            if node.item.origin is None:
                continue

            exp_name, exp_origin = expected.pop(0)
            assert node.item.name == exp_name
            assert node.item.origin == exp_origin

        assert len(expected) == 0, "origin test mismatch"


# -- symlink + rsource -------------------------------------------------------


def test_symlink_rsource(monkeypatch):
    # Test a tricky case involving symlinks. $srctree is tests/symlink, which
    # points to tests/sub/sub, meaning tests/symlink/.. != tests/. Previously,
    # using 'rsource' from a file sourced with an absolute path triggered an
    # unsafe relpath() with tests/symlink/.. in it, crashing.

    monkeypatch.setenv("srctree", "tests/symlink")
    monkeypatch.setenv(
        "KCONFIG_SYMLINK_2",
        os.path.abspath("tests/sub/Kconfig_symlink_2"),
    )
    assert os.path.isabs(
        Kconfig("Kconfig_symlink_1").syms["FOUNDME"].nodes[0].filename
    ), "Symlink + rsource issues"


# -- Kconfig.node_iter() -----------------------------------------------------


def test_node_iter(monkeypatch):
    # Reuse tests/Klocation. The node_iter(unique_syms=True) case already gets
    # plenty of testing from write_config() as well.

    monkeypatch.setenv("TESTS_DIR_FROM_ENV", "tests")
    monkeypatch.setenv("SUB_DIR_FROM_ENV", "sub")
    monkeypatch.setenv("_SOURCED", "_sourced")
    monkeypatch.setenv("_RSOURCED", "_rsourced")
    monkeypatch.setenv("_GSOURCED", "_gsourced")
    monkeypatch.setenv("_GRSOURCED", "_grsourced")

    c = Kconfig("tests/Klocation", warn=False)

    assert [
        node.item.name for node in c.node_iter() if isinstance(node.item, Symbol)
    ] == [
        "ONE_DEF",
        "TWO_DEF",
        "TWO_DEF",
        "MANY_DEF",
        "HELP_1",
        "HELP_2",
        "HELP_3",
        "MANY_DEF",
        "MANY_DEF",
        "MANY_DEF",
        "MENU_HOOK",
        "COMMENT_HOOK",
    ] + 10 * [
        "MANY_DEF"
    ]

    assert [
        node.item.name for node in c.node_iter(True) if isinstance(node.item, Symbol)
    ] == [
        "ONE_DEF",
        "TWO_DEF",
        "MANY_DEF",
        "HELP_1",
        "HELP_2",
        "HELP_3",
        "MENU_HOOK",
        "COMMENT_HOOK",
    ]

    assert [
        node.prompt[0] for node in c.node_iter() if not isinstance(node.item, Symbol)
    ] == [
        "one-def choice",
        "two-def choice 1",
        "two-def choice 2",
        "menu",
        "comment",
    ]

    assert [
        node.prompt[0]
        for node in c.node_iter(True)
        if not isinstance(node.item, Symbol)
    ] == [
        "one-def choice",
        "two-def choice 1",
        "two-def choice 2",
        "menu",
        "comment",
    ]


# -- MenuNode.include_path --------------------------------------------------


def test_include_path(monkeypatch):
    monkeypatch.setenv("srctree", "tests")

    c = Kconfig("Kinclude_path")

    _verify_sym_path(c, "TOP", 0)
    _verify_sym_path(c, "TOP", 1)
    _verify_sym_path(c, "TOP", 2)

    _verify_sym_path(c, "ONE_DOWN", 0, ("Kinclude_path", 4))
    _verify_sym_path(c, "ONE_DOWN", 1, ("Kinclude_path", 4))
    _verify_sym_path(c, "ONE_DOWN", 2, ("Kinclude_path", 4))
    _verify_sym_path(c, "ONE_DOWN", 3, ("Kinclude_path", 9))
    _verify_sym_path(c, "ONE_DOWN", 4, ("Kinclude_path", 9))
    _verify_sym_path(c, "ONE_DOWN", 5, ("Kinclude_path", 9))

    _verify_sym_path(
        c, "TWO_DOWN", 0, ("Kinclude_path", 4), ("Kinclude_path_sourced_1", 4)
    )
    _verify_sym_path(
        c, "TWO_DOWN", 1, ("Kinclude_path", 4), ("Kinclude_path_sourced_1", 9)
    )
    _verify_sym_path(
        c, "TWO_DOWN", 2, ("Kinclude_path", 9), ("Kinclude_path_sourced_1", 4)
    )
    _verify_sym_path(
        c, "TWO_DOWN", 3, ("Kinclude_path", 9), ("Kinclude_path_sourced_1", 9)
    )

    _verify_node_path(c.top_node)
    _verify_node_path(c.menus[0], ("Kinclude_path", 4), ("Kinclude_path_sourced_1", 4))
    _verify_node_path(
        c.comments[0], ("Kinclude_path", 4), ("Kinclude_path_sourced_1", 4)
    )
    _verify_node_path(
        c.choices[0].nodes[0], ("Kinclude_path", 4), ("Kinclude_path_sourced_1", 4)
    )


# -- Kconfig.choices/menus/comments -----------------------------------------


def test_item_lists():
    c = Kconfig("tests/Kitemlists")

    _verify_prompts(c.choices, "choice 1", "choice 2", "choice 3", "choice 2")
    _verify_prompts(c.menus, "menu 1", "menu 2", "menu 3", "menu 4", "menu 5")
    _verify_prompts(c.comments, "comment 1", "comment 2", "comment 3")
