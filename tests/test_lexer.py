# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Tests for string literal lexing, escape/unescape, and _ordered_unique.
# Lexer tests: escape/unescape, _ordered_unique.

import pytest

from kconfiglib import Kconfig, KconfigError, escape, unescape, _ordered_unique

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_string_lex(c, s, expected):
    """Tokenize a string literal and check the resulting constant symbol name."""
    res = c._tokenize("if " + s)[1].name
    assert (
        res == expected
    ), f"expected <{s[1:-1]}> to produce the constant symbol <{expected}>, got <{res}>"


def _verify_string_bad(c, s):
    """Assert that evaluating a malformed string literal raises KconfigError."""
    with pytest.raises(KconfigError):
        c.eval_string(s)


def _verify_escape_unescape(s, sesc):
    """Assert that escape(s) == sesc and unescape(sesc) == s."""
    assert escape(s) == sesc, f"escape({s!r}) == {escape(s)!r}, expected {sesc!r}"
    assert (
        unescape(sesc) == s
    ), f"unescape({sesc!r}) == {unescape(sesc)!r}, expected {s!r}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_string_literal_lexing():
    """Verify that string literals are lexed into the expected constant
    symbols."""
    c = Kconfig("tests/empty")
    lex = _verify_string_lex

    # Empty strings
    lex(c, r""" "" """, "")
    lex(c, r""" '' """, "")

    # Simple content
    lex(c, r""" "a" """, "a")
    lex(c, r""" 'a' """, "a")
    lex(c, r""" "ab" """, "ab")
    lex(c, r""" 'ab' """, "ab")
    lex(c, r""" "abc" """, "abc")
    lex(c, r""" 'abc' """, "abc")

    # Opposite quote inside
    lex(c, r""" "'" """, "'")
    lex(c, r""" '"' """, '"')

    # Escaped own quote
    lex(c, r""" "\"" """, '"')
    lex(c, r""" '\'' """, "'")

    # Double escaped own quote
    lex(c, r""" "\"\"" """, '""')
    lex(c, r""" '\'\'' """, "''")

    # Escaped opposite quote (treated as literal)
    lex(c, r""" "\'" """, "'")
    lex(c, r""" '\"' """, '"')

    # Escaped backslash
    lex(c, r""" "\\" """, "\\")
    lex(c, r""" '\\' """, "\\")

    # Mixed escapes
    lex(c, r""" "\a\\'\b\c\"'d" """, "a\\'bc\"'d")
    lex(c, r""" '\a\\"\b\c\'"d' """, 'a\\"bc\'"d')


def test_string_bad_lexing():
    """Verify that malformed string literals raise KconfigError."""
    c = Kconfig("tests/empty")

    for s in [
        r""" " """,
        r""" ' """,
        r""" "' """,
        r""" '" """,
        r""" "\" """,
        r""" '\' """,
        r""" "foo """,
        r""" 'foo """,
    ]:
        _verify_string_bad(c, s)


def test_escape_unescape():
    """Verify that escape() and unescape() are inverses and handle edge
    cases correctly."""
    _verify_escape_unescape(r"", r"")
    _verify_escape_unescape(r"foo", r"foo")
    _verify_escape_unescape(r'"', r"\"")
    _verify_escape_unescape(r'""', r"\"\"")
    _verify_escape_unescape("\\", r"\\")
    _verify_escape_unescape(r"\\", r"\\\\")
    _verify_escape_unescape(r"\"", r"\\\"")
    _verify_escape_unescape(r'"ab\cd"ef"', r"\"ab\\cd\"ef\"")

    # Backslashes before any character should be unescaped, not just " and \
    assert unescape(r"\afoo\b\c\\d\\\e\\\\f") == r"afoobc\d\e\\f"


def test_ordered_unique():
    """Verify _ordered_unique() preserves first-occurrence order and removes
    duplicates."""
    assert _ordered_unique([]) == []
    assert _ordered_unique([1]) == [1]
    assert _ordered_unique([1, 2]) == [1, 2]
    assert _ordered_unique([1, 1]) == [1]
    assert _ordered_unique([1, 1, 2]) == [1, 2]
    assert _ordered_unique([1, 2, 1]) == [1, 2]
    assert _ordered_unique([1, 2, 2]) == [1, 2]
    assert _ordered_unique([1, 2, 3, 2, 1, 2, 3, 4, 3, 2, 1, 0]) == [1, 2, 3, 4, 0]
