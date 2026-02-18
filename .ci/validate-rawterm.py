#!/usr/bin/env python3
"""Validate rawterm and menuconfig on all platforms.

Exercises rawterm Color/Style/Region compositing, Windows console API
(GetStdHandle/SetConsoleMode), Unix termios terminal init/close, and
menuconfig headless mode with style parsing.

Run from the project root: python .ci/validate-rawterm.py
"""

import os
import sys

# Ensure the project root (CWD) is on the import path, since Python
# adds the script's directory (.ci/) rather than CWD by default.
sys.path.insert(0, os.getcwd())

_IS_WINDOWS = os.name == "nt"


def check_rawterm_units():
    """rawterm Color, Style, Key, Box -- no terminal required."""
    from rawterm import Style, Color, Key, Box, NAMED_COLORS

    # Color construction and equality
    c1 = Color.RED
    c2 = Color.index(196)
    c3 = Color.rgb(255, 0, 0)
    assert c1 == Color.RED, "named color identity"
    assert c2 == Color.index(196), "index color identity"
    assert c3 == Color.rgb(255, 0, 0), "rgb color identity"
    assert c1 != c2, "named vs index differ"
    assert hash(c1) == hash(Color.RED), "color hash stable"
    assert Color.DEFAULT == Color.DEFAULT, "DEFAULT identity"

    # Style construction and attributes
    s1 = Style(fg=c1, bg=Color.DEFAULT)
    s2 = Style(fg=c1, bg=Color.DEFAULT, bold=True)
    assert s1 != s2, "bold changes style"
    assert s1 == Style(fg=c1, bg=Color.DEFAULT), "style equality"
    assert s2.bold is True, "bold attribute"
    assert s1.standout is False, "standout default"

    # Key constants exist
    for attr in (
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
        "HOME",
        "END",
        "PAGE_UP",
        "PAGE_DOWN",
        "BACKSPACE",
        "DELETE",
        "RESIZE",
    ):
        assert getattr(Key, attr) is not None, "Key." + attr

    # Box-drawing constants are single characters
    for attr in (
        "HLINE",
        "VLINE",
        "ULCORNER",
        "URCORNER",
        "LLCORNER",
        "LRCORNER",
        "LTEE",
        "RTEE",
        "UARROW",
        "DARROW",
        "RARROW",
    ):
        ch = getattr(Box, attr)
        assert isinstance(ch, str) and len(ch) == 1, "Box." + attr

    # NAMED_COLORS has the 16 standard colors
    for name in (
        "black",
        "red",
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "white",
    ):
        assert name in NAMED_COLORS, "missing " + name
        assert "bright" + name in NAMED_COLORS, "missing bright" + name

    print("rawterm unit checks passed")


def _windows_has_console():
    """Probe whether real Windows console handles are available.

    Returns True if GetStdHandle/GetConsoleMode succeed on stdout,
    meaning we have a native console (cmd/powershell) rather than a
    mintty/MSYS2 PTY that lacks Win32 console handles.
    """
    if not _IS_WINDOWS:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        if handle == -1 or handle == 0:
            return False
        mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return True
    except (OSError, AttributeError):
        return False


