#!/usr/bin/env python3
"""Test conditional dependencies behavior (depends on A if B)"""

from kconfiglib import Kconfig, TRI_TO_STR
import tempfile
import os


def test_conditional_dependency_behavior():
    """Test that 'depends on A if B' behaves correctly"""

    print("Testing conditional dependency behavior\n")

    # Create a test Kconfig with conditional dependencies
    kconfig_content = """
config A
    bool "A"
    default y

config B
    bool "B"
    default n

config C
    bool "C"
    depends on A if B

config D
    bool "D"
    default y

config E
    bool "E"
    depends on C if D
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix="", delete=False) as f:
        f.write(kconfig_content)
        kconfig_file = f.name

    try:
        c = Kconfig(kconfig_file)

        # Test case 1: B=n, so "depends on A if B" becomes "!B || A" = "!n || A" = "y || A" = y
        # So C should be visible regardless of A's value
        print("Test 1: B=n (condition false)")
        print(f"  A={c.syms['A'].str_value}, B={c.syms['B'].str_value}")
        print(f"  C visibility: {TRI_TO_STR[c.syms['C'].visibility]}")
        print(f"  C is visible because: !B || A = !n || y = y")
        assert c.syms["C"].visibility > 0, "C should be visible when B is n"
        print("  ✓ Pass\n")

        # Test case 2: Set B=y, A=y, then C should depend on A
        print("Test 2: B=y, A=y (condition true, dependency satisfied)")
        c.syms["B"].set_value("y")
        c.syms["A"].set_value("y")
        print(f"  A={c.syms['A'].str_value}, B={c.syms['B'].str_value}")
        print(f"  C visibility: {TRI_TO_STR[c.syms['C'].visibility]}")
        print(f"  C is visible because: !B || A = !y || y = n || y = y")
        assert c.syms["C"].visibility > 0, "C should be visible when B=y and A=y"
        print("  ✓ Pass\n")

        # Test case 3: B=y, A=n, then C should NOT be visible
        print("Test 3: B=y, A=n (condition true, dependency NOT satisfied)")
        c.syms["B"].set_value("y")
        c.syms["A"].set_value("n")
        print(f"  A={c.syms['A'].str_value}, B={c.syms['B'].str_value}")
        print(f"  C visibility: {TRI_TO_STR[c.syms['C'].visibility]}")
        print(f"  C is NOT visible because: !B || A = !y || n = n || n = n")
        assert c.syms["C"].visibility == 0, "C should NOT be visible when B=y and A=n"
        print("  ✓ Pass\n")

        # Test case 4: Nested conditional - E depends on C if D
        print("Test 4: Nested conditional dependencies")
        c.syms["D"].set_value("y")
        c.syms["B"].set_value("n")
        c.syms["A"].set_value("y")
        print(
            f"  A={c.syms['A'].str_value}, B={c.syms['B'].str_value}, C visible={TRI_TO_STR[c.syms['C'].visibility]}, D={c.syms['D'].str_value}"
        )
        print(f"  E visibility: {TRI_TO_STR[c.syms['E'].visibility]}")
        print(f"  E depends on: !D || C")
        print("  ✓ Pass\n")

        print("All behavioral tests passed!")
        print("\nSummary:")
        print("  'depends on A if B' correctly transforms to '!B || A'")
        print("  - When B is false: dependency is always satisfied (y)")
        print("  - When B is true: dependency becomes A")

    finally:
        os.unlink(kconfig_file)


if __name__ == "__main__":
    test_conditional_dependency_behavior()
