# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Expression evaluation, split_expr(), and expr_items() tests.

import pytest

from kconfiglib import (
    AND,
    OR,
    Kconfig,
    KconfigError,
    expr_items,
    expr_str,
    expr_value,
    split_expr,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _eval(c, expr, expected):
    """Assert that c.eval_string(expr) returns *expected*."""
    res = c.eval_string(expr)
    assert res == expected, f"Expression '{expr}' evaluation"


def _parse_expr(c, text):
    """Use the internal tokenizer to parse an expression string."""
    c._tokens = c._tokenize("if " + text)[1:]
    c._tokens_i = 0
    return c._parse_expr(False)


def _verify_split(c, cases, op):
    """Verify split_expr() for a list of (input, expected_parts) cases."""
    op_name = "OR" if op is OR else "AND"
    for to_split, expected_strs in cases:
        operands = split_expr(_parse_expr(c, to_split), op)
        assert len(operands) == len(
            expected_strs
        ), f"split_expr '{to_split}' by {op_name}"
        for operand, operand_str in zip(operands, expected_strs):
            assert expr_str(operand) == operand_str


# ---------------------------------------------------------------------------
# Expression evaluation: no modules
# ---------------------------------------------------------------------------


def test_eval_no_modules():
    c = Kconfig("tests/Keval", warn=False)

    _eval(c, "n", 0)
    _eval(c, "m", 0)
    _eval(c, "y", 2)
    _eval(c, "'n'", 0)
    _eval(c, "'m'", 0)
    _eval(c, "'y'", 2)
    _eval(c, "M", 2)


# ---------------------------------------------------------------------------
# Expression evaluation: modules enabled
# ---------------------------------------------------------------------------


def test_eval_with_modules():
    c = Kconfig("tests/Keval", warn=False)
    c.modules.set_value(2)

    # Basic tristate
    _eval(c, "n", 0)
    _eval(c, "m", 1)
    _eval(c, "y", 2)
    _eval(c, "'n'", 0)
    _eval(c, "'m'", 1)
    _eval(c, "'y'", 2)
    _eval(c, "M", 1)
    _eval(c, "(Y || N) && (m && y)", 1)

    # Non-bool/non-tristate symbols are always n in a tristate sense
    _eval(c, "Y_STRING", 0)
    _eval(c, "Y_STRING || m", 1)

    # Constants besides y and m
    _eval(c, '"foo"', 0)
    _eval(c, '"foo" || "bar"', 0)
    _eval(c, '"foo" || m', 1)

    # --- equality for N ---
    _eval(c, "N = N", 2)
    _eval(c, "N = n", 2)
    _eval(c, "N = 'n'", 2)
    _eval(c, "N != N", 0)
    _eval(c, "N != n", 0)
    _eval(c, "N != 'n'", 0)

    # --- equality for M ---
    _eval(c, "M = M", 2)
    _eval(c, "M = m", 2)
    _eval(c, "M = 'm'", 2)
    _eval(c, "M != M", 0)
    _eval(c, "M != m", 0)
    _eval(c, "M != 'm'", 0)

    # --- equality for Y ---
    _eval(c, "Y = Y", 2)
    _eval(c, "Y = y", 2)
    _eval(c, "Y = 'y'", 2)
    _eval(c, "Y != Y", 0)
    _eval(c, "Y != y", 0)
    _eval(c, "Y != 'y'", 0)

    # --- cross inequalities ---
    _eval(c, "N != M", 2)
    _eval(c, "N != Y", 2)
    _eval(c, "M != Y", 2)

    # --- string / int / hex equality ---
    _eval(c, "Y_STRING = y", 2)
    _eval(c, "Y_STRING = 'y'", 2)
    _eval(c, 'FOO_BAR_STRING = "foo bar"', 2)
    _eval(c, 'FOO_BAR_STRING != "foo bar baz"', 2)
    _eval(c, "INT_37 = 37", 2)
    _eval(c, "INT_37 = '37'", 2)
    _eval(c, "HEX_0X37 = 0x37", 2)
    _eval(c, "HEX_0X37 = '0x37'", 2)

    # After 31847b67 (kconfig: allow use of relations other than (in)equality)
    _eval(c, "HEX_0X37 = '0x037'", 2)
    _eval(c, "HEX_0X37 = '0x0037'", 2)

    # --- constant symbol comparisons ---
    _eval(c, '"foo" != "bar"', 2)
    _eval(c, '"foo" = "bar"', 0)
    _eval(c, '"foo" = "foo"', 2)

    # --- undefined symbols (get their name as their value) ---
    c.warn = False
    _eval(c, "'not_defined' = not_defined", 2)
    _eval(c, "not_defined_2 = not_defined_2", 2)
    _eval(c, "not_defined_1 != not_defined_2", 2)

    # --- less than / greater than: basic ---
    _eval(c, "INT_37 < 38", 2)
    _eval(c, "38 < INT_37", 0)
    _eval(c, "INT_37 < '38'", 2)
    _eval(c, "'38' < INT_37", 0)
    _eval(c, "INT_37 < 138", 2)
    _eval(c, "138 < INT_37", 0)
    _eval(c, "INT_37 < '138'", 2)
    _eval(c, "'138' < INT_37", 0)
    _eval(c, "INT_37 < -138", 0)
    _eval(c, "-138 < INT_37", 2)
    _eval(c, "INT_37 < '-138'", 0)
    _eval(c, "'-138' < INT_37", 2)
    _eval(c, "INT_37 < 37", 0)
    _eval(c, "37 < INT_37", 0)
    _eval(c, "INT_37 < 36", 0)
    _eval(c, "36 < INT_37", 2)

    # --- different formats in comparison ---
    _eval(c, "INT_37 < 0x26", 2)  # 0x26 == 38
    _eval(c, "INT_37 < 0x25", 0)  # 0x25 == 37
    _eval(c, "INT_37 < 0x24", 0)  # 0x24 == 36
    _eval(c, "HEX_0X37 < 56", 2)  # 56 == 0x38
    _eval(c, "HEX_0X37 < 55", 0)  # 55 == 0x37
    _eval(c, "HEX_0X37 < 54", 0)  # 54 == 0x36

    # --- other int comparisons ---
    _eval(c, "INT_37 <= 38", 2)
    _eval(c, "INT_37 <= 37", 2)
    _eval(c, "INT_37 <= 36", 0)
    _eval(c, "INT_37 >  38", 0)
    _eval(c, "INT_37 >  37", 0)
    _eval(c, "INT_37 >  36", 2)
    _eval(c, "INT_37 >= 38", 0)
    _eval(c, "INT_37 >= 37", 2)
    _eval(c, "INT_37 >= 36", 2)

    # --- other hex comparisons ---
    _eval(c, "HEX_0X37 <= 0x38", 2)
    _eval(c, "HEX_0X37 <= 0x37", 2)
    _eval(c, "HEX_0X37 <= 0x36", 0)
    _eval(c, "HEX_0X37 >  0x38", 0)
    _eval(c, "HEX_0X37 >  0x37", 0)
    _eval(c, "HEX_0X37 >  0x36", 2)
    _eval(c, "HEX_0X37 >= 0x38", 0)
    _eval(c, "HEX_0X37 >= 0x37", 2)
    _eval(c, "HEX_0X37 >= 0x36", 2)

    # --- hex without 0x prefix ---
    _eval(c, "HEX_37 < 0x38", 2)
    _eval(c, "HEX_37 < 0x37", 0)
    _eval(c, "HEX_37 < 0x36", 0)

    # --- symbol-to-symbol comparisons ---
    _eval(c, "INT_37   <  HEX_0X37", 2)
    _eval(c, "INT_37   >  HEX_0X37", 0)
    _eval(c, "HEX_0X37 <  INT_37  ", 0)
    _eval(c, "HEX_0X37 >  INT_37  ", 2)
    _eval(c, "INT_37   <  INT_37  ", 0)
    _eval(c, "INT_37   <= INT_37  ", 2)
    _eval(c, "INT_37   >  INT_37  ", 0)
    _eval(c, "INT_37   >= INT_37  ", 2)

    # --- tristate value comparisons ---
    _eval(c, "n < n", 0)
    _eval(c, "n < m", 2)
    _eval(c, "n < y", 2)
    _eval(c, "n < N", 0)
    _eval(c, "n < M", 2)
    _eval(c, "n < Y", 2)
    _eval(c, "0 > n", 0)
    _eval(c, "1 > n", 2)
    _eval(c, "2 > n", 2)
    _eval(c, "m < n", 0)
    _eval(c, "m < m", 0)
    _eval(c, "m < y", 2)

    # --- strings compare lexicographically ---
    _eval(c, "'aa' < 'ab'", 2)
    _eval(c, "'aa' > 'ab'", 0)
    _eval(c, "'ab' < 'aa'", 0)
    _eval(c, "'ab' > 'aa'", 2)

    # --- non-number operand falls back to lexicographic ---
    _eval(c, "INT_37 <  '37a' ", 2)
    _eval(c, "'37a'  >  INT_37", 2)
    _eval(c, "INT_37 <= '37a' ", 2)
    _eval(c, "'37a'  >= INT_37", 2)
    _eval(c, "INT_37 >= '37a' ", 0)
    _eval(c, "INT_37 >  '37a' ", 0)
    _eval(c, "'37a'  <  INT_37", 0)
    _eval(c, "'37a'  <= INT_37", 0)


# ---------------------------------------------------------------------------
# Bad expression evaluation
# ---------------------------------------------------------------------------

_BAD_EXPRS = [
    "",
    "&",
    "|",
    "!",
    "(",
    ")",
    "=",
    "(X",
    "X)",
    "X X",
    "!X X",
    "X !X",
    "(X) X",
    "X &&",
    "&& X",
    "X && && X",
    "X && !&&",
    "X ||",
    "|| X",
]


def test_eval_bad():
    c = Kconfig("tests/Keval", warn=False)
    c.modules.set_value(2)

    for expr in _BAD_EXPRS:
        with pytest.raises(KconfigError):
            c.eval_string(expr)


# ---------------------------------------------------------------------------
# split_expr()
# ---------------------------------------------------------------------------


def test_split_expr_or():
    c = Kconfig("tests/empty")
    c.warn = False

    _verify_split(
        c,
        [
            ("A", ("A",)),
            ("!A", ("!A",)),
            ("A = B", ("A = B",)),
            ("A && B", ("A && B",)),
            ("A || B", ("A", "B")),
            ("(A || B) || C", ("A", "B", "C")),
            ("A || (B || C)", ("A", "B", "C")),
            ("A || !(B || C)", ("A", "!(B || C)")),
            ("A || (B && (C || D))", ("A", "B && (C || D)")),
            ("(A && (B || C)) || D", ("A && (B || C)", "D")),
        ],
        OR,
    )


def test_split_expr_and():
    c = Kconfig("tests/empty")
    c.warn = False

    _verify_split(
        c,
        [
            ("A", ("A",)),
            ("!A", ("!A",)),
            ("A = B", ("A = B",)),
            ("A || B", ("A || B",)),
            ("A && B", ("A", "B")),
            ("(A && B) && C", ("A", "B", "C")),
            ("A && (B && C)", ("A", "B", "C")),
            ("A && !(B && C)", ("A", "!(B && C)")),
            ("A && (B || (C && D))", ("A", "B || (C && D)")),
            ("(A || (B && C)) && D", ("A || (B && C)", "D")),
        ],
        AND,
    )


# ---------------------------------------------------------------------------
# expr_items()
# ---------------------------------------------------------------------------


def test_expr_items():
    c = Kconfig("tests/Kexpr_items")

    items = expr_items(c.syms["TEST"].defaults[0][0])
    assert tuple(sorted(item.name for item in items)) == (
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
    )

    items = expr_items(c.syms["TEST_CHOICE"].nodes[0].prompt[1])
    assert tuple(sorted(item.name for item in items)) == ("A", "CHOICE")


# ---------------------------------------------------------------------------
# expr_value() on parsed expressions
# ---------------------------------------------------------------------------


def test_expr_value():
    c = Kconfig("tests/Keval", warn=False)
    c.modules.set_value(2)

    # Direct symbol tristate values
    assert expr_value(c.syms["N"]) == 0
    assert expr_value(c.syms["M"]) == 1
    assert expr_value(c.syms["Y"]) == 2

    # AND/OR/NOT on parsed expression trees
    and_expr = _parse_expr(c, "Y && M")
    assert expr_value(and_expr) == 1  # min(2, 1)

    or_expr = _parse_expr(c, "N || M")
    assert expr_value(or_expr) == 1  # max(0, 1)

    not_expr = _parse_expr(c, "!M")
    assert expr_value(not_expr) == 1  # 2 - 1

    not_n = _parse_expr(c, "!N")
    assert expr_value(not_n) == 2  # 2 - 0

    not_y = _parse_expr(c, "!Y")
    assert expr_value(not_y) == 0  # 2 - 2

    # Nested: (Y && M) || N  -> max(min(2,1), 0) = 1
    nested = _parse_expr(c, "(Y && M) || N")
    assert expr_value(nested) == 1

    # Relation operators on int/hex symbols
    eq_expr = _parse_expr(c, "INT_37 = 37")
    assert expr_value(eq_expr) == 2

    neq_expr = _parse_expr(c, "INT_37 != 37")
    assert expr_value(neq_expr) == 0

    lt_expr = _parse_expr(c, "INT_37 < 38")
    assert expr_value(lt_expr) == 2

    gt_expr = _parse_expr(c, "INT_37 > 38")
    assert expr_value(gt_expr) == 0

    le_expr = _parse_expr(c, "INT_37 <= 37")
    assert expr_value(le_expr) == 2

    ge_expr = _parse_expr(c, "INT_37 >= 38")
    assert expr_value(ge_expr) == 0

    # Comparison against constant (quoted) symbol
    str_eq = _parse_expr(c, 'FOO_BAR_STRING = "foo bar"')
    assert expr_value(str_eq) == 2

    str_neq = _parse_expr(c, 'FOO_BAR_STRING = "wrong"')
    assert expr_value(str_neq) == 0
