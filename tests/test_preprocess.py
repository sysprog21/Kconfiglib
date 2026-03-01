# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Preprocessor tests: variable expansion, user-defined functions, Kbuild
# toolchain test functions, and KCONFIG_WARN_UNDEF.

import os
import shutil
import sys

import pytest

from kconfiglib import (
    Kconfig,
    KconfigError,
    _success_fn,
    _failure_fn,
    _if_success_fn,
)
from conftest import verify_value, verify_str


def _verify_variable(c, name, unexp_value, exp_value, recursive, *args):
    """Check a preprocessor variable's unexpanded value,
    expanded_value_w_args(), and is_recursive flag."""
    var = c.variables[name]

    assert var.value == unexp_value, f"{name} unexpanded value"

    assert (
        var.expanded_value_w_args(*args) == exp_value
    ), f"{name} expanded_value_w_args"

    assert var.is_recursive == recursive, f"{name} is_recursive flag"


# ---------------------------------------------------------------------------
# Shared fixture: load Kpreprocess with the required environment variables
# ---------------------------------------------------------------------------


@pytest.fixture
def preprocess_kconfig(monkeypatch):
    """Load Kpreprocess with the expected environment variables set."""
    monkeypatch.setenv("ENV_1", "env_1")
    monkeypatch.setenv("ENV_2", "env_2")
    monkeypatch.setenv("ENV_3", "env_3")
    monkeypatch.setenv("ENV_4", "env_4")
    monkeypatch.setenv("ENV_5", "n")
    monkeypatch.setenv("ENV_6", "tests/empty")
    monkeypatch.setenv("ENV_7", "env_7")
    return Kconfig("tests/Kpreprocess", warn_to_stderr=False)


# ===========================================================================
# Preprocessor variable expansion
# ===========================================================================


def test_preprocessor_variables(preprocess_kconfig):
    c = preprocess_kconfig

    _verify_variable(c, "simple-recursive", "foo", "foo", True)
    _verify_variable(c, "simple-immediate", "bar", "bar", False)
    _verify_variable(c, "simple-recursive-2", "baz", "baz", True)

    _verify_variable(c, "whitespaced", "foo", "foo", True)

    _verify_variable(c, "preserve-recursive", "foo bar", "foo bar", True)
    _verify_variable(c, "preserve-immediate", "foo bar", "foo bar", False)

    _verify_variable(
        c,
        "recursive",
        "$(foo) $(bar) $($(b-char)a$(z-char)) $(indir)",
        "abc def ghi jkl mno",
        True,
    )

    _verify_variable(c, "immediate", "foofoo", "foofoo", False)

    _verify_variable(
        c,
        "messy-fn-res",
        "$($(fn-indir)-unused-arg, a  b (,) , c  d )",
        'surround-rev-quote " c  d " " a  b (,) " surround-rev-quote ',
        True,
    )

    _verify_variable(
        c,
        "special-chars-fn-res",
        "$(fn,$(comma)$(dollar)$(left-paren)foo$(right-paren))",
        '",$(foo)"',
        True,
    )

    _verify_variable(c, "quote", '"$(1)" "$(2)"', '"" ""', True)
    _verify_variable(c, "quote", '"$(1)" "$(2)"', '"one" ""', True, "one")
    _verify_variable(c, "quote", '"$(1)" "$(2)"', '"one" "two"', True, "one", "two")
    _verify_variable(
        c, "quote", '"$(1)" "$(2)"', '"one" "two"', True, "one", "two", "three"
    )


# ===========================================================================
# Preprocessor symbol __str__() output
# ===========================================================================


def test_preprocessor_symbols(preprocess_kconfig):
    c = preprocess_kconfig

    verify_str(
        c.syms["PRINT_ME"],
        r"""
config PRINT_ME
	string "env_1" if (FOO && BAR) || !BAZ || !QAZ
	default "\"foo\"" if "foo \"bar\" baz" = ""
""",
    )

    verify_str(
        c.syms["PRINT_ME_TOO"],
        r"""
config PRINT_ME_TOO
	bool "foo"
	default FOOBARBAZQAZ if QAZ && QAZFOO && xxx
""",
    )


