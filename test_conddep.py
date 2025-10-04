#!/usr/bin/env python3
"""Test conditional dependencies (depends on A if B)"""

from kconfiglib import Kconfig, expr_str


def test_conditional_dependencies():
    """Test the new 'depends on A if B' syntax"""

    print("Testing conditional dependencies (depends on A if B)")

    c = Kconfig("tests/Kconddep")

    # Test 1: "depends on A if B" should become "!B || A"
    result = expr_str(c.syms["COND_DEP_1"].direct_dep)
    expected = "!B || A"
    assert result == expected, f"COND_DEP_1: expected '{expected}', got '{result}'"
    print(f"✓ COND_DEP_1: {result}")

    # Test 2: "depends on (C && D) if E" should become "!E || (C && D)"
    result = expr_str(c.syms["COND_DEP_2"].direct_dep)
    expected = "!E || (C && D)"
    assert result == expected, f"COND_DEP_2: expected '{expected}', got '{result}'"
    print(f"✓ COND_DEP_2: {result}")

    # Test 3: Multiple depends combined: "depends on A", "depends on B if C", "depends on D"
    # Should become: "A && (!C || B) && D"
    result = expr_str(c.syms["COND_DEP_MIXED"].direct_dep)
    expected = "A && (!C || B) && D"
    assert result == expected, f"COND_DEP_MIXED: expected '{expected}', got '{result}'"
    print(f"✓ COND_DEP_MIXED: {result}")

    # Test 4: Test with choice
    result = expr_str(c.named_choices["COND_CHOICE"].direct_dep)
    expected = "!Y || X"
    assert result == expected, f"COND_CHOICE: expected '{expected}', got '{result}'"
    print(f"✓ COND_CHOICE: {result}")

    # Test 5: Multiple conditional dependencies
    result = expr_str(c.syms["MULTI_COND"].direct_dep)
    expected = "(!B || A) && (!D || C)"
    assert result == expected, f"MULTI_COND: expected '{expected}', got '{result}'"
    print(f"✓ MULTI_COND: {result}")

    print("\nAll tests passed!")


if __name__ == "__main__":
    test_conditional_dependencies()
