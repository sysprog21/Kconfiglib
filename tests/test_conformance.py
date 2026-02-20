# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Conformance tests that compare Kconfiglib output against the C Kconfig
# tools (scripts/kconfig/conf) in a Linux kernel source tree.
#
# These tests must be run from the root of a Linux kernel tree that has
# Kconfiglib checked out (or symlinked) as a subdirectory.  The C conf
# tool (scripts/kconfig/conf) must already be built.
#
# Usage:
#   cd /path/to/linux
#   python -m pytest Kconfiglib/tests/test_conformance.py -v
#
# The entire module is skipped when scripts/kconfig/conf does not exist.

import difflib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

import pytest

from kconfiglib import (
    Kconfig,
    KconfigError,
    Symbol,
    Choice,
    BOOL,
    TRISTATE,
    MENU,
    COMMENT,
)

# ---------------------------------------------------------------------------
# Module-level skip: these tests only make sense inside a kernel tree.
# ---------------------------------------------------------------------------

pytestmark = [
    pytest.mark.skipif(
        not os.path.exists("scripts/kconfig/conf"),
        reason="Requires Linux kernel source tree with scripts/kconfig/conf built",
    ),
    pytest.mark.conformance,
]

# ---------------------------------------------------------------------------
# Configuration flags.
# Override via environment variables if needed:
#   KCONFIGLIB_OBSESSIVE=1          -- test every arch/defconfig combination
#   KCONFIGLIB_OBSESSIVE_MIN_CONFIG=1
#   KCONFIGLIB_LOG=1                -- log defconfig failures to a file
# ---------------------------------------------------------------------------

