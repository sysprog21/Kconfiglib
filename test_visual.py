#!/usr/bin/env python3
"""Quick visual test for menuconfig improvements"""

import sys
import curses
import time

# Add current directory to path
sys.path.insert(0, ".")

from menuconfig import _draw_box, _draw_shadow, _style, _init_styles


def test_visual(stdscr):
    """Test box drawing and shadow"""
    # Initialize
    curses.curs_set(0)
    stdscr.clear()

    # Initialize styles
    _init_styles()

    # Test 1: Draw a box with shadow
    stdscr.addstr(0, 0, "Testing _draw_box() and _draw_shadow()...", curses.A_BOLD)
    stdscr.addstr(1, 0, "Press any key to continue, 'q' to quit")

    # Create a test window
    test_win = curses.newwin(10, 40, 5, 10)

    # Draw shadow first
    _draw_shadow(stdscr, 5, 10, 10, 40)

    # Draw box
    _draw_box(test_win, 0, 0, 10, 40, _style["frame"], _style["frame"])

    # Add some text inside
    test_win.attron(_style["body"])
    test_win.addstr(2, 2, "Box with shadow test", _style["body"])
    test_win.addstr(3, 2, "ACS characters working!", _style["body"])
    test_win.attroff(_style["body"])

    test_win.refresh()
    stdscr.refresh()

    # Wait for keypress
    key = stdscr.getch()

    if chr(key) == "q":
        return

    # Test 2: Show different styles
    stdscr.clear()
    stdscr.addstr(0, 0, "Testing different box styles...", curses.A_BOLD)

    # List style box
    list_win = curses.newwin(8, 35, 3, 5)
    _draw_shadow(stdscr, 3, 5, 8, 35)
    _draw_box(list_win, 0, 0, 8, 35, _style["list"], _style["list"])
    list_win.addstr(1, 2, "List style box")
    list_win.refresh()

    # Selection style box
    sel_win = curses.newwin(8, 35, 3, 45)
    _draw_shadow(stdscr, 3, 45, 8, 35)
    _draw_box(sel_win, 0, 0, 8, 35, _style["selection"], _style["selection"])
    sel_win.addstr(1, 2, "Selection style box")
    sel_win.refresh()

    stdscr.addstr(20, 0, "Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()


if __name__ == "__main__":
    try:
        curses.wrapper(test_visual)
        print("\n✓ Visual test passed!")
    except Exception as e:
        print(f"\n✗ Visual test failed: {e}")
        import traceback

        traceback.print_exc()