# ===========================================================================
# Preprocessor variable __repr__()
# ===========================================================================


def test_preprocessor_variable_repr(preprocess_kconfig):
    c = preprocess_kconfig

    assert (
        repr(c.variables["simple-immediate"])
        == "<variable simple-immediate, immediate, value 'bar'>"
    )

    assert (
        repr(c.variables["messy-fn-res"])
        == "<variable messy-fn-res, recursive, value '$($(fn-indir)-unused-arg, a  b (,) , c  d )'>"
    )


# ===========================================================================
# Recursive expansion detection
# ===========================================================================


def test_preprocessor_recursive(preprocess_kconfig):
    c = preprocess_kconfig

    with pytest.raises(KconfigError):
        c.variables["rec-1"].expanded_value_w_args()

    # Indirectly verifies that it's not recursive
    _verify_variable(c, "safe-fn-rec-res", "$(safe-fn-rec,safe-fn-rec-2)", "foo", True)

    with pytest.raises(KconfigError):
        c.variables["unsafe-fn-rec"].expanded_value_w_args()


# ===========================================================================
# Miscellaneous preprocessor variables (shell, parens, location, warnings,
# errors, env_vars)
# ===========================================================================


def test_preprocessor_misc(preprocess_kconfig):
    c = preprocess_kconfig

    _verify_variable(c, "foo-bar-baz", "$(rhs)", "value", True)

    _verify_variable(c, "space-var-res", "$(foo bar)", "value", True)

    _verify_variable(
        c,
        "shell-res",
        "$(shell,false && echo foo bar || echo baz qaz)",
        "baz qaz",
        True,
    )

    _verify_variable(c, "shell-stderr-res", "", "", False)

    _verify_variable(
        c,
        "parens-res",
        "pre-$(shell,echo '(a,$(b-char),(c,d),e)')-post",
        "pre-(a,b,(c,d),e)-post",
        True,
    )

    _verify_variable(
        c,
        "location-res",
        "tests/Kpreprocess:129",
        "tests/Kpreprocess:129",
        False,
    )

    _verify_variable(c, "warning-res", "", "", False)
    _verify_variable(c, "error-n-res", "", "", False)

    with pytest.raises(KconfigError):
        c.variables["error-y-res"].expanded_value_w_args()

    # Check Kconfig.env_vars
    assert c.env_vars == {"ENV_1", "ENV_2", "ENV_3", "ENV_4", "ENV_5", "ENV_6"}

    # Check that the expected warnings were generated
    assert c.warnings == [
        "tests/Kpreprocess:122: warning: 'echo message on stderr >&2' wrote to stderr: message on stderr",
        "tests/Kpreprocess:134: warning: a warning",
    ]


# ===========================================================================
# User-defined preprocessor functions
# ===========================================================================


def test_user_defined_functions(monkeypatch):
    # Make tests/kconfigfunctions.py importable
    monkeypatch.syspath_prepend("tests")
    c = Kconfig("tests/Kuserfunctions")

    _verify_variable(c, "add-zero", "$(add)", "0", True)
    _verify_variable(c, "add-one", "$(add,1)", "1", True)
    _verify_variable(c, "add-three", "$(add,1,-1,2,1)", "3", True)

    _verify_variable(c, "one-one", "$(one,foo bar)", "onefoo barfoo bar", True)

    _verify_variable(c, "one-or-more-one", "$(one-or-more,foo)", "foo + ", True)
    _verify_variable(
        c, "one-or-more-three", "$(one-or-more,foo,bar,baz)", "foo + bar,baz", True
    )

    _verify_variable(
        c,
        "location-1",
        "tests/Kuserfunctions:13",
        "tests/Kuserfunctions:13",
        False,
    )
    _verify_variable(
        c,
        "location-2",
        "tests/Kuserfunctions:14",
        "tests/Kuserfunctions:14",
        False,
    )

    with pytest.raises(KconfigError):
        c.variables["one-zero"].expanded_value_w_args()

    with pytest.raises(KconfigError):
        c.variables["one-two"].expanded_value_w_args()

    with pytest.raises(KconfigError):
        c.variables["one-or-more-zero"].expanded_value_w_args()


