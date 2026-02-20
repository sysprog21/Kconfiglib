# Prints all (set) environment variables referenced in the Kconfig files
# together with their values, as a list of assignments.
#
# Note: This only works for environment variables referenced via the $(FOO)
# preprocessor syntax.

import os
import sys

import kconfiglib

print(
    " ".join(
        "{}='{}'".format(var, os.environ[var])
        for var in kconfiglib.Kconfig(sys.argv[1]).env_vars
    )
)
