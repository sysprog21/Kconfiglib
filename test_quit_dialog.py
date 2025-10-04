#!/usr/bin/env python3
"""Test the quit dialog display"""

import curses
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_dialog(stdscr):
    """Test the dialog in curses mode"""
    curses.start_color()
    curses.use_default_colors()

    # Initialize color pair
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # Create test window
    screen_height, screen_width = stdscr.getmaxyx()

    text = "Save configuration?"
    buttons = ["Yes", "No", "Cancel"]

    # Calculate size
    lines = text.split("\n")
    button_row_width = sum(len(btn) + 4 for btn in buttons) + (len(buttons) - 1)
    text_width = max(len(line) for line in lines) if lines else 0
    win_height = min(len(lines) + 6, screen_height)
    win_width = min(max(text_width, button_row_width) + 4, screen_width)

    # Create window
    win = curses.newwin(
        win_height,
        win_width,
        (screen_height - win_height) // 2,
        (screen_width - win_width) // 2,
    )

    # Draw dialog
    win.erase()
    win.bkgd(" ", curses.color_pair(2))

    # Draw text
    for i, line in enumerate(lines):
        win.addstr(2 + i, 2, line)

    # Draw buttons
    button_row = win_height - 3
    total_width = sum(len(btn) + 4 for btn in buttons) + (len(buttons) - 1)
    start_x = (win_width - total_width) // 2

    x = start_x
    for i, btn in enumerate(buttons):
        if i == 0:  # Selected
            btn_attr = curses.color_pair(1) | curses.A_BOLD
        else:
            btn_attr = curses.color_pair(2)

        win.addstr(button_row, x, "< ", btn_attr)
        x += 2
        win.addstr(button_row, x, btn, btn_attr)
        x += len(btn)
        win.addstr(button_row, x, " >", btn_attr)
        x += 2
        if i < len(buttons) - 1:
            x += 1

    # Draw frame
    win.box()
    win.addstr(0, (win_width - 4) // 2, "Quit")

    win.refresh()

    stdscr.addstr(
        screen_height - 1,
        0,
        f"Window size: {win_height}x{win_width}, button_row: {button_row}",
    )
    stdscr.addstr(screen_height - 2, 0, "Press any key to exit...")
    stdscr.refresh()
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(test_dialog)