# ===========================================================================
# Kbuild toolchain test functions
# ===========================================================================


def test_kbuild_functions(monkeypatch):
    cc = (
        os.environ.get("CC")
        or shutil.which("cc")
        or shutil.which("gcc")
        or shutil.which("clang")
    )
    if not cc:
        pytest.skip("no C compiler found")
    monkeypatch.setenv("CC", cc)
    c = Kconfig("tests/Kbuild_functions")

    # $(python,...) tests
    verify_value(c, "TEST_PYTHON_SUCCESS", "y")
    verify_value(c, "TEST_PYTHON_ASSERT_PASS", "y")
    verify_value(c, "TEST_PYTHON_ASSERT_FAIL", "n")
    verify_value(c, "TEST_PYTHON_ENV", "y")
    verify_value(c, "TEST_PYTHON_WHICH", "y")
    verify_value(c, "TEST_PYTHON_RUN", "y")
    verify_value(c, "TEST_PYTHON_RUN_FAIL", "y")

    # Quote tracking -- commas/parens inside quotes must not
    # split macro arguments
    verify_value(c, "TEST_PYTHON_QUOTE_COMMA", "y")
    verify_value(c, "TEST_PYTHON_QUOTE_PAREN", "y")
    verify_value(c, "TEST_PYTHON_SINGLE_QUOTE", "y")
    verify_value(c, "TEST_PYTHON_ESCAPED_QUOTE", "y")
    verify_value(c, "TEST_PYTHON_TRIPLE_QUOTE", "y")
    verify_value(c, "TEST_PYTHON_TRIPLE_SINGLE", "y")
    verify_value(c, "TEST_PYTHON_MACRO_BEFORE_ESCAPE", "y")

    # Toolchain function tests (shell-free via _run_argv)
    verify_value(c, "CC_HAS_WALL", "y")
    verify_value(c, "CC_HAS_WERROR", "y")
    verify_value(c, "CC_HAS_FSTACK_PROTECTOR", "y")
    verify_value(c, "AS_HAS_NOP", "y")
    verify_value(c, "TEST_INVALID_OPTION", "n")

    # ld-option: result is platform-dependent (Apple ld rejects
    # --version), just verify the symbol was evaluated
    assert c.syms["LD_HAS_VERSION"].str_value in ("y", "n")

    # cc-option-bit returns the flag itself (string) or ""
    val = c.syms["CC_STACK_USAGE_FLAG"].str_value
    assert val in (
        "-fstack-usage",
        "",
    ), "CC_STACK_USAGE_FLAG should be the flag or empty"

    # AS_HAS_MOVQ (x86-64 only) and AS_HAS_CUSTOM_FLAG
    # (-march=native, compiler-dependent) are intentionally not
    # asserted here -- results vary by architecture and toolchain.


@pytest.fixture(scope="module")
def kbuild_kconfig():
    """Load Kbuild_functions once per module -- avoids repeated
    subprocess toolchain probes across python_fn tests."""
    return Kconfig("tests/Kbuild_functions", warn_to_stderr=False)


def test_success_failure_fns():
    """Test success/failure/if-success functions directly with
    sys.executable as a portable true/false replacement."""
    c = Kconfig("tests/Kbuild_functions")
    # Double-quote the path -- works in both bash (Unix) and cmd.exe
    # (Windows).  shlex.quote uses single quotes, which cmd.exe
    # does not understand.
    py = f'"{sys.executable}"'

    assert _success_fn(c, "success", py + ' -c ""') == "y"
    assert _success_fn(c, "success", py + ' -c "raise SystemExit(1)"') == "n"

    assert _failure_fn(c, "failure", py + ' -c ""') == "n"
    assert _failure_fn(c, "failure", py + ' -c "raise SystemExit(1)"') == "y"

    assert _if_success_fn(c, "if-success", py + ' -c ""', "yes", "no") == "yes"
    assert (
        _if_success_fn(c, "if-success", py + ' -c "raise SystemExit(1)"', "yes", "no")
        == "no"
    )


