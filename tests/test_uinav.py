# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Menu navigation and scrolling tests for menuconfig.
#
# _enter_menu()/_leave_menu() and the four _select_*_menu_entry() functions are
# the whole cursor state machine: between them they write _sel_node_i and
# _menu_scroll from a dozen places, and getting the pair out of step is what
# makes a TUI scroll to the wrong row or index past the end of the list.
#
# None of this was reachable before the interface state moved into
# menuconfig._State. The functions read and wrote module globals that only
# _menuconfig() ever set up, so driving one meant starting a terminal. Now a
# test builds a _State, gives it a window with a height, and calls them.

import locale

import pytest

import menuconfig
from conftest import named_menu
from kconfiglib import Kconfig


class FakeWin:
    """Stands in for a rawterm region. _height() only reads .height."""

    def __init__(self, height):
        self.height = height


@pytest.fixture(scope="module")
def kconf():
    return Kconfig("tests/Kuirender", warn=False)


@pytest.fixture
def mc(kconf, monkeypatch):
    """menuconfig positioned at the top menu, in a 5-row window."""
    state = menuconfig._State()
    state.kconf = kconf
    state.show_all = True
    state.menu_win = FakeWin(5)
    state.cur_menu = kconf.top_node
    monkeypatch.setattr(menuconfig, "_s", state)
    # After the install, not before: _shown_nodes() reads show_all off the
    # module's _s rather than off anything passed in, so building the list
    # first silently used the previous state's value and dropped the
    # promptless nodes this fixture exists to show.
    state.shown = menuconfig._shown_nodes(kconf.top_node)
    return menuconfig


def test_the_top_menu_has_enough_rows_to_scroll(mc):
    """Guards the fixture: the cases below are meaningless on a short list."""
    assert len(mc._s.shown) > mc._s.menu_win.height


def test_next_and_prev_walk_the_list(mc):
    mc._select_next_menu_entry()
    assert mc._s.sel_node_i == 1
    mc._select_prev_menu_entry()
    assert mc._s.sel_node_i == 0


def test_selection_stops_at_both_ends(mc):
    mc._select_prev_menu_entry()
    assert mc._s.sel_node_i == 0

    mc._select_last_menu_entry()
    last = len(mc._s.shown) - 1
    assert mc._s.sel_node_i == last

    mc._select_next_menu_entry()
    assert mc._s.sel_node_i == last


def test_scroll_never_leaves_the_selection_off_screen(mc):
    """The invariant the whole scroll offset dance exists to keep."""
    height = mc._s.menu_win.height
    for _ in range(len(mc._s.shown) + 5):
        mc._select_next_menu_entry()
        assert mc._s.menu_scroll <= mc._s.sel_node_i < mc._s.menu_scroll + height
    for _ in range(len(mc._s.shown) + 5):
        mc._select_prev_menu_entry()
        assert mc._s.menu_scroll <= mc._s.sel_node_i < mc._s.menu_scroll + height


def test_scroll_stops_at_max_scroll(mc):
    """Asserting this right after _select_last_menu_entry() proves nothing:
    that function assigns _max_scroll() to menu_scroll, so the comparison is
    against the value just written. Walk there one entry at a time instead,
    which is the path that has to respect the limit."""
    limit = mc._max_scroll(mc._s.shown, mc._s.menu_win)
    assert limit > 0

    for _ in range(len(mc._s.shown) + 10):
        mc._select_next_menu_entry()
        assert mc._s.menu_scroll <= limit

    assert mc._s.menu_scroll == limit
    assert mc._s.sel_node_i == len(mc._s.shown) - 1


def test_first_entry_resets_the_scroll(mc):
    mc._select_last_menu_entry()
    assert mc._s.menu_scroll > 0
    mc._select_first_menu_entry()
    assert (mc._s.sel_node_i, mc._s.menu_scroll) == (0, 0)


def shown_node(mc, name):
    for node in mc._s.shown:
        if node.item is not None and getattr(node.item, "name", None) == name:
            return node
    raise AssertionError(name + " not shown in the top menu")


def test_entering_and_leaving_a_menu_restores_the_screen_row(mc, kconf):
    """The reason _enter_menu() pushes onto parent_screen_rows at all."""
    menu = shown_node(mc, "MENUCONFIG_SYM")
    mc._s.sel_node_i = mc._s.shown.index(menu)
    # Two rows down from the top of the window, so the row survives the
    # clamp in _leave_menu()
    mc._s.menu_scroll = mc._s.sel_node_i - 2
    row_before = 2

    assert mc._enter_menu(menu) is True
    assert mc._s.cur_menu is menu
    assert (mc._s.sel_node_i, mc._s.menu_scroll) == (0, 0)

    mc._leave_menu()
    assert mc._s.cur_menu is kconf.top_node
    assert mc._s.shown[mc._s.sel_node_i] is menu
    assert mc._s.sel_node_i - mc._s.menu_scroll == row_before
    assert mc._s.parent_screen_rows == []


def test_a_shrunk_window_clamps_the_restored_row(mc):
    """The terminal can shrink while we are inside the submenu."""
    menu = shown_node(mc, "MENUCONFIG_SYM")
    mc._s.sel_node_i = mc._s.shown.index(menu)
    mc._s.menu_scroll = 0
    assert mc._enter_menu(menu) is True

    mc._s.menu_win = FakeWin(3)
    mc._leave_menu()

    # Restored to the last row of the smaller window rather than off-screen
    assert mc._s.sel_node_i - mc._s.menu_scroll == 2
    assert mc._s.menu_scroll >= 0


def test_an_empty_menu_is_never_entered(mc, kconf):
    """_enter_menu() refuses, because the display needs a selected node."""
    empty = named_menu(kconf, "Empty menu")
    before = (mc._s.cur_menu, mc._s.sel_node_i, mc._s.menu_scroll)
    assert mc._enter_menu(empty) is False
    assert (mc._s.cur_menu, mc._s.sel_node_i, mc._s.menu_scroll) == before
    assert mc._s.parent_screen_rows == []


def test_leaving_the_top_menu_does_nothing(mc, kconf):
    mc._leave_menu()
    assert mc._s.cur_menu is kconf.top_node


def test_a_second_run_does_not_inherit_the_first_runs_position(
    mc, kconf, tmp_path, monkeypatch, capsys
):
    """What the _State() reset in menuconfig() is for.

    This one drives the real entry point, which is the only way to cover the
    reset, and that entry point has two process-wide side effects: it sets
    the locale from the environment, and it loads a .config from the working
    directory, printing as it goes. Left alone, the locale would stay changed
    for every test that runs afterwards, including the byte-for-byte render
    comparisons. So run it in an empty directory and put the locale back.
    """
    monkeypatch.chdir(tmp_path)
    saved = locale.setlocale(locale.LC_ALL)
    try:
        mc._select_last_menu_entry()
        assert mc._s.sel_node_i > 0

        menuconfig.menuconfig(kconf, headless=True)
    finally:
        locale.setlocale(locale.LC_ALL, saved)
    capsys.readouterr()
    assert menuconfig._s.sel_node_i == 0
    assert menuconfig._s.menu_scroll == 0
    assert menuconfig._s.parent_screen_rows == []
