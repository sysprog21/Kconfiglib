#!/usr/bin/env python3

# Copyright (c) 2019 Nordic Semiconductor ASA
# SPDX-License-Identifier: ISC

"""
Linter for Kconfig files. Pass --help to see available checks.
By default, all checks are enabled.

Some checks rely on heuristics and can get tripped up by things
like preprocessor magic, so manual checking is still needed.
'git grep' is handy.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys

import kconfiglib

# Global Kconfig instance
kconf = None


def print_header(s):
    print(s + "\n" + len(s) * "=")


def has_prompt(sym):
    return any(node.prompt for node in sym.nodes)


def is_selected_or_implied(sym):
    return sym.rev_dep is not kconf.n or sym.weak_rev_dep is not kconf.n


def has_defaults(sym):
    return bool(sym.defaults)


def name_and_locs(sym):
    # Returns a string with the name and definition location(s) for 'sym'

    return "{:40} {}".format(
        sym.name,
        ", ".join("{0.filename}:{0.linenr}".format(node) for node in sym.nodes),
    )


def print_results(header, results, print_separator):
    # Prints a list of results with a header and optional leading separator.
    # Returns True if any results were printed, False otherwise.

    if not results:
        return False

    if print_separator:
        print()
    print_header(header)
    for result in results:
        print(result, end="" if result.endswith("\n") else "\n")
    return True


def check_always_n(print_separator):
    results = [
        name_and_locs(sym)
        for sym in kconf.unique_defined_syms
        if not has_prompt(sym)
        and not is_selected_or_implied(sym)
        and not has_defaults(sym)
    ]
    return print_results(
        "Symbols that can't be anything but n/empty", results, print_separator
    )


def referenced_in_kconfig():
    # Returns the names of all symbols referenced inside the Kconfig files

    return {
        ref.name
        for node in kconf.node_iter()
        for ref in node.referenced
        if isinstance(ref, kconfiglib.Symbol)
    }


def executable():
    cmd = sys.argv[0]  # Empty string if missing
    return cmd + ": " if cmd else ""


def err(msg):
    sys.exit(executable() + "error: " + msg)


def warn(msg):
    print(executable() + "warning: " + msg, file=sys.stderr)


def run(cmd, cwd=None, check=True):
    # Runs 'cmd' with subprocess, returning the decoded stdout output.
    # 'cwd' is the working directory. Exits with an error if the command
    # exits with a non-zero return code if 'check' is True.

    cmd_s = " ".join(shlex.quote(word) for word in cmd)

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
        )
    except OSError as e:
        err("Failed to run '{}': {}".format(cmd_s, e))

    stdout, stderr = process.communicate()
    stdout = stdout.decode("utf-8", errors="ignore")
    stderr = stderr.decode("utf-8")
    if check and process.returncode:
        err(
            """\
'{}' exited with status {}.

===stdout===
{}
===stderr===
{}""".format(
                cmd_s, process.returncode, stdout, stderr
            )
        )

    if stderr:
        warn("'{}' wrote to stderr:\n{}".format(cmd_s, stderr))

    return stdout


def referenced_outside_kconfig(search_dirs):
    # Returns the names of all symbols referenced outside the Kconfig files
    # Searches in the specified directories using git grep

    if not search_dirs:
        return set()

    regex = r"\bCONFIG_[A-Z0-9_]+\b"
    res = set()

    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue

        try:
            for line in run(
                ("git", "grep", "-h", "-I", "--extended-regexp", regex),
                cwd=search_dir,
                check=False,
            ).splitlines():
                # Don't record lines starting with "CONFIG_FOO=" or "# CONFIG_FOO="
                # as references, so that symbols that are only assigned in .config
                # files are not included
                if re.match(r"[\s#]*CONFIG_[A-Z0-9_]+=.*", line):
                    continue

                # Could pass --only-matching to git grep as well, but it was added
                # pretty recently (2018)
                for match in re.findall(regex, line):
                    res.add(match[7:])  # Strip "CONFIG_"
        except:
            # If git grep fails (not a git repo, etc.), skip this directory
            pass

    return res


def referenced_sym_names(search_dirs):
    # Returns the names of all symbols referenced inside and outside the
    # Kconfig files (that we can detect), without any "CONFIG_" prefix

    return referenced_in_kconfig() | referenced_outside_kconfig(search_dirs)


def is_selecting_or_implying(sym):
    return sym.selects or sym.implies


def check_unused(search_dirs, print_separator):
    referenced = referenced_sym_names(search_dirs)
    results = [
        name_and_locs(sym)
        for sym in kconf.unique_defined_syms
        if not is_selecting_or_implying(sym)
        and not sym.choice
        and sym.name not in referenced
    ]
    return print_results("Symbols that look unused", results, print_separator)


def check_pointless_menuconfigs(print_separator):
    results = [
        "{0.item.name:40} {0.filename}:{0.linenr}".format(node)
        for node in kconf.node_iter()
        if node.is_menuconfig
        and not node.list
        and isinstance(node.item, kconfiglib.Symbol)
    ]
    return print_results(
        "menuconfig symbols with empty menus", results, print_separator
    )


def check_defconfig_only_definition(print_separator):
    results = [
        name_and_locs(sym)
        for sym in kconf.unique_defined_syms
        if all("defconfig" in node.filename for node in sym.nodes)
    ]
    return print_results(
        "Symbols only defined in Kconfig.defconfig files", results, print_separator
    )


def split_list(lst, batch_size):
    # Helper generator that splits a list into equal-sized batches
    # (possibly with a shorter batch at the end)

    for i in range(0, len(lst), batch_size):
        yield lst[i : i + batch_size]


def check_missing_config_prefix(search_dirs, print_separator):
    if not search_dirs:
        return False

    # Gather #define'd macros that might overlap with symbol names, so that
    # they don't trigger false positives
    defined = set()
    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue
        try:
            regex = r"#\s*define\s+([A-Z0-9_]+)\b"
            defines = run(
                ("git", "grep", "--extended-regexp", regex), cwd=search_dir, check=False
            )
            defined.update(re.findall(regex, defines))
        except:
            pass

    # Filter out symbols whose names are #define'd too. Preserve definition
    # order to make the output consistent.
    syms = [sym for sym in kconf.unique_defined_syms if sym.name not in defined]

    # grep for symbol references in #ifdef/defined() that are missing a CONFIG_
    # prefix. Work around an "argument list too long" error from 'git grep' by
    # checking symbols in batches.
    results = []
    for batch in split_list(syms, 200):
        # grep for '#if((n)def) <symbol>', 'defined(<symbol>', and
        # 'IS_ENABLED(<symbol>', with a missing CONFIG_ prefix
        regex = (
            r"(?:#\s*if(?:n?def)\s+|\bdefined\s*\(\s*|IS_ENABLED\(\s*)(?:"
            + "|".join(sym.name for sym in batch)
            + r")\b"
        )
        cmd = ("git", "grep", "--line-number", "-I", "--perl-regexp", regex)

        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            try:
                output = run(cmd, cwd=search_dir, check=False)
                if output:
                    results.append(output)
            except:
                pass

    return print_results(
        "Symbol references that might be missing a CONFIG_ prefix",
        results,
        print_separator,
    )


def parse_args():
    # args.checks is set to a list of check functions to run

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description=__doc__,
        allow_abbrev=False,
    )

    parser.add_argument(
        "kconfig",
        metavar="KCONFIG",
        nargs="?",
        default="Kconfig",
        help="Top-level Kconfig file (default: Kconfig)",
    )

    parser.add_argument(
        "--search-dir",
        action="append",
        dest="search_dirs",
        default=[],
        help="""\
