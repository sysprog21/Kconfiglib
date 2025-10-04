#!/usr/bin/env python3
"""
檢查 menuconfig.py 的顏色設定是否符合 mconf
"""

import re

# 讀取 menuconfig.py 的顏色設定
with open("menuconfig.py", "r") as f:
    content = f.read()

# 提取 _STYLES["default"]
match = re.search(r'_STYLES = \{[^}]*"default": """([^"]+)"""', content, re.DOTALL)
if match:
    styles = match.group(1)
    print("Kconfiglib 顏色設定:")
    print("=" * 60)
    for line in styles.strip().split("\n"):
        line = line.strip()
        if line:
            print(f"  {line}")
    print()

# mconf 顏色對照表 (from util.c:61-89)
print("mconf bluetitle theme 對照:")
print("=" * 60)
mconf_colors = [
    ("screen", "CYAN", "BLUE", "bold"),
    ("dialog", "BLACK", "WHITE", ""),
    ("title", "YELLOW", "WHITE", "bold"),
    ("border", "WHITE", "WHITE", "bold"),
    ("button_active", "WHITE", "BLUE", "bold"),
    ("button_inactive", "BLACK", "WHITE", ""),
    ("item", "BLACK", "WHITE", ""),
    ("item_selected", "WHITE", "BLUE", "bold"),
    ("tag", "YELLOW", "WHITE", "bold"),
    ("uarrow/darrow", "GREEN", "WHITE", "bold"),
    ("menubox", "BLACK", "WHITE", ""),
    ("menubox_border", "WHITE", "WHITE", "bold"),
]

for name, fg, bg, attr in mconf_colors:
    attr_str = f",{attr}" if attr else ""
    print(f"  {name:20s} = fg:{fg.lower()},bg:{bg.lower()}{attr_str}")

print()
print("對應關係:")
print("=" * 60)
mappings = [
    ("screen", "→", "螢幕背景 (_stdscr.bkgd)"),
    ("dialog/item", "→", "list (fg:black,bg:white)"),
    ("border", "→", "frame (fg:white,bg:white,bold)"),
    ("item_selected", "→", "selection (fg:white,bg:blue,bold)"),
    ("tag", "→", "path/help (fg:yellow,bg:white,bold)"),
    ("uarrow/darrow", "→", "arrow (fg:green,bg:white,bold)"),
    ("title", "→", "path (fg:yellow,bg:white,bold)"),
]

for mconf, arrow, kconfiglib in mappings:
    print(f"  {mconf:20s} {arrow} {kconfiglib}")
