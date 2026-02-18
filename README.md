# Kconfiglib

## Overview

Kconfiglib is a [Kconfig](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-language.rst)
implementation in Python.
It started as a helper library but now has enough functionality to work as a standalone Kconfig implementation
(including [terminal and GUI menuconfig interfaces](#menuconfig-interfaces) and [Kconfig extensions](#kconfig-extensions)).

The entire library is contained in [kconfiglib.py](kconfiglib.py).
The bundled scripts are implemented on top of it, and creating your own scripts should be relatively straightforward if needed.

Kconfiglib is used extensively by projects such as the
[Zephyr Project](https://www.zephyrproject.org/) and
[ESP-IDF](https://github.com/espressif/esp-idf).
It is also employed for various helper scripts in other projects.

Because Kconfiglib is library-based, it can be used, for example, to generate a
[Kconfig cross-reference](https://docs.zephyrproject.org/latest/reference/kconfig/index.html)
using the same robust Kconfig parser used by other Kconfig tools,
instead of relying on brittle ad-hoc parsing.

Kconfiglib implements the recently added
[Kconfig preprocessor](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-macro-language.rst).
For backward compatibility, environment variables can be referenced both as `$(FOO)` (the new syntax)
and as `$FOO` (the old syntax).
While the old syntax is deprecated,
it will likely remain supported for some time in order to maintain compatibility with older Linux kernels.
If support for it is ever dropped, the major version will be incremented accordingly.
Note that using the old syntax with an undefined environment variable leaves the string unchanged.

See [Kconfig: Tips and Best Practices](https://docs.zephyrproject.org/latest/build/kconfig/tips.html) for more information.

## Installation

### Installation with pip

To install the latest version directly from GitHub, run:
```shell
pip install git+https://github.com/sysprog21/Kconfiglib
```

Microsoft Windows is supported.

When installed via `pip`, you get both the core library and the following executables.
All but three (`genconfig`, `setconfig`, and `lint`) mirror functionality available in the C tools.
- [menuconfig](menuconfig.py)
- [guiconfig](guiconfig.py)
- [oldconfig](oldconfig.py)
- [olddefconfig](olddefconfig.py)
- [savedefconfig](savedefconfig.py)
- [defconfig](defconfig.py)
- [alldefconfig](alldefconfig.py)
- [allnoconfig](allnoconfig.py)
- [allmodconfig](allmodconfig.py)
- [allyesconfig](allyesconfig.py)
- [listnewconfig](listnewconfig.py)
- [genconfig](genconfig.py)
- [setconfig](setconfig.py)
- [lint](lint.py)

`genconfig` is intended to be run at build time.
It generates a C header from the configuration and, optionally,
additional data that can be used to rebuild only the files referencing Kconfig symbols whose values have changed.

`lint.py` is a standalone linter for Kconfig files that performs static analysis to detect potential issues
such as unused symbols, symbols that can never be enabled, pointless menuconfig entries, and missing CONFIG_
prefixes in source code. Run it directly with `python3 lint.py <Kconfig>` or see `python3 lint.py --help`
for available checks.

Kconfiglib requires Python 3.6 or later.

**Note:** If Kconfiglib is installed with the `pip --user` flag,
ensure that the `PATH` variable includes the directory where the executables are installed.
To list the installed files, use:
```shell
pip show -f kconfiglib
```

All releases have a corresponding tag in the Git repository (for example, `v14.1.0` is the latest stable version).

Kconfiglib follows [Semantic Versioning](https://semver.org/).
Major version increments are made for any behavior change, regardless of scope.
Most changes thus far have addressed small issues introduced in the early days of the Kconfiglib 2 API.

### Manual installation

Just drop `kconfiglib.py` and the scripts you want somewhere.
There are no third-party dependencies, but the terminal `menuconfig` will not work on Windows unless a package like
[windows-curses](https://github.com/zephyrproject-rtos/windows-curses)
is installed.

### Installation for the Linux kernel

See the module docstring at the top of [kconfiglib.py](kconfiglib.py).

### Python version compatibility

Kconfiglib requires Python 3.6 or later.
The code primarily relies on basic Python features and does not depend on third-party libraries.

## Getting started

1. [Install](#installation) the library and the utilities.

2. Write [Kconfig](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-language.rst)
   files that describe the available configuration options.
   For general Kconfig advice, see [Tips and Best Practices](https://docs.zephyrproject.org/latest/guides/kconfig/tips.html).

3. Generate an initial configuration using `menuconfig`, `guiconfig`, or `alldefconfig`.
   The configuration is saved as `.config` by default.

   - For more advanced projects, use the `defconfig` utility to generate the initial configuration from an existing configuration file.
     Typically, this existing file is a minimal configuration generated by commands like `savedefconfig`.

4. Run `genconfig` to generate a header file.
   By default, this file is saved as `config.h`.

   - Normally, `genconfig` is run automatically as part of the build.
   - Before writing a header or any other configuration output, Kconfiglib compares the file’s old contents with the new contents.
     If they are identical, Kconfiglib skips writing.
     This avoids needlessly updating file metadata (like modification times) and can save build time.
   - Adding new configuration output formats is relatively straightforward.
     See the implementation of `write_config()` in [kconfiglib.py](kconfiglib.py).
     The documentation for the `Symbol.config_string` property also contains helpful tips.

5. Update an old `.config` file after changing the Kconfig files (e.g., adding new options) by
   running `oldconfig` (prompts for values for new options) or `olddefconfig` (assigns default values to new options).
   - Entering the `menuconfig` or `guiconfig` interface and saving will also update the configuration
     (the interfaces prompt for saving on exit if the `.config` file has changed).
   - Due to Kconfig semantics, loading an old `.config` file implicitly performs an `olddefconfig`,
     so building typically won’t be affected by an outdated configuration.

Whenever `.config` is overwritten, its previous contents are saved to `.config.old` (or, more generally, to `$KCONFIG_CONFIG.old`).

### Using `.config` files as Make input

Because `.config` files use Make syntax, they can be included directly in Makefiles to read configuration values.
For `n`-valued `bool` / `tristate` options, the line `# CONFIG_FOO is not set` (a Make comment) is generated in `.config`,
allowing the option to be tested via `ifdef` in Make.

If you rely on this behavior, consider passing `--config-out <filename>` to `genconfig` and including the generated configuration file instead of `.config` directly.
This ensures the included file is always a "full" configuration file, even if `.config` becomes outdated.
Otherwise, you may need to run `old(def)config`, `menuconfig`, or `guiconfig` before rebuilding.

If you use the `--sync-deps` option to generate incremental build information,
you can include `deps/auto.conf` instead, which is also a full configuration file.

### Useful helper macros

The
[include/linux/kconfig.h](https://github.com/torvalds/linux/blob/master/include/linux/kconfig.h) header in the Linux kernel defines several helper macros for testing Kconfig configuration values.
Among these, `IS_ENABLED()` is especially useful because it allows configuration values to be tested in `if` statements with no runtime overhead.

### Incremental building

For guidance on implementing incremental builds (rebuilding only those source files that reference changed configuration values),
refer to the docstring for `Kconfig.sync_deps()` in [kconfiglib.py](kconfiglib.py).

It may also be helpful to run the kernel’s `scripts/basic/fixdep.c` tool on the output of `gcc -MD <source file>`,
to see how the build process fits together.

## Library documentation

Kconfiglib includes extensive documentation in the form of docstrings.
To view it, run, for example:
```shell
pydoc kconfiglib
```

For HTML output, add `-w`:
```shell
pydoc -w kconfiglib
```

This will work even after installing Kconfiglib with `pip`.

Documentation for other modules can be viewed the same way.
For executables, a plain `--help` often suffices:
```shell
pydoc menuconfig/guiconfig/...
```

A good place to start is the module docstring, located at the beginning of [kconfiglib.py](kconfiglib.py).
It provides an introduction to symbol values, the menu tree, and expressions.

After reviewing the module docstring, the next step is to read the documentation for the `Kconfig` class,
followed by `Symbol`, `Choice`, and `MenuNode`.

Please [report any issues](https://github.com/sysprog21/Kconfiglib/issues) if something is unclear or can be explained better.

## Library features

Kconfiglib can do the following, among other things:

- Programmatically get and set symbol values

  See [allnoconfig.py](allnoconfig.py) and [allyesconfig.py](allyesconfig.py),
  which are automatically verified to produce identical output to the standard
  `make allnoconfig` and `make allyesconfig`.

- Read and write `.config` and `defconfig` files

  The generated `.config` and `defconfig` (minimal configuration) files are
  character-for-character identical to what the C implementation would generate
  (except for the header comment).
  The test suite relies on this by comparing the generated files directly.

- Write C headers

  The generated headers use the same format as `include/generated/autoconf.h` from the Linux kernel.
  Symbol output appears in the order in which the symbols are defined,
  unlike in the C tools (where the order depends on the hash table implementation).

- Implement incremental builds

  This follows the same scheme used by the `include/config` directory in the kernel:
  symbols are translated into files that are updated when a symbol's value changes between builds,
  which can help avoid a full rebuild whenever the configuration changes.

  See the `sync_deps()` function for additional details.

- Inspect symbols

  Printing a symbol or other item (via `__str__()`) returns its definition in Kconfig format,
  and this also works for symbols that appear in multiple locations.

  A useful `__repr__()` is defined on all objects as well.

  All `__str__()` and `__repr__()` methods are deliberately implemented using public APIs,
  so all symbol information can also be retrieved separately.

- Inspect expressions

  Expressions use a simple tuple-based format that can be processed manually if needed.
  Kconfiglib includes expression-printing and evaluation functions, implemented with public APIs.

- Inspect the menu tree

  The underlying menu tree is exposed, including submenus created implicitly by symbols that depend on preceding symbols.
  This can be used, for example, to implement menuconfig-like functionality.

See [menuconfig.py](menuconfig.py), [guiconfig.py](guiconfig.py),
and the minimalistic [menuconfig_example.py](examples/menuconfig_example.py) example.

### Kconfig extensions

The following Kconfig extensions are available:

- `source` supports glob patterns and includes each matching file.
  A pattern must match at least one file.
  A separate `osource` statement is available for situations where it is acceptable for the pattern to match no files
  (in which case `osource` becomes a no-op).

- A relative `source` statement (`rsource`) is available,
  where file paths are specified relative to the directory of the current Kconfig file.
  An `orsource` statement is also available, analogous to `osource`.

- Preprocessor user functions can be defined in Python,
  which makes it straightforward to integrate information from existing Python tools into Kconfig
  (for example, to have Kconfig symbols depend on hardware information stored in another format).
  See the "Kconfig extensions" section in the [kconfiglib.py](kconfiglib.py) module docstring for more details.

- `def_int`, `def_hex`, and `def_string` are provided in addition to `def_bool` and `def_tristate`,
  allowing `int`, `hex`, and `string` symbols to have both a type and a default value at the same time.
  These can be useful for projects that define symbols in multiple locations and help address some Kconfig inconsistencies.

- Environment variables are expanded directly in statements such as `source` and `mainmenu`, making `option env` symbols redundant.
  This is the standard behavior of the new
  [Kconfig preprocessor](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-macro-language.rst), which Kconfiglib implements.

  `option env` symbols are still accepted but ignored,
  provided they have the same name as the referenced environment variable (Kconfiglib will warn if they differ).
  This preserves compatibility with older Linux kernels, where the `option env` symbol's name always matched the environment variable.
  The main reason `option env` remains supported is to maintain backward compatibility.
  The C tools have dropped support for `option env`.

- Two extra optional warnings can be enabled by setting environment variables.
  These warnings cover cases that are easily overlooked when modifying Kconfig files:

- `KCONFIG_WARN_UNDEF`: If set to `y`, a warning is generated for any reference to an undefined symbol in a Kconfig file.
  The only caveat is that all hexadecimal literals must be prefixed with `0x` or `0X` so they can be distinguished from symbol references.

  Some projects (such as the Linux kernel) use multiple Kconfig trees with many shared Kconfig files,
  which can result in intentionally undefined symbol references.
  However, `KCONFIG_WARN_UNDEF` can be very useful in projects with a single Kconfig tree.
  `KCONFIG_STRICT` is an older alias for `KCONFIG_WARN_UNDEF`, retained for backward compatibility.

- `KCONFIG_WARN_UNDEF_ASSIGN`: If set to `y`, a warning is generated for any assignment to an undefined symbol in a `.config` file.
  By default, no such warnings are generated.

This warning can also be toggled by setting `Kconfig.warn_assign_undef` to `True` or `False`.

## Other features

- Single-file implementation

  The entire library is contained in [kconfiglib.py](kconfiglib.py).
  The tools built on top of it are each contained in a single file.

- Robust and highly compatible with the C Kconfig tools

  The [test suite](tests/) automatically compares output from Kconfiglib and
  the C tools by diffing the generated `.config` files for the real kernel Kconfig and defconfig files across all ARCHes.
  Currently, this involves comparing output for 36 ARCHes and 498 defconfig files (or over 18,000 ARCH/defconfig combinations in
  "obsessive" test suite mode). All tests are expected to pass.
  A comprehensive suite of self-tests is included as well.

- Not horribly slow despite being a pure Python implementation

  The [allyesconfig.py](allyesconfig.py) script runs in about 1.3 seconds on the Linux kernel using a Core i7 2600K with a warm file cache,
  including the `make` overhead from `make scriptconfig`.
  The Linux kernel Kconfigs are especially large (over 14k symbols for x86),
  and there is additional overhead from running shell commands via the Kconfig preprocessor.

  Kconfiglib is particularly efficient when multiple `.config` files must be processed, because the `Kconfig` files are parsed only once.

  For long-running jobs, [PyPy](https://pypy.org/) provides a significant performance boost,
  although CPython is typically faster for short jobs since PyPy requires time to warm up.

  Kconfiglib also works well with the [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) module,
  as it does not rely on global state.

- Generates more warnings than the C implementation

  Kconfiglib generates the same warnings as the C implementation,
  plus additional ones. It also detects dependency loops and `source` loops.
  All warnings indicate the relevant location(s) in the `Kconfig` files where a symbol is defined, if applicable.

- Unicode support

  Unicode characters in string literals within `Kconfig` and `.config` files are handled correctly,
  primarily thanks to Python’s built-in Unicode functionality.

- Windows support

  Nothing in Kconfiglib is specific to Linux.
  The [Zephyr](https://www.zephyrproject.org/) project uses Kconfiglib to generate `.config` files and C headers on both Linux and Windows.

- Internals that (mostly) mirror the C implementation

  While the internals are simpler to understand and modify, they closely track the logic of the C tools.

## Menuconfig interfaces

Three configuration interfaces are currently available:

- [menuconfig.py](menuconfig.py) is a terminal-based configuration interface implemented using the standard Python `curses` module.
  It includes `xconfig` features such as showing invisible symbols and symbol names,
  and it allows jumping directly to a symbol in the menu tree (even if it is currently invisible).

  ![image](https://raw.githubusercontent.com/zephyrproject-rtos/Kconfiglib/screenshots/screenshots/menuconfig.gif)

  There is also a show-help mode that displays the help text of the currently selected symbol in the bottom help window.

  `menuconfig.py` requires Python 3.6+.

  There are no third-party dependencies on Unix-like systems.
  On Windows, the `curses` module is not included by default, but can be added by installing the `windows-curses` package:
  ```shell
  pip install windows-curses
  ```
  These wheels are built from [this repository](https://github.com/zephyrproject-rtos/windows-curses),
  which is based on Christoph Gohlke's [Python Extension Packages for Windows](https://www.cgohlke.com/#curses).

  See the docstring at the top of [menuconfig.py](menuconfig.py) for more information about the terminal menuconfig implementation.

- [guiconfig.py](guiconfig.py) is a graphical configuration interface written in [Tkinter](https://docs.python.org/3/library/tkinter.html).
  Like `menuconfig.py`, it supports showing all symbols (with invisible symbols in red) and
  allows jumping directly to symbols.
  Symbol values can also be changed directly in the jump-to dialog.

  When single-menu mode is enabled, only a single menu is displayed at a time, similar to the terminal menuconfig.
  In this mode, it distinguishes between symbols defined with `config` and those defined with `menuconfig`.

  `guiconfig.py` features a modern dark/light theme system with a professional blue color scheme.
  Toggle between themes via the Theme menu.
  The interface includes a responsive layout that adapts to window resizing.

  `guiconfig.py` has been tested on X11, Windows, and macOS, and requires Python 3.6+.

  Although Tkinter is part of the Python standard library, it is not always installed by default on Linux.
  The commands below install it on a few different systems:
  - Ubuntu/Debian:
    ```shell
    sudo apt install python3-tk
    ```
  - Fedora:
    ```shell
    dnf install python3-tkinter
    ```
  - Arch:
    ```shell
    sudo pacman -S tk
    ```
  - macOS:
    ```shell
    brew install python-tk
    ```

  Screenshot below, with show-all mode enabled and the jump-to dialog open:
  ![image](https://raw.githubusercontent.com/zephyrproject-rtos/Kconfiglib/screenshots/screenshots/guiconfig.png)

  To avoid carrying around multiple GIF files, the image data is embedded in `guiconfig.py`.
  To use separate GIF files instead, set `_USE_EMBEDDED_IMAGES` to `False` in `guiconfig.py`.
  The image files are located in the [screenshots](https://github.com/zephyrproject-rtos/Kconfiglib/tree/screenshots/guiconfig) branch.

  The included images might not be the most artistic. Touch-ups are welcome.

## Examples

### Example scripts

The [examples/](examples) directory contains simple example scripts.
Make sure to run them with the latest version of Kconfiglib, as they may rely on newly added features.
Some examples include:

- [eval_expr.py](examples/eval_expr.py) evaluates an expression in the context of a configuration.
- [find_symbol.py](examples/find_symbol.py) searches expressions for references to a specific symbol and
  provides a "backtrace" of parents for each reference found.
- [help_grep.py](examples/help_grep.py) looks for a specified string in all help texts.
- [print_tree.py](examples/print_tree.py) prints a tree of all configuration items.
- [print_config_tree.py](examples/print_config_tree.py) functions similarly to `print_tree.py` but
  shows the tree as it would appear in `menuconfig`, including values.
  This is useful for visually diffing `.config` files and different versions of `Kconfig` files.
- [list_undefined.py](examples/list_undefined.py) identifies references to symbols that are not defined by any architecture in the Linux kernel.
- [merge_config.py](examples/merge_config.py) combines multiple configuration fragments into a complete `.config`,
  similar to `scripts/kconfig/merge_config.sh` in the kernel.
- [menuconfig_example.py](examples/menuconfig_example.py) demonstrates how to implement a configuration interface using notation
  similar to `make menuconfig`.
  This script is intentionally minimal to focus on the core concepts.

### Real-world examples

- [kconfig.py](https://github.com/zephyrproject-rtos/zephyr/blob/main/scripts/kconfig/kconfig.py)
  from the [Zephyr](https://www.zephyrproject.org/) project handles `.config` and header file generation,
  as well as configuration fragment merging.

- [CMake and IDE integration](https://github.com/espressif/esp-idf/tree/master/tools/kconfig_new)
  from the ESP-IDF project, using a configuration server program.

  These examples use the older Kconfiglib 1 API, which was clunkier and less general
  (e.g., functions instead of properties, no direct access to the menu structure, and a more limited `__str__()` output):

- [gen-manual-lists.py](https://git.busybox.net/buildroot/tree/support/scripts/gen-manual-lists.py?id=5676a2deea896f38123b99781da0a612865adeb0)
  produced listings for an appendix in the [Buildroot](https://buildroot.org) manual.
  (Those listings have since been removed.)

- [gen_kconfig_doc.py](https://github.com/espressif/esp-idf/blob/master/docs/gen-kconfig-doc.py)
  from the [esp-idf](https://github.com/espressif/esp-idf) project generates documentation from Kconfig files.

- [SConf](https://github.com/CoryXie/SConf)
  builds an interactive configuration interface (similar to `menuconfig`) on top of Kconfiglib,
  for use with [SCons](https://scons.org).

- [kconfig-diff.py](https://gist.github.com/dubiousjim/5638961)
  by [dubiousjim](https://github.com/dubiousjim) is a script that compares kernel configurations.

- In chapter 4 of Ulf Magnusson's [master thesis](http://liu.diva-portal.org/smash/get/diva2:473038/FULLTEXT01.pdf),
  Kconfiglib was originally used to generate a "minimal" kernel for a given system.
  Some parts of that approach feel dated now, but that often happens with older work.

## Test suite

The self-tests can be run from the project root with [pytest](https://docs.pytest.org/):
```shell
python -m pytest tests/ -v
```

To run the full suite -- self-tests, compatibility tests against the C Kconfig tools, and example scripts -- use
[tests/reltest](tests/reltest) from the top-level kernel directory (requires the Makefile patch):
```shell
Kconfiglib/tests/reltest python
```

To suppress warnings generated for the kernel `Kconfig` files, redirect `stderr` to `/dev/null`:
```
Kconfiglib/tests/reltest python 2>/dev/null
```

[pypy](https://pypy.org/) also works and is much faster for most tasks,
except for `allnoconfig.py`, `allnoconfig_simpler.py`, and `allyesconfig.py`,
where it has no time to warm up because those scripts are invoked via `make scriptconfig`.

Note: Forgetting to apply the Makefile patch will cause some compatibility tests that compare generated configurations to fail.

Note: The compatibility tests overwrite `.config` in the kernel root, so make sure to back it up.

The test suite consists of self-tests (under [tests/](tests/)) and compatibility tests
([tests/test_compat.py](tests/test_compat.py)) that compare configurations generated by Kconfiglib
with those generated by the C tools across various scenarios.

Occasionally, the C tools' output may change slightly (for example, due to a [recent change](https://www.spinics.net/lists/linux-kbuild/msg17074.html)).
If the test suite reports failures, try running it again against the [linux-next tree](https://www.kernel.org/doc/man-pages/linux-next.html),
which contains the latest updates. Any non-backward-compatible changes will be clearly stated.

A significant amount of time can be spent waiting for `make` and the C utilities to re-parse all Kconfig files for each defconfig test.
Adding multiprocessing to the test suite could help reduce this overhead.

## Notes

- This is version 2 of Kconfiglib, which is not backward-compatible with Kconfiglib 1.
  A summary of changes between Kconfiglib 1 and Kconfiglib 2 can be found
  [here](https://github.com/zephyrproject-rtos/Kconfiglib/blob/screenshots/kconfiglib-2-changes.txt).

- To add custom output formats, it is fairly straightforward to do (see the implementations of `write_autoconf()` and `write_config()`,
  as well as the documentation for the `Symbol.config_string` property).
  If a user develops something that could be useful to others,
  the maintainers are happy to include it upstream—batteries included and all that.
  To contribute, please [open an issue](https://github.com/sysprog21/Kconfiglib/issues) or
  [submit a pull request](https://github.com/sysprog21/Kconfiglib/pulls).

## Thanks

- To [RomaVis](https://github.com/RomaVis) for creating [pymenuconfig](https://github.com/RomaVis/pymenuconfig)
  and suggesting the `rsource` keyword.
- To [Mitja Horvat](https://github.com/pinkfluid) for adding support for user-defined styles to the terminal menuconfig.
- To [Philip Craig](https://github.com/philipc) for adding support for the `allnoconfig_y` option
  and fixing an obscure issue involving `comment`s within `choice`s.
  Although it did not affect correctness, it caused outputs to differ.
  The `allnoconfig_y` option is used to force certain symbols to `y` during `make allnoconfig` to improve coverage.

## License

See [LICENSE](LICENSE).
SPDX license identifiers are used throughout the source code.
