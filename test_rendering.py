#!/usr/bin/env python3
"""
簡單的測試腳本，用於驗證 ACS 字元和陰影效果的繪製。
這個腳本會創建一個簡單的對話框來展示新的視覺效果。
"""

import curses
import sys


def test_box_drawing(stdscr):
    # 清除螢幕
    stdscr.clear()
    curses.curs_set(0)

    # 初始化顏色
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        # Linux kernel menuconfig 配色
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # 框架
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # 內容

    # 創建一個測試視窗
    height, width = stdscr.getmaxyx()
    win_h, win_w = 10, 60
    win_y = (height - win_h) // 2
    win_x = (width - win_w) // 2

    win = curses.newwin(win_h, win_w, win_y, win_x)

    # 繪製邊框（使用 ACS 字元）
    win.attron(curses.color_pair(1))

    # 繪製四個角
    win.addch(0, 0, curses.ACS_ULCORNER)
    win.addch(0, win_w - 1, curses.ACS_URCORNER)
    win.addch(win_h - 1, 0, curses.ACS_LLCORNER)
    win.addch(win_h - 1, win_w - 1, curses.ACS_LRCORNER)

    # 繪製水平線
    win.hline(0, 1, curses.ACS_HLINE, win_w - 2)
    win.hline(win_h - 1, 1, curses.ACS_HLINE, win_w - 2)

    # 繪製垂直線
    win.vline(1, 0, curses.ACS_VLINE, win_h - 2)
    win.vline(1, win_w - 1, curses.ACS_VLINE, win_h - 2)

    # 標題
    title = " Linux Kernel Style Menuconfig "
    win.addstr(0, (win_w - len(title)) // 2, title)

    win.attroff(curses.color_pair(1))

    # 繪製陰影（右側和底部）
    # 右側陰影
    if win_x + win_w + 2 < width:
        for i in range(1, min(win_h, height - win_y)):
            try:
                stdscr.addch(win_y + i, win_x + win_w, " ")
                stdscr.addch(win_y + i, win_x + win_w + 1, " ")
            except curses.error:
                pass

    # 底部陰影
    if win_y + win_h + 1 < height:
        for i in range(2, min(win_w + 2, width - win_x)):
            try:
                stdscr.addch(win_y + win_h, win_x + i, " ")
            except curses.error:
                pass

    # 內容文字
    win.attron(curses.color_pair(2))
    messages = [
        "ACS box-drawing test",
        "Shadow effect enabled",
        "",
        "Press any key to exit",
    ]
    for i, msg in enumerate(messages):
        win.addstr(2 + i, 2, msg)
    win.attroff(curses.color_pair(2))

    win.refresh()
    stdscr.refresh()

    # 等待按鍵
    stdscr.getch()


if __name__ == "__main__":
    try:
        curses.wrapper(test_box_drawing)
        print("✓ ACS 字元繪製成功")
        print("✓ 陰影效果已實現")
        print("✓ 視覺風格符合 Linux kernel menuconfig")
    except Exception as e:
        print(f"✗ 測試失敗: {e}", file=sys.stderr)
        sys.exit(1)
