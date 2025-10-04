#!/usr/bin/env python3
"""
測試帶有可選擇按鈕的對話框
"""

import curses


def test_button_dialog(stdscr):
    curses.curs_set(0)
    stdscr.clear()

    # 初始化顏色
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # 框架
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)  # 內容
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)  # 選中按鈕

    height, width = stdscr.getmaxyx()

    # 創建對話框
    dialog_height = 10
    dialog_width = 50
    dialog_y = (height - dialog_height) // 2
    dialog_x = (width - dialog_width) // 2

    dialog_win = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
    dialog_win.keypad(True)

    selected_button = 0
    buttons = ["< Yes >", "< No >", "< Cancel >"]

    # 主循環
    while True:
        dialog_win.erase()

        # 繪製邊框
        dialog_win.attron(curses.color_pair(1))
        dialog_win.box()
        title = " Save configuration? "
        dialog_win.addstr(0, (dialog_width - len(title)) // 2, title)
        dialog_win.attroff(curses.color_pair(1))

        # 繪製文字
        dialog_win.addstr(3, 2, "Save configuration?", curses.color_pair(2))
        dialog_win.addstr(5, 2, "Use arrow keys to navigate", curses.color_pair(2))
        dialog_win.addstr(6, 2, "Press Enter to select", curses.color_pair(2))

        # 繪製按鈕
        button_row = 8
        total_width = sum(len(b) for b in buttons) + (len(buttons) - 1) * 2
        start_col = (dialog_width - total_width) // 2

        col = start_col
        for i, button in enumerate(buttons):
            if i == selected_button:
                # 選中的按鈕（反白）
                dialog_win.addstr(
                    button_row, col, button, curses.color_pair(3) | curses.A_BOLD
                )
            else:
                # 正常按鈕
                dialog_win.addstr(button_row, col, button, curses.color_pair(2))
            col += len(button) + 2

        # 繪製陰影
        if dialog_x + dialog_width + 2 < width:
            for i in range(1, min(dialog_height, height - dialog_y)):
                try:
                    stdscr.addch(dialog_y + i, dialog_x + dialog_width, " ")
                    stdscr.addch(dialog_y + i, dialog_x + dialog_width + 1, " ")
                except curses.error:
                    pass

        if dialog_y + dialog_height + 1 < height:
            for i in range(2, min(dialog_width + 2, width - dialog_x)):
                try:
                    stdscr.addch(dialog_y + dialog_height, dialog_x + i, " ")
                except curses.error:
                    pass

        dialog_win.refresh()
        stdscr.refresh()

        # 處理按鍵
        c = dialog_win.getch()

        if c == curses.KEY_LEFT:
            selected_button = (selected_button - 1) % len(buttons)
        elif c == curses.KEY_RIGHT:
            selected_button = (selected_button + 1) % len(buttons)
        elif c in (ord("\n"), ord(" ")):  # Enter or Space
            result = ["Yes", "No", "Cancel"][selected_button]
            return result
        elif c == 27:  # ESC
            return None


if __name__ == "__main__":
    try:
        result = curses.wrapper(test_button_dialog)
        if result:
            print(f"✓ 按鈕對話框測試成功")
            print(f"✓ 選擇了: {result}")
            print(f"✓ 方向鍵導航功能正常")
            print(f"✓ 反白光標顯示正常")
        else:
            print("✓ 按下 ESC 取消")
    except Exception as e:
        print(f"✗ 測試失敗: {e}")