def test_python_fn_isolation(kbuild_kconfig):
    """Verify that assignments in one $(python,...) call do not leak
    into subsequent calls."""
    python_fn = kbuild_kconfig._functions["python"][0]
    c = kbuild_kconfig

    assert python_fn(c, "python", "leaked_var = 42") == "y"
    assert python_fn(c, "python", "assert 'leaked_var' not in dir()") == "y"


def test_python_fn_system_exit(kbuild_kconfig):
    """Verify SystemExit handling: exit(0) -> 'y', exit(1) -> 'n'."""
    python_fn = kbuild_kconfig._functions["python"][0]
    c = kbuild_kconfig

    assert python_fn(c, "python", "raise SystemExit(0)") == "y"
    assert python_fn(c, "python", "raise SystemExit(None)") == "y"
    assert python_fn(c, "python", "raise SystemExit(1)") == "n"
    assert python_fn(c, "python", "raise SystemExit('error')") == "n"

    # Falsy codes -> "y", truthy codes -> "n"
    assert python_fn(c, "python", 'raise SystemExit("")') == "y"
    assert python_fn(c, "python", "raise SystemExit([])") == "y"
    assert python_fn(c, "python", "raise SystemExit([1])") == "n"


def test_python_fn_warnings(kbuild_kconfig):
    """Verify that non-assertion exceptions generate warnings
    while AssertionError is silent."""
    c = kbuild_kconfig
    python_fn = c._functions["python"][0]

    # AssertionError: silent (expected for boolean checks)
    c.warnings.clear()
    assert python_fn(c, "python", "assert False") == "n"
    assert len(c.warnings) == 0

    # NameError: warns (typo in code string)
    c.warnings.clear()
    assert python_fn(c, "python", "nonexistent_var") == "n"
    assert len(c.warnings) == 1
    assert "NameError" in c.warnings[0]

    # SyntaxError: warns (malformed code)
    c.warnings.clear()
    assert python_fn(c, "python", "def") == "n"
    assert len(c.warnings) == 1
    assert "SyntaxError" in c.warnings[0]

    # Success: no warning
    c.warnings.clear()
    assert python_fn(c, "python", "x = 1") == "y"
    assert len(c.warnings) == 0


# ===========================================================================
# KCONFIG_WARN_UNDEF
# ===========================================================================


def test_kconfig_warn_undef(monkeypatch):
    monkeypatch.setenv("KCONFIG_WARN_UNDEF", "y")
    c = Kconfig("tests/Kundef", warn_to_stderr=False)

    assert "\n".join(c.warnings) == """
warning: the int symbol INT (defined at tests/Kundef:8) has a non-int range [UNDEF_2 (undefined), 8 (undefined)]
warning: undefined symbol UNDEF_1:

- Referenced at tests/Kundef:4:

config BOOL
\tbool "foo" if DEF || !UNDEF_1
\tdefault UNDEF_2

- Referenced at tests/Kundef:19:

menu "menu"
\tdepends on UNDEF_1
\tvisible if UNDEF_3
warning: undefined symbol UNDEF_2:

- Referenced at tests/Kundef:4:

config BOOL
\tbool "foo" if DEF || !UNDEF_1
\tdefault UNDEF_2

- Referenced at tests/Kundef:8:

config INT
\tint
\trange UNDEF_2 8
\trange 5 15
\tdefault 10
warning: undefined symbol UNDEF_3:

- Referenced at tests/Kundef:19:

menu "menu"
\tdepends on UNDEF_1
\tvisible if UNDEF_3
"""[1:-1]
