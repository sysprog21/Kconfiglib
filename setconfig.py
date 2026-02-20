#!/usr/bin/env python3

# Copyright (c) 2019 Ulf Magnusson
# SPDX-License-Identifier: ISC

"""
Simple utility for setting configuration values from the command line.

Sample usage:

  $ setconfig FOO_SUPPORT=y BAR_BITS=8

Note: Symbol names should not be prefixed with 'CONFIG_'.

The exit status on errors is 1.

The default input/output configuration file is '.config'. A different filename
can be passed in the KCONFIG_CONFIG environment variable.

When overwriting a configuration file, the old version is saved to
<filename>.old (e.g. .config.old).
"""

import argparse
import sys

import kconfiglib


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__
    )

    parser.add_argument(
        "--kconfig", default="Kconfig", help="Top-level Kconfig file (default: Kconfig)"
    )

    parser.add_argument(
        "--no-check-exists",
        dest="check_exists",
        action="store_false",
        help="Ignore assignments to non-existent symbols instead of erroring out",
    )

    parser.add_argument(
        "--no-check-value",
        dest="check_value",
        action="store_false",
        help='Ignore assignments that didn\'t "take" (where the symbol got a '
        "different value, e.g. due to unsatisfied dependencies) instead "
        "of erroring out",
    )

    parser.add_argument(
        "assignments", metavar="ASSIGNMENT", nargs="*", help="A 'NAME=value' assignment"
    )

    args = parser.parse_args()

    kconf = kconfiglib.Kconfig(args.kconfig, suppress_traceback=True)
    print(kconf.load_config())

    for arg in args.assignments:
        if "=" not in arg:
            sys.exit(f"error: no '=' in assignment: '{arg}'")
        name, value = arg.split("=", 1)

        if name not in kconf.syms:
            if not args.check_exists:
                continue
            sys.exit(f"error: no symbol '{name}' in configuration")

        sym = kconf.syms[name]

        if not sym.set_value(value):
            sys.exit(
                f"error: '{value}' is an invalid value for the {kconfiglib.TYPE_TO_STR[sym.orig_type]} symbol {name}"
            )

        if args.check_value and sym.str_value != value:
            sys.exit(
                f"error: {name} was assigned the value '{value}', but got the "
                f"value '{sym.str_value}'. Check the symbol's dependencies, and make "
                "sure that it has a prompt."
            )

    print(kconf.write_config())


if __name__ == "__main__":
    main()
