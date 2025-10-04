#!/usr/bin/env python3
"""Test backward compatibility after adding conditional dependency support"""

from kconfiglib import Kconfig, expr_str


def test_backward_compatibility():
    """Verify that existing Kconfig files still parse correctly"""

    print("Testing backward compatibility\n")

    # Test 1: Existing test files still work
    print("Test 1: Existing dependency tests (tests/Kdirdep)")
    c = Kconfig("tests/Kdirdep")

    result = expr_str(c.syms["NO_DEP_SYM"].direct_dep)
    expected = "y"
    assert result == expected, f"NO_DEP_SYM: expected '{expected}', got '{result}'"
    print(f"  ✓ NO_DEP_SYM: {result}")

    result = expr_str(c.syms["DEP_SYM"].direct_dep)
    expected = "A || (B && C) || !D"
    assert result == expected, f"DEP_SYM: expected '{expected}', got '{result}'"
    print(f"  ✓ DEP_SYM: {result}")

    result = expr_str(c.named_choices["NO_DEP_CHOICE"].direct_dep)
    expected = "y"
    assert result == expected, f"NO_DEP_CHOICE: expected '{expected}', got '{result}'"
    print(f"  ✓ NO_DEP_CHOICE: {result}")

    result = expr_str(c.named_choices["DEP_CHOICE"].direct_dep)
    expected = "A || B || C"
    assert result == expected, f"DEP_CHOICE: expected '{expected}', got '{result}'"
    print(f"  ✓ DEP_CHOICE: {result}")

    # Test 2: Complex boolean expressions still work
    print("\nTest 2: Complex boolean expressions")
    import tempfile
    import os

    kconfig_content = """
config A
    bool

config B
    bool

config C
    bool

config D
    bool

config TEST1
    bool
    depends on A && B

config TEST2
    bool
    depends on A || B

config TEST3
    bool
    depends on !A

config TEST4
    bool
    depends on (A && B) || (C && D)

config TEST5
    bool
    depends on A
    depends on B
    depends on C
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        c = Kconfig(kconfig_file)

        tests = [
            ("TEST1", "A && B"),
            ("TEST2", "A || B"),
            ("TEST3", "!A"),
            ("TEST4", "(A && B) || (C && D)"),
            ("TEST5", "A && B && C"),
        ]

        for sym_name, expected in tests:
            result = expr_str(c.syms[sym_name].direct_dep)
            assert (
                result == expected
            ), f"{sym_name}: expected '{expected}', got '{result}'"
            print(f"  ✓ {sym_name}: {result}")

    finally:
        os.unlink(kconfig_file)

    # Test 3: 'if' in other contexts still works
    print("\nTest 3: 'if' in other contexts")

    kconfig_content = """
config A
    bool

config B
    bool

menu "Test Menu"
    visible if A

config TEST
    bool "test"

endmenu

if B

config TEST2
    bool "test2"

endif
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        c = Kconfig(kconfig_file)
        print(f"  ✓ 'visible if' still works")
        print(f"  ✓ 'if...endif' blocks still work")
        print(f"  ✓ Found {len(c.syms)} symbols")
    finally:
        os.unlink(kconfig_file)

    # Test 4: Prompts with conditions still work
    print("\nTest 4: Prompts with conditions")

    kconfig_content = """
config A
    bool

config B
    bool

config TEST
    bool "prompt" if A
    default y
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        c = Kconfig(kconfig_file)
        # Check that the prompt condition is parsed correctly
        prompt_cond = c.syms["TEST"].nodes[0].prompt[1]
        result = expr_str(prompt_cond)
        expected = "A"
        assert (
            result == expected
        ), f"Prompt condition: expected '{expected}', got '{result}'"
        print(f"  ✓ Prompt with 'if' condition: {result}")
    finally:
        os.unlink(kconfig_file)

    print("\n✓ All backward compatibility tests passed!")


if __name__ == "__main__":
    test_backward_compatibility()
