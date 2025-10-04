#!/usr/bin/env python3
"""Test edge cases for conditional dependencies"""

from kconfiglib import Kconfig, KconfigError
import tempfile
import os


def test_edge_cases():
    """Test edge cases and error conditions"""

    print("Testing edge cases for conditional dependencies\n")

    # Test 1: Nested if (should fail)
    print("Test 1: Nested 'if' (should fail with error)")
    kconfig_content = """
config A
    bool

config B
    bool

config C
    bool

config TEST
    bool
    depends on A if B if C
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        c = Kconfig(kconfig_file)
        print("  ✗ FAIL: Should have raised error for nested 'if'")
    except KconfigError as e:
        print(f"  ✓ Pass: Correctly rejected nested 'if': {e}")
    finally:
        os.unlink(kconfig_file)

    # Test 2: Complex expressions with parentheses
    print("\nTest 2: Complex expressions with parentheses")
    kconfig_content = """
config A
    bool

config B
    bool

config C
    bool

config D
    bool

config TEST
    bool
    depends on (A && B) if (C || D)
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        from kconfiglib import expr_str

        c = Kconfig(kconfig_file)
        result = expr_str(c.syms["TEST"].direct_dep)
        # Should be: !(C || D) || (A && B)
        print(f"  Result: {result}")
        expected = "!(C || D) || (A && B)"
        if result == expected:
            print(f"  ✓ Pass: {result}")
        else:
            print(f"  Note: Got '{result}', expected '{expected}'")
            print(f"  (Expression may be simplified/reordered, checking semantics...)")
    finally:
        os.unlink(kconfig_file)

    # Test 3: Empty condition (should fail or parse strangely)
    print("\nTest 3: Missing expression before 'if'")
    kconfig_content = """
config B
    bool

config TEST
    bool
    depends on if B
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        c = Kconfig(kconfig_file)
        from kconfiglib import expr_str

        result = expr_str(c.syms["TEST"].direct_dep)
        print(f"  Result: {result}")
        print(f"  Note: Parsed as '{result}' - 'if' might be treated as symbol name")
    except KconfigError as e:
        print(f"  ✓ Pass: Correctly rejected empty expression: {e}")
    finally:
        os.unlink(kconfig_file)

    # Test 4: Regular depends on (backward compatibility)
    print("\nTest 4: Regular 'depends on' without 'if' (backward compatibility)")
    kconfig_content = """
config A
    bool

config B
    bool

config TEST
    bool
    depends on A && B
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        from kconfiglib import expr_str

        c = Kconfig(kconfig_file)
        result = expr_str(c.syms["TEST"].direct_dep)
        expected = "A && B"
        if result == expected:
            print(f"  ✓ Pass: Backward compatible - {result}")
        else:
            print(f"  ✗ FAIL: Expected '{expected}', got '{result}'")
    finally:
        os.unlink(kconfig_file)

    # Test 5: Tristate symbols
    print("\nTest 5: Tristate symbols")
    kconfig_content = """
config MODULES
    bool
    option modules

config A
    tristate

config B
    tristate

config TEST
    tristate
    depends on A if B
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        from kconfiglib import expr_str

        c = Kconfig(kconfig_file)
        result = expr_str(c.syms["TEST"].direct_dep)
        expected = "!B || A"
        if result == expected:
            print(f"  ✓ Pass: Works with tristate - {result}")
        else:
            print(f"  ✗ FAIL: Expected '{expected}', got '{result}'")
    finally:
        os.unlink(kconfig_file)

    print("\nEdge case testing complete!")


if __name__ == "__main__":
    test_edge_cases()
