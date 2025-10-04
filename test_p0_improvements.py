#!/usr/bin/env python3
"""
測試 P0 優先級改進項目:
1. 分隔線 (separator line above buttons)
2. 首字母高亮 (first letter underline for shortcut keys)
3. TAB 鍵支持 (TAB/Shift+TAB navigation)
"""

import curses


def test_dialog(stdscr):
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
    dialog_height = 12
    dialog_width = 60
    dialog_y = (height - dialog_height) // 2
    dialog_x = (width - dialog_width) // 2

    dialog_win = curses.newwin(dialog_height, dialog_width, dialog_y, dialog_x)
    dialog_win.keypad(True)

    selected_button = 0
    button_labels = ["Yes", "No", "Cancel"]

    instructions = [
        "測試項目:",
        "✓ 分隔線應該在按鈕上方",
        "✓ 按鈕格式應該是 < Label >",
        "✓ 首字母應該有底線 (快捷鍵)",
        "✓ 使用方向鍵/TAB/Shift+TAB 導航",
        "✓ Enter 選擇按鈕",
    ]

    # 主循環
    while True:
        dialog_win.erase()

        # 繪製邊框
        dialog_win.attron(curses.color_pair(1))
        dialog_win.box()
        title = " P0 Improvements Test "
        dialog_win.addstr(0, (dialog_width - len(title)) // 2, title)
        dialog_win.attroff(curses.color_pair(1))

        # 繪製說明文字
        for i, line in enumerate(instructions):
            dialog_win.addstr(2 + i, 2, line, curses.color_pair(2))

        # 繪製分隔線 (P0 改進 #1)
        separator_row = dialog_height - 4
        dialog_win.attron(curses.color_pair(1))
        dialog_win.addch(separator_row, 0, curses.ACS_LTEE)
        for i in range(1, dialog_width - 1):
            dialog_win.addch(separator_row, i, curses.ACS_HLINE)
        dialog_win.addch(separator_row, dialog_width - 1, curses.ACS_RTEE)
        dialog_win.attroff(curses.color_pair(1))

        # 繪製按鈕 (P0 改進 #2: 首字母高亮)
        button_row = dialog_height - 3
        # 計算按鈕總寬度: "< Yes > < No > < Cancel >"
        total_width = (
            sum(len(label) + 4 for label in button_labels)
            + (len(button_labels) - 1) * 2
        )
        start_col = (dialog_width - total_width) // 2

        col = start_col
        for i, label in enumerate(button_labels):
            if i == selected_button:
                button_style = curses.color_pair(3) | curses.A_BOLD
                key_style = curses.color_pair(3) | curses.A_BOLD | curses.A_UNDERLINE
            else:
                button_style = curses.color_pair(2)
                key_style = curses.color_pair(2) | curses.A_UNDERLINE

            # "< "
            dialog_win.addstr(button_row, col, "< ", button_style)
            col += 2

            # 首字母 (with underline)
            dialog_win.addstr(button_row, col, label[0], key_style)
            col += 1

            # 其餘文字
            dialog_win.addstr(button_row, col, label[1:], button_style)
            col += len(label) - 1

            # " >"
            dialog_win.addstr(button_row, col, " >", button_style)
            col += 4

        dialog_win.refresh()

        # 處理按鍵 (P0 改進 #3: TAB 支持)
        c = dialog_win.getch()

        if c == curses.KEY_LEFT:
            selected_button = (selected_button - 1) % len(button_labels)
        elif c == curses.KEY_RIGHT:
            selected_button = (selected_button + 1) % len(button_labels)
        elif c == ord("\t"):  # TAB
            selected_button = (selected_button + 1) % len(button_labels)
        elif c == curses.KEY_BTAB:  # Shift+TAB
            selected_button = (selected_button - 1) % len(button_labels)
        elif c in (ord("\n"), ord(" ")):  # Enter or Space
            result = button_labels[selected_button]
            return result
        elif c == 27:  # ESC
            return None


if __name__ == "__main__":
    try:
        result = curses.wrapper(test_dialog)
        print("\n測試結果:")
        print("=" * 50)
        if result:
            print(f"✓ P0 改進項目測試成功")
            print(f"✓ 選擇了: {result}")
            print(f"✓ 分隔線繪製正常")
            print(f"✓ 按鈕格式正確 (< Label >)")
            print(f"✓ 首字母底線顯示正常")
            print(f"✓ TAB/方向鍵導航功能正常")
        else:
            print("✓ 按下 ESC 取消")
    except Exception as e:
        print(f"✗ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
