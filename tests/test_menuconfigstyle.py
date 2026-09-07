# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Tests for menuconfig's style parser -- the MENUCONFIG_STYLE environment
# variable, which is the one piece of menuconfig configuration users write by
# hand and therefore the one most likely to be malformed.
#
# _parse_color(), _style_from_def() and _parse_style() are pure string
# handling, so they run without a terminal. Every branch here either produces a
# value or warns and falls back; nothing may raise, since a bad style string
# must not stop menuconfig from starting.

import pytest

import menuconfig
from rawterm import Color


@pytest.fixture
def warnings(monkeypatch):
    """Captures menuconfig._warn() output instead of writing to stderr."""
    captured = []
    monkeypatch.setattr(
        menuconfig, "_warn", lambda *args: captured.append(" ".join(map(str, args)))
    )
    return captured


# --- _parse_color -----------------------------------------------------------


def test_parse_color_html():
    assert menuconfig._parse_color("#FF8000") == Color.rgb(255, 128, 0)
    assert menuconfig._parse_color("#ff8000") == Color.rgb(255, 128, 0)


def test_parse_color_named():
    assert menuconfig._parse_color("red") == Color.RED
    assert menuconfig._parse_color("brightblue") == Color.BRIGHT_BLUE


@pytest.mark.parametrize(
    "text, index",
    [("0", 0), ("123", 123), ("255", 255), ("0x10", 16)],
)
def test_parse_color_index(text, index):
    """Plain and 0x-prefixed numbers both name a palette entry."""
    assert menuconfig._parse_color(text) == Color.index(index)


def test_parse_color_out_of_range_warns_and_falls_back(warnings):
    assert menuconfig._parse_color("256") == Color.DEFAULT
    assert menuconfig._parse_color("-1") == Color.DEFAULT
    assert len(warnings) == 2
    assert "outside range 0..255" in warnings[0]


def test_parse_color_unknown_warns_and_falls_back(warnings):
    assert menuconfig._parse_color("mauve") == Color.DEFAULT
    assert "neither predefined nor a number" in warnings[0]


def test_parse_color_near_miss_html_is_not_treated_as_html(warnings):
    """Five or seven hex digits is not #RRGGBB, and must not be read as one."""
    assert menuconfig._parse_color("#FF800") == Color.DEFAULT
    assert menuconfig._parse_color("#FF80000") == Color.DEFAULT
    assert len(warnings) == 2


# --- _style_from_def --------------------------------------------------------


def test_style_from_def_all_attributes():
    style = menuconfig._style_from_def("fg:red,bg:blue,bold,standout,underline")
    assert style.fg == Color.RED
    assert style.bg == Color.BLUE
    assert style.standout
    assert style.underline
    # 'bold' is dropped on Windows, where it renders as a bright color
    assert style.bold == (not menuconfig._IS_WINDOWS)


def test_style_from_def_empty_is_all_defaults():
    style = menuconfig._style_from_def("")
    assert style.fg == Color.DEFAULT
    assert style.bg == Color.DEFAULT
    assert not style.bold
    assert not style.standout
    assert not style.underline


def test_style_from_def_unknown_attribute_warns_but_keeps_the_rest(warnings):
    style = menuconfig._style_from_def("fg:red,blink,bg:blue")
    assert "blink" in warnings[0]
    assert style.fg == Color.RED
    assert style.bg == Color.BLUE


def test_style_from_def_accepts_colons_in_the_color(warnings):
    """Only the first colon separates, so a bad remainder still warns cleanly."""
    style = menuconfig._style_from_def("fg:not:a:color")
    assert style.fg == Color.DEFAULT
    assert warnings


# --- _parse_style -----------------------------------------------------------


@pytest.fixture
def style_table(monkeypatch):
    """A scratch _style dict, so tests can't corrupt the module's real one."""
    table = {"path": menuconfig._style_from_def("fg:white")}
    monkeypatch.setattr(menuconfig, "_style", table)
    return table


def test_parse_style_assignment(style_table, warnings):
    menuconfig._parse_style("path=fg:red,bold", parsing_default=False)
    assert style_table["path"].fg == Color.RED
    assert not warnings


def test_parse_style_reference_copies_another_entry(style_table, warnings):
    """'a=b' where b is an existing key copies b's style rather than parsing it."""
    menuconfig._parse_style("path=fg:green", parsing_default=False)
    style_table["other"] = menuconfig._style_from_def("fg:blue")
    menuconfig._parse_style("path=other", parsing_default=False)
    assert style_table["path"] is style_table["other"]


def test_parse_style_unknown_key_warns(style_table, warnings):
    menuconfig._parse_style("nosuchelement=fg:red", parsing_default=False)
    assert "nosuchelement" in warnings[0]
    # ...but the assignment still happens, matching the documented behavior
    assert "nosuchelement" in style_table


def test_parse_style_unknown_key_is_silent_while_parsing_defaults(
    style_table, warnings
):
    menuconfig._parse_style("nosuchelement=fg:red", parsing_default=True)
    assert not warnings


def test_parse_style_expands_a_builtin_template(style_table, warnings):
    """A bare word names a built-in style, inlined at that point."""
    menuconfig._parse_style("monochrome", parsing_default=True)
    assert len(style_table) > 1
    assert not warnings


def test_parse_style_unknown_template_warns(style_table, warnings):
    menuconfig._parse_style("nosuchtemplate", parsing_default=False)
    assert "nosuchtemplate" in warnings[0]


def test_parse_style_later_assignment_wins(style_table, warnings):
    menuconfig._parse_style("path=fg:red path=fg:blue", parsing_default=False)
    assert style_table["path"].fg == Color.BLUE


def test_shipped_styles_parse_without_warnings(monkeypatch, warnings):
    """Every built-in style must parse cleanly, or menuconfig warns on startup."""
    for name, definition in menuconfig._STYLES.items():
        monkeypatch.setattr(menuconfig, "_style", {})
        menuconfig._parse_style(definition, parsing_default=True)
        assert not warnings, f"built-in style {name!r} warned: {warnings}"