Directory to search for symbol references (can be specified
multiple times). Used by --check-unused and
--check-missing-config-prefix. If not specified, only Kconfig
files will be searched.""",
    )

    parser.add_argument(
        "-n",
        "--check-always-n",
        action="append_const",
        dest="checks",
        const="always_n",
        help="""\
List symbols that can never be anything but n/empty. These
are detected as symbols with no prompt or defaults that
aren't selected or implied.
""",
    )

    parser.add_argument(
        "-u",
        "--check-unused",
        action="append_const",
        dest="checks",
        const="unused",
        help="""\
List symbols that might be unused.

Heuristic:

 - Isn't referenced in Kconfig
 - Isn't referenced as CONFIG_<NAME> outside Kconfig
   (besides possibly as CONFIG_<NAME>=<VALUE>)
 - Isn't selecting/implying other symbols
 - Isn't a choice symbol

C preprocessor magic can trip up this check.""",
    )

    parser.add_argument(
        "-m",
        "--check-pointless-menuconfigs",
        action="append_const",
        dest="checks",
        const="menuconfigs",
        help="""\
List symbols defined with 'menuconfig' where the menu is
empty due to the symbol not being followed by stuff that
depends on it""",
    )

    parser.add_argument(
        "-d",
        "--check-defconfig-only-definition",
        action="append_const",
        dest="checks",
        const="defconfig",
        help="""\
List symbols that are only defined in Kconfig.defconfig
files. A common base definition should probably be added
somewhere for such symbols, and the type declaration ('int',
'hex', etc.) removed from Kconfig.defconfig.""",
    )

    parser.add_argument(
        "-p",
        "--check-missing-config-prefix",
        action="append_const",
        dest="checks",
        const="prefix",
        help="""\
Look for references like

    #if MACRO
    #if(n)def MACRO
    defined(MACRO)
    IS_ENABLED(MACRO)

where MACRO is the name of a defined Kconfig symbol but
doesn't have a CONFIG_ prefix. Could be a typo.

Macros that are #define'd somewhere are not flagged.
Requires --search-dir to be specified.""",
    )

    return parser.parse_args()


def main():
    global kconf

    args = parse_args()

    # Load Kconfig
    if not os.path.exists(args.kconfig):
        err("Kconfig file '{}' not found".format(args.kconfig))

    try:
        kconf = kconfiglib.Kconfig(
            args.kconfig, warn_to_stderr=False, suppress_traceback=True
        )
    except Exception as e:
        err("Failed to load Kconfig: {}".format(e))

    # Run all checks if none were specified on the command line
    check_names = args.checks or [
        "always_n",
        "unused",
        "menuconfigs",
        "defconfig",
        "prefix",
    ]

    # Map check names to functions
    check_map = {
        "always_n": check_always_n,
        "unused": lambda sep: check_unused(args.search_dirs, sep),
        "menuconfigs": check_pointless_menuconfigs,
        "defconfig": check_defconfig_only_definition,
        "prefix": lambda sep: check_missing_config_prefix(args.search_dirs, sep),
    }

    had_output = False
    for check_name in check_names:
        had_output |= check_map[check_name](had_output)


if __name__ == "__main__":
    main()