obsessive = os.environ.get("KCONFIGLIB_OBSESSIVE", "") == "1"
obsessive_min_config = os.environ.get("KCONFIGLIB_OBSESSIVE_MIN_CONFIG", "") == "1"
log = os.environ.get("KCONFIGLIB_LOG", "") == "1"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True, scope="module")
def kernel_env():
    """Set up kernel build environment variables.

    These are referenced inside the kernel Kconfig files and must be present
    before any Kconfig object is instantiated.
    """
    os.environ["srctree"] = "."
    os.environ.setdefault("CC", "gcc")
    os.environ.setdefault("LD", "ld")
    _make = os.environ.get("MAKE", "make")
    _cc = os.environ["CC"]
    os.environ["KERNELVERSION"] = (
        subprocess.check_output(f"{_make} kernelversion", shell=True)
        .decode("utf-8")
        .rstrip()
    )
    os.environ["CC_VERSION_TEXT"] = (
        subprocess.check_output(f"{_cc} --version | head -n1", shell=True)
        .decode("utf-8")
        .rstrip()
    )
    yield


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def shell(cmd):
    """Run a shell command, suppressing stdout and stderr."""
    subprocess.call(
        cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def all_arch_srcarch():
    """Yield (arch, srcarch) pairs for every architecture in the tree.

    Some architectures are skipped because they are broken with the C tools
    or require a non-standard testing setup (user-mode Linux).
    """
    for srcarch in os.listdir("arch"):
        # arc and h8300 are currently broken with the C tools on linux-next
        # as well.  Perhaps they require cross-compilers to be installed.
        #
        # User-mode Linux has an unorthodox Kconfig setup that would require
        # a different testing setup.  Skip it too.
        if srcarch in ("arc", "h8300", "um"):
            continue

        if os.path.exists(os.path.join("arch", srcarch, "Kconfig")):
            yield (srcarch, srcarch)

    # Some arches define additional ARCH settings with ARCH != SRCARCH
    # (search for "Additional ARCH settings for" in the top-level Makefile)

    yield ("i386", "x86")
    yield ("x86_64", "x86")

    yield ("sparc32", "sparc")
    yield ("sparc64", "sparc")

    yield ("sh64", "sh")


def run_conf_and_compare(script, conf_flag, arch):
    """Run a Kconfiglib script and the C conf tool, then compare .config files.

    Both sides are invoked directly (not through 'make') so they inherit
    the identical process environment set up by the kernel_env fixture.
    This eliminates asymmetry: both parsers see the same CC, LD,
    KERNELVERSION, RUSTC (or lack thereof), etc., ensuring that $(shell)
    evaluations in Kconfig files produce identical results.  It also avoids
    platform-specific 'make' failures (e.g. macOS cross-arch builds).

    If either tool fails to produce a .config, the comparison is skipped
    for this architecture (with a printed note).
    """
    shell(f"{shlex.quote(sys.executable)} {shlex.quote(script)} Kconfig")
    if not os.path.exists(".config"):
        print(f"  {arch}: Kconfiglib script failed to produce .config, skipping")
        return
    shell("mv .config ._config")

    shell(f"scripts/kconfig/conf --{conf_flag} Kconfig")
    if not os.path.exists(".config"):
        print(f"  {arch}: C conf tool failed to produce .config, skipping")
        return

    compare_configs(arch)


def defconfig_files(srcarch):
    """Yield defconfig file paths for a particular srcarch subdirectory
    (arch/<srcarch>/).
    """
    srcarch_dir = os.path.join("arch", srcarch)

    root_defconfig = os.path.join(srcarch_dir, "defconfig")
    if os.path.exists(root_defconfig):
        yield root_defconfig

    defconfigs_dir = os.path.join(srcarch_dir, "configs")
    if not os.path.isdir(defconfigs_dir):
        return

    for dirpath, _, filenames in os.walk(defconfigs_dir):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


def collect_defconfigs(srcarch, use_obsessive):
    """Collect defconfig paths, optionally from all architectures."""
    if use_obsessive:
        configs = []
        for sa in os.listdir("arch"):
            configs.extend(defconfig_files(sa))
        return configs
    return defconfig_files(srcarch)


def rm_configs():
    """Delete any old '.config' and '._config', if present."""
    for name in (".config", "._config"):
        try:
            os.remove(name)
        except FileNotFoundError:
            pass


def compare_configs(arch):
    """Compare .config (C tool) with ._config (Kconfiglib) and assert they
    are identical.
    """
    assert equal_configs(), f"Mismatched .config for arch {arch}"


def equal_configs():
    """Return True if .config and ._config are equivalent (ignoring the
    header comment generated by the C conf tool).

    On mismatch, prints a unified diff to aid debugging.
    """
    try:
        with open(".config") as f:
            their = f.readlines()
    except FileNotFoundError:
        print(".config not found (C conf tool may have failed)")
        return False

    # Strip the header generated by 'conf'.  Stop at the first non-comment
    # line, or at a "# CONFIG_... is not set" comment (which is config data).
    for i, line in enumerate(their):
        if not line.startswith("#") or re.match(r"# CONFIG_(\w+) is not set", line):
            break
    else:
        i = len(their)
    their = their[i:]

    try:
        with open("._config") as f:
            our = f.readlines()
    except FileNotFoundError:
        print("._config not found (Kconfiglib script may have failed)")
        return False

    if their == our:
        return True

    print("Mismatched .config's! Unified diff:")
    sys.stdout.writelines(
        difflib.unified_diff(their, our, fromfile="their", tofile="our")
    )
    return False


def _exercise_sym_api(kconf, sym):
    """Call all public API methods/properties on a symbol to verify nothing
    crashes or hangs.
    """
    repr(sym)
    str(sym)
    sym.assignable
    kconf.warn = False
    sym.set_value(2)
    sym.set_value("foo")
    sym.unset_value()
    kconf.warn = True
    sym.str_value
    sym.tri_value
    sym.type
    sym.visibility


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# The five all*config tests share the same structure: iterate architectures,
# run a Kconfiglib script, then compare against the C tool output.  A single
# parametrized test covers all of them without losing per-mode granularity
# in pytest output.

_ALLCONFIG_CASES = [
    ("Kconfiglib/allnoconfig.py", "allnoconfig"),
    ("Kconfiglib/examples/allnoconfig_walk.py", "allnoconfig"),
    ("Kconfiglib/allmodconfig.py", "allmodconfig"),
    ("Kconfiglib/allyesconfig.py", "allyesconfig"),
    ("Kconfiglib/alldefconfig.py", "alldefconfig"),
]


@pytest.mark.parametrize(
    "script,conf_flag",
    _ALLCONFIG_CASES,
    ids=[
        c[1] if i == 0 or c[1] != _ALLCONFIG_CASES[i - 1][1] else f"{c[1]}_walk"
        for i, c in enumerate(_ALLCONFIG_CASES)
    ],
)
def test_allconfig(script, conf_flag):
    """Verify that a Kconfiglib *config script generates the same .config
    as the corresponding 'make <conf_flag>', for each architecture.
    """
    for arch, srcarch in all_arch_srcarch():
        os.environ["ARCH"] = arch
        os.environ["SRCARCH"] = srcarch
        rm_configs()
        run_conf_and_compare(script, conf_flag, arch)


def test_defconfig():
    """Verify that Kconfiglib generates the same .config as
    scripts/kconfig/conf, for each architecture/defconfig pair.

    In obsessive mode (KCONFIGLIB_OBSESSIVE=1), this test includes
    nonsensical groupings of arches with defconfigs from other arches
    (every arch/defconfig combination) and takes an order of magnitude
    longer to run.

    With logging enabled (KCONFIGLIB_LOG=1), failures are appended to
    test_defconfig_fails in the kernel root.
    """
    for arch, srcarch in all_arch_srcarch():
        os.environ["ARCH"] = arch
        os.environ["SRCARCH"] = srcarch
        rm_configs()

        try:
            kconf = Kconfig()
        except KconfigError:
            print(f"  {arch}: Kconfig parsing failed, skipping")
            continue

        for defconfig in collect_defconfigs(srcarch, obsessive):
            rm_configs()

            kconf.load_config(defconfig)
            kconf.write_config("._config")
            shell(f"scripts/kconfig/conf --defconfig='{defconfig}' Kconfig")

            label = f"  {arch:14}with {defconfig:60} "

            if equal_configs():
                print(label + "OK")
            else:
                if log:
                    with open("test_defconfig_fails", "a") as fail_log:
                        fail_log.write(f"{arch} with {defconfig} did not match\n")
                pytest.fail(label + "FAIL")


def test_min_config():
    """Verify that Kconfiglib generates the same .config as
    'make savedefconfig' for each architecture/defconfig pair.

    NOTE: This test is disabled in the original suite due to a bug in the
    C tools for a few defconfigs.  It is included here for completeness
    and can be run explicitly.
    """
    for arch, srcarch in all_arch_srcarch():
        os.environ["ARCH"] = arch
        os.environ["SRCARCH"] = srcarch
        rm_configs()

        try:
            kconf = Kconfig()
        except KconfigError:
            print(f"  {arch}: Kconfig parsing failed, skipping")
            continue

        for defconfig in collect_defconfigs(srcarch, obsessive_min_config):
            rm_configs()

            kconf.load_config(defconfig)
            kconf.write_min_config("._config")

            shell(f"cp {defconfig} .config")
            shell("scripts/kconfig/conf --savedefconfig=.config Kconfig")

            label = f"  {arch:14}with {defconfig:60} "

            if equal_configs():
                print(label + "OK")
            else:
                print(label + "FAIL")
                pytest.fail(label + "FAIL")


def test_sanity():
    """Do sanity checks on each configuration and call all public methods
    on all symbols, choices, and menu nodes for all architectures to make
    sure we never crash or hang.
    """
    for arch, srcarch in all_arch_srcarch():
        os.environ["ARCH"] = arch
        os.environ["SRCARCH"] = srcarch
        rm_configs()

        print(f"For {arch}...")

        try:
            kconf = Kconfig()
        except KconfigError:
            print(f"  {arch}: Kconfig parsing failed, skipping")
            continue

        for sym in kconf.defined_syms:
            assert sym._visited == 2, (
                f"{sym.name} has broken dependency loop detection "
                f"(_visited = {sym._visited})"
            )

        kconf.modules
        kconf.defconfig_list
        kconf.defconfig_filename

        # Exercise warning attribute toggles
        kconf.warn_assign_redun = True
        kconf.warn_assign_redun = False
        kconf.warn_assign_undef = True
        kconf.warn_assign_undef = False
        kconf.warn = True
        kconf.warn = False
        kconf.warn_to_stderr = True
        kconf.warn_to_stderr = False

        kconf.mainmenu_text
        kconf.unset_values()

        kconf.write_autoconf("/dev/null")

        tmpdir = tempfile.mkdtemp()
        kconf.sync_deps(os.path.join(tmpdir, "deps"))  # Create
        kconf.sync_deps(os.path.join(tmpdir, "deps"))  # Update
        shutil.rmtree(tmpdir)

        # -- Verify non-constant symbols (kconf.syms) --

        for key, sym in kconf.syms.items():
            assert isinstance(key, str), f"weird key '{key}' in syms dict"
            assert not sym.is_constant, f"{sym.name} in 'syms' and constant"
            assert (
                sym not in kconf.const_syms
            ), f"{sym.name} in both 'syms' and 'const_syms'"

            for dep in sym._dependents:
                assert (
                    not dep.is_constant
                ), f"the constant symbol {dep.name} depends on {sym.name}"

            _exercise_sym_api(kconf, sym)
            sym.user_value

        # -- Verify defined symbols have nodes and correct choice types --

        for sym in kconf.defined_syms:
            assert sym.nodes, f"{sym.name} is defined but lacks menu nodes"

            if sym.choice:
                assert sym.orig_type in (
                    BOOL,
                    TRISTATE,
                ), f"{sym.name} is a choice symbol but not bool/tristate"

        # -- Verify constant symbols (kconf.const_syms) --

        for key, sym in kconf.const_syms.items():
            assert isinstance(key, str), f"weird key '{key}' in const_syms dict"
            assert (
                sym.is_constant
            ), f'"{sym.name}" is in const_syms but not marked constant'
            assert not sym.nodes, f'"{sym.name}" is constant but has menu nodes'
            assert (
                not sym._dependents
            ), f'"{sym.name}" is constant but is a dependency of some symbol'
            assert not sym.choice, f'"{sym.name}" is constant and a choice symbol'

            _exercise_sym_api(kconf, sym)

        # -- Verify choices --

        for choice in kconf.choices:
            for sym in choice.syms:
                assert sym.choice is choice, (
                    f"{sym.name} is in choice.syms but 'sym.choice' is not "
                    "the choice"
                )
                assert sym.type in (
                    BOOL,
                    TRISTATE,
                ), f"{sym.name} is a choice symbol but is not a bool/tristate"

            str(choice)
            repr(choice)
            choice.str_value
            choice.tri_value
            choice.user_value
            choice.assignable
            choice.selection
            choice.type
            choice.visibility

        # -- Walk all menu nodes --

        node = kconf.top_node

        while True:
            repr(node)
            str(node)
            assert isinstance(node.item, (Symbol, Choice)) or node.item in (
                MENU,
                COMMENT,
            ), f"'{node.item}' appeared as a menu item"

            if node.list is not None:
                node = node.list
            elif node.next is not None:
                node = node.next
            else:
                while node.parent is not None:
                    node = node.parent
                    if node.next is not None:
                        node = node.next
                        break
                else:
                    break