def check_windows_console():
    """Validate Windows console API at the ctypes level.

    Tests GetStdHandle, GetConsoleMode, SetConsoleMode VT100 toggle
    without entering alternate screen or changing terminal state
    permanently.  Only runs on Windows with a real console.
    """
    if not _IS_WINDOWS:
        print("Windows console checks skipped (not Windows)")
        return

    if not _windows_has_console():
        print("Windows console checks skipped (no native console handle)")
        return

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32

    # Validate stdout handle
    STD_OUTPUT_HANDLE = -11
    STD_INPUT_HANDLE = -10
    stdout_h = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    stdin_h = kernel32.GetStdHandle(STD_INPUT_HANDLE)
    assert stdout_h not in (-1, 0, None), "invalid stdout handle"
    assert stdin_h not in (-1, 0, None), "invalid stdin handle"

    # Read current console modes
    out_mode = wintypes.DWORD()
    in_mode = wintypes.DWORD()
    assert kernel32.GetConsoleMode(
        stdout_h, ctypes.byref(out_mode)
    ), "GetConsoleMode(stdout) failed"
    assert kernel32.GetConsoleMode(
        stdin_h, ctypes.byref(in_mode)
    ), "GetConsoleMode(stdin) failed"

    # Toggle VT100 output processing on, then restore
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    new_out = out_mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
    assert kernel32.SetConsoleMode(
        stdout_h, new_out
    ), "SetConsoleMode(stdout, VT100) failed"
    # Restore original mode
    assert kernel32.SetConsoleMode(
        stdout_h, out_mode.value
    ), "SetConsoleMode(stdout, restore) failed"

    # Test VT100 input mode (may fail on older Windows -- not fatal)
    ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200
    new_in = (in_mode.value | ENABLE_VIRTUAL_TERMINAL_INPUT) & ~0x0007
    vt_input_ok = kernel32.SetConsoleMode(stdin_h, new_in)
    kernel32.SetConsoleMode(stdin_h, in_mode.value)  # always restore
    print(
        "  VT100 input: {}".format(
            "supported" if vt_input_ok else "not supported (ReadConsoleInputW fallback)"
        )
    )

    print("Windows console checks passed")


def check_terminal_init():
    """Terminal init/close -- full rawterm.Terminal lifecycle.

    On Unix, requires a real TTY on stdin/stdout.
    On Windows, requires native console handles (cmd/powershell, not
    MSYS2/mintty).  The workflow uses 'shell: cmd' on Windows to
    provide this.
    """
    from rawterm import Style, Color, Box

    if _IS_WINDOWS:
        can_init = _windows_has_console()
    else:
        can_init = os.isatty(sys.stdin.fileno()) and os.isatty(sys.stdout.fileno())

    if not can_init:
        reason = "no native console" if _IS_WINDOWS else "no TTY"
        print("Terminal init/close skipped ({})".format(reason))
        return

    from rawterm import Terminal

    term = Terminal()
    assert term.width > 0, "terminal width"
    assert term.height > 0, "terminal height"

    # Create a region and verify compositing operations
    reg = term.region(3, 10)
    reg.fill(Style(fg=Color.WHITE, bg=Color.BLACK))
    reg.write(0, 0, "test")
    reg.write_char(1, 0, Box.HLINE)
    assert reg._cells[0][0][0] == "t", "region write"
    reg.clear()
    assert reg._cells[0][0][0] == " ", "region clear"
    reg.move(1, 2)
    assert reg.y == 1 and reg.x == 2, "region move"
    reg.resize(5, 20)
    assert reg.height == 5 and reg.width == 20, "region resize"
    term.update()
    reg.close()
    term.close()
    print("Terminal init/close passed")


def check_menuconfig_headless():
    """menuconfig headless mode and style parsing."""
    from rawterm import Style, Color
    from kconfiglib import Kconfig
    import menuconfig

    kconf = Kconfig("examples/Kmenuconfig")
    menuconfig.menuconfig(kconf, headless=True)

    # Verify style parsing (exercises _parse_color, _style_from_def)
    menuconfig._init_styles()
    for key in (
        "body",
        "list",
        "screen",
        "frame",
        "selection",
        "border",
        "title",
        "edit",
        "help",
        "show-help",
    ):
        assert key in menuconfig._style, key + " style missing"
        assert isinstance(menuconfig._style[key], Style), key + " type"

    # Verify MENUCONFIG_STYLE env override (save/restore any existing value)
    old_mstyle = os.environ.get("MENUCONFIG_STYLE")
    os.environ["MENUCONFIG_STYLE"] = "selection=fg:red,bg:white,bold"
    menuconfig._style.clear()
    menuconfig._init_styles()
    sel = menuconfig._style["selection"]
    assert sel.fg == Color.RED, "MENUCONFIG_STYLE fg override"
    assert sel.bg == Color.WHITE, "MENUCONFIG_STYLE bg override"
    if old_mstyle is None:
        del os.environ["MENUCONFIG_STYLE"]
    else:
        os.environ["MENUCONFIG_STYLE"] = old_mstyle

    print("menuconfig headless + style validation passed")


if __name__ == "__main__":
    check_rawterm_units()
    check_windows_console()
    check_terminal_init()
    check_menuconfig_headless()
    print("All checks passed")
