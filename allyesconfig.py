#!/usr/bin/env python3

# Copyright (c) 2018-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC

"""
Writes a configuration file where as many symbols as possible are set to 'y'.

The default output filename is '.config'. A different filename can be passed
in the KCONFIG_CONFIG environment variable.

Usage for the Linux kernel:

  $ make [ARCH=<arch>] scriptconfig SCRIPT=Kconfiglib/allyesconfig.py
"""

import kconfiglib


def main():
    kconf = kconfiglib.standard_kconfig(__doc__)

    # See allnoconfig.py
    kconf.warn = False

    # Try to set all symbols to 'y'. Dependencies might truncate the value down
    # later, but this will at least give the highest possible value.
    #
    # Assigning 0/1/2 to non-bool/tristate symbols has no effect (int/hex
    # symbols still take a string, because they preserve formatting).
    for sym in kconf.unique_defined_syms:
        # Skip choice member symbols -- conf_set_all_new_symbols() in
        # scripts/kconfig/conf.c (Linux) never sets SYMBOL_DEF_USER on
        # choice values, leaving the choice selection logic to pick the
        # default.
        if sym.choice:
            continue
        sym.set_value(2)

    # Set all choices to the highest possible mode
    for choice in kconf.unique_choices:
        choice.set_value(2)

    kconf.warn = True

    kconf.load_allconfig("allyes.config")

    print(kconf.write_config())


if __name__ == "__main__":
    main()
