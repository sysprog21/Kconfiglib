# Kconfiglib

## Overview

Kconfiglib is a
[Kconfig](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-language.rst)
implementation in Python. It started out as a helper library,
but now has a enough functionality to also work well as a standalone Kconfig
implementation (including [terminal and GUI menuconfig interfaces](#menuconfig-interfaces) and
[Kconfig extensions](#kconfig-extensions)).

The entire library is contained in
[kconfiglib.py](https://github.com/zephyrproject-rtos/Kconfiglib/blob/main/kconfiglib.py).
The bundled scripts are implemented on top of it. Implementing your own scripts should be relatively easy, if needed.

Kconfiglib is used exclusively by e.g. the
[Zephyr](https://www.zephyrproject.org/) and
[esp-idf](https://github.com/espressif/esp-idf) prohects.
It is also used for many small helper scripts in various projects.

Since Kconfiglib is based around a library, it can be used e.g. to generate a
[Kconfig cross-reference](https://docs.zephyrproject.org/latest/reference/kconfig/index.html),
using the same robust Kconfig parser used for other Kconfig tools, instead of brittle ad-hoc parsing.

Kconfiglib implements the recently added
[Kconfig preprocessor](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-macro-language.rst).
For backwards compatibility, environment variables can be referenced both as `$(FOO)` (the new syntax) and as `$FOO` (the old syntax).
The old syntax is deprecated, but will probably be supported for a long time,
as it is needed to stay compatible with older Linux kernels.
The major version will be increased if support is ever dropped.
Using the old syntax with an undefined environment variable keeps the string as is.

See [Kconfig: Tips and Best Practices](https://docs.zephyrproject.org/latest/build/kconfig/tips.html).

## Installation

### Installation with pip

Kconfiglib is available on
[PyPI](https://pypi.python.org/pypi/kconfiglib/) and can be installed
with e.g.
```shell
$ pip install kconfiglib
```

Microsoft Windows is supported.

The `pip` installation will give you both the base library and the
following executables. All but two (`genconfig` and `setconfig`) mirror
functionality available in the C tools.

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

`genconfig` is intended to be run at build time.
It generates a C header from the configuration and (optionally) information that can be used to
rebuild only files that reference Kconfig symbols that have changed value.

Starting with Kconfiglib version 12.2.0, all utilities are compatible with both Python 2 and Python 3.
Previously, `menuconfig.py` only ran under Python 3 (i.e., it is now more backwards compatible than before).

**Note:** If you install Kconfiglib with `pip`\'s `--user` flag,
make sure that your `PATH` includes the directory where the executables end up.
You can list the installed files with `pip show -f kconfiglib`.

All releases have a corresponding tag in the git repository, e.g. `v14.1.0` (the latest version).

[Semantic versioning](http://semver.org/) is used.
I do major version bumps for all behavior changes, even tiny ones,
and most of these were fixes for baby issues in the early days of the Kconfiglib 2 API.

### Manual installation

Just drop `kconfiglib.py` and the scripts you want somewhere.
There are no third-party dependencies, but the terminal `menuconfig` will not work on Windows unless a package like
[windows-curses](https://github.com/zephyrproject-rtos/windows-curses)
is installed.

### Installation for the Linux kernel

See the module docstring at the top of
[kconfiglib.py](https://github.com/zephyrproject-rtos/Kconfiglib/blob/main/kconfiglib.py).

### Python version compatibility (2.7/3.2+)

Kconfiglib and all utilities run under both Python 2.7 and Python 3.2 and later.
The code mostly uses basic Python features and has no third-party dependencies,
so keeping it backwards-compatible is pretty low effort.

The 3.2 requirement comes from `argparse`. `format()` with unnumbered `{}` is used as well.

A recent Python 3 version is recommended if you have a choice, as it will give you better Unicode handling.

## Getting started

1.  [Install](#installation) the library and the utilities.

2.  Write [Kconfig](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-language.rst)
    files that describe the available configuration options.
    See [Tips and Best Practices](https://docs.zephyrproject.org/latest/guides/kconfig/tips.html)
    for some general Kconfig advice.

3.  Generate an initial configuration with e.g. `menuconfig`, `guiconfig`, or `alldefconfig`.
    The configuration is saved as `.config` by default.

    For more advanced projects, the `defconfig` utility can be used to generate the initial configuration from an existing configuration
    file. Usually, this existing configuration file would be a minimal configuration file, as generated by e.g. `savedefconfig`.

4.  Run `genconfig` to generate a header file. By default, it is saved as `config.h`.

    Normally, `genconfig` would be run automatically as part of the build.

    Before writing a header file or other configuration output,
    Kconfiglib compares the old contents of the file against the new contents.
    If there is no change, the write is skipped.
    This avoids updating file metadata like the modification time,
    and might save work depending on your build setup.

    Adding new configuration output formats should be relatively straightforward.
    See the implementation of `write_config()` in [kconfiglib.py](kconfiglib.py).
    The documentation for the `Symbol.config_string` property has some tips as well.

5.  To update an old `.config` file after the Kconfig files have changed (e.g. to add new options),
    run `oldconfig` (prompts for values for new options) or `olddefconfig`
    (gives new options their default value).
    Entering the `menuconfig` or `guiconfig` interface and saving the configuration will also update it
    (the configuration interfaces always prompt for saving on exit if it would modify the
    contents of the `.config` file).

    Due to Kconfig semantics, simply loading an old `.config` file performs an implicit `olddefconfig`,
    so building will normally not be affected by having an outdated configuration.

Whenever `.config` is overwritten, the previous version of the file is saved to `.config.old`
(or, more generally, to `$KCONFIG_CONFIG.old`).

### Using `.config` files as Make input

`.config` files use Make syntax and can be included directly in Makefiles to read configuration values from there.
This is why `n`-valued `bool`/`tristate` values are written out as `# CONFIG_FOO is not set` (a Make comment) in `.config`,
allowing them to be tested with `ifdef` in Make.

If you make use of this, you might want to pass `--config-out <filename>` to `genconfig` and
include the configuration file it generates instead of including `.config` directly.
This has the advantage that the generated configuration file will always be a \"full\" configuration file,
even if `.config` is outdated.
Otherwise, it might be necessary to run `old(def)config` or `menuconfig` / `guiconfig` before rebuilding with an outdated `.config`.

If you use `--sync-deps` to generate incremental build information,
you can include `deps/auto.conf` instead, which is also a full configuration file.

### Useful helper macros

The
[include/linux/kconfig.h](https://github.com/torvalds/linux/blob/master/include/linux/kconfig.h)
header in the Linux kernel defines some useful helper macros for testing Kconfig configuration values.

`IS_ENABLED()` is generally useful, allowing configuration values to be tested in `if` statements with no runtime overhead.

### Incremental building

See the docstring for `Kconfig.sync_deps()` in
[kconfiglib.py](kconfiglib.py)
for hints on implementing incremental builds (rebuilding just source files that reference changed configuration values).

Running the `scripts/basic/fixdep.c` tool from the kernel on the output of `gcc -MD <source file>`
might give you an idea of how it all fits together.

## Library documentation

Kconfiglib comes with extensive documentation in the form of docstrings.
To view it, run e.g. the following command:
```shell
$ pydoc kconfiglib
```

For HTML output, add `-w`:
```shell
$ pydoc -w kconfiglib
```

This will also work after installing Kconfiglib with `pip`.

Documentation for other modules can be viewed in the same way (though a plain `--help` will work when they are run as executables):
```shell
$ pydoc menuconfig/guiconfig/...
```

A good starting point for learning the library is to read the module docstring
(which you could also just read directly at the beginning of [kconfiglib.py](kconfiglib.py)).
It gives an introduction to symbol values, the menu tree, and expressions.

After reading the module docstring, a good next step is to read the `Kconfig` class documentation,
and then the documentation for the `Symbol`, `Choice`, and `MenuNode` classes.

Please tell me if something is unclear or can be explained better.

## Library features

Kconfiglib can do the following, among other things:

-   **Programmatically get and set symbol values**
    See
    [allnoconfig.py](allnoconfig.py)
    and
    [allyesconfig.py](allyesconfig.py),
    which are automatically verified to produce identical output to the standard
    `make allnoconfig` and `make allyesconfig`.

-   **Read and write .config and defconfig files**

    The generated `.config` and `defconfig` (minimal configuration) files are
    character-for-character identical to what the C implementation would generate
    (except for the header comment).
    The test suite relies on this, as it compares the generated files.

-   **Write C headers**

    The generated headers use the same format as `include/generated/autoconf.h` from the Linux kernel.
    Output for symbols appears in the order that they are defined,
    unlike in the C tools (where the order depends on the hash table implementation).

-   **Implement incremental builds**

    This uses the same scheme as the `include/config` directory in the kernel:
    Symbols are translated into files that are touched when the symbol\'s value changes between builds,
    which can be used to avoid having to do a full rebuild whenever the configuration is changed.

    See the `sync_deps()` function for more information.

-   **Inspect symbols**

    Printing a symbol or other item (which calls `__str__()`) returns its definition in Kconfig format.
    This also works for symbols defined in multiple locations.

    A helpful `__repr__()` is on all objects too.

    All `__str__()` and `__repr__()` methods are deliberately
    implemented with just public APIs, so all symbol information can be
    fetched separately as well.

-   **Inspect expressions**

    Expressions use a simple tuple-based format that can be processed manually if needed.
    Expression printing and evaluation functions are provided, implemented with public APIs.

-   **Inspect the menu tree**

    The underlying menu tree is exposed, including submenus created implicitly from symbols depending on preceding symbols.
    This can be used e.g. to implement menuconfig-like functionality.

    See
    [menuconfig.py](menuconfig.py),
    [guiconfig.py](guiconfig.py),
    and the minimalistic
    [menuconfig_example.py](examples/menuconfig_example.py)
    example.

### Kconfig extensions

The following Kconfig extensions are available:

-   `source` supports glob patterns and includes each matching file.
    A pattern is required to match at least one file.

    A separate `osource` statement is available for cases where it is okay for the pattern to match no files
    (in which case `osource` turns into a no-op).

-   A relative `source` statement (`rsource`) is available,
    where file paths are specified relative to the directory of the current Kconfig file.
    An `orsource` statement is available as well, analogous to `osource`.

-   Preprocessor user functions can be defined in Python, which makes it simple to integrate
    information from existing Python tools into Kconfig (e.g. to have Kconfig symbols depend on
    hardware information stored in some other format).

    See the *Kconfig extensions* section in the
    [kconfiglib.py](kconfiglib.py)
    module docstring for more information.

-   `def_int`, `def_hex`, and `def_string` are available in addition to `def_bool` and `def_tristate`,
    allowing `int`, `hex`, and `string` symbols to be given a type and a default at the same time.

    These can be useful in projects that make use of symbols defined in multiple locations,
    and remove some Kconfig inconsistency.

-   Environment variables are expanded directly in e.g. `source` and
    `mainmenu` statements, meaning `option env` symbols are redundant.

    This is the standard behavior with the new
    [Kconfig preprocessor](https://github.com/torvalds/linux/blob/master/Documentation/kbuild/kconfig-macro-language.rst),
    which Kconfiglib implements.

    `option env` symbols are accepted but ignored, which leads the caveat that they must have the same name as the environment
    variables they reference (Kconfiglib warns if the names differ).
    This keeps Kconfiglib compatible with older Linux kernels,
    where the name of the `option env` symbol always matched the environment variable.
    Compatibility with older Linux kernels is the main reason `option env` is still supported.

    The C tools have dropped support for `option env`.

-   Two extra optional warnings can be enabled by setting environment variables,
    covering cases that are easily missed when making changes to Kconfig files:

    -   `KCONFIG_WARN_UNDEF`: If set to `y`, warnings will be generated
        for all references to undefined symbols within Kconfig files.
        The only gotcha is that all hex literals must be prefixed with
        `0x` or `0X`, to make it possible to distinguish them from
        symbol references.

        Some projects (e.g. the Linux kernel) use multiple Kconfig trees
        with many shared Kconfig files, leading to some safe undefined
        symbol references. `KCONFIG_WARN_UNDEF` is useful in projects
        that only have a single Kconfig tree though.

        `KCONFIG_STRICT` is an older alias for this environment
        variable, supported for backwards compatibility.

    -   `KCONFIG_WARN_UNDEF_ASSIGN`: If set to `y`, warnings will be
        generated for all assignments to undefined symbols within
        `.config` files. By default, no such warnings are generated.

        This warning can also be enabled/disabled by setting
        `Kconfig.warn_assign_undef` to `True`/`False`.

## Other features

-   **Single-file implementation**

    The entire library is contained in [kconfiglib.py](kconfiglib.py).

    The tools implemented on top of it are one file each.

-   **Robust and highly compatible with the C Kconfig tools**

    The [test suite](testsuite.py) automatically compares output from Kconfiglib
    and the C tools by diffing the generated `.config` files for the real kernel Kconfig
    and defconfig files, for all ARCHes.

    This currently involves comparing the output for 36 ARCHes and 498 defconfig files
    (or over 18000 ARCH/defconfig combinations in \"obsessive\" test suite mode). All tests are expected to pass.

    A comprehensive suite of selftests is included as well.

-   **Not horribly slow despite being a pure Python implementation**

    The [allyesconfig.py](allyesconfig.py) script currently runs in about 1.3 seconds on the Linux kernel
    on a Core i7 2600K (with a warm file cache), including the `make` overhead from `make scriptconfig`.
    Note that the Linux kernel Kconfigs are absolutely massive (over 14k symbols for x86) compared
    to most projects, and also have overhead from running shell commands
    via the Kconfig preprocessor.

    Kconfiglib is especially speedy in cases where multiple `.config`
    files need to be processed, because the `Kconfig` files will only
    need to be parsed once.

    For long-running jobs, [PyPy](https://pypy.org/) gives a big
    performance boost. CPython is faster for short-running jobs as PyPy
    needs some time to warm up.

    Kconfiglib also works well with the
    [multiprocessing](https://docs.python.org/3/library/multiprocessing.html)
    module. No global state is kept.

-   **Generates more warnings than the C implementation**

    Generates the same warnings as the C implementation, plus additional
    ones. Also detects dependency and `source` loops.

    All warnings point out the location(s) in the `Kconfig` files where
    a symbol is defined, where applicable.

-   **Unicode support**

    Unicode characters in string literals in `Kconfig` and `.config`
    files are correctly handled. This support mostly comes for free from
    Python.

-   **Windows support**

    Nothing Linux-specific is used. Universal newlines mode is used for
    both Python 2 and Python 3.

    The [Zephyr](https://www.zephyrproject.org/) project uses Kconfiglib
    to generate `.config` files and C headers on Linux as well as
    Windows.

-   **Internals that (mostly) mirror the C implementation**

    While being simpler to understand and tweak.

## Menuconfig interfaces

Three configuration interfaces are currently available:

-   [menuconfig.py](menuconfig.py)
    is a terminal-based configuration interface implemented using the
    standard Python `curses` module. `xconfig` features like showing
    invisible symbols and showing symbol names are included,
    and it is possible to jump directly to a symbol in the menu tree (even if it is currently invisible).

    ![image](https://raw.githubusercontent.com/zephyrproject-rtos/Kconfiglib/screenshots/screenshots/menuconfig.gif)

    *There is now also a show-help mode that shows the help text of the currently selected symbol in the help window at the bottom.*

    Starting with Kconfiglib 12.2.0, `menuconfig.py` runs under both Python 2 and Python 3
    (previously, it only ran under Python 3, so this was a backport).
    Running it under Python 3 provides better support for Unicode text entry (`get_wch()` is not available in the
    `curses` module on Python 2).

    There are no third-party dependencies on \*nix.
    On Windows, the `curses` modules is not available by default,
    but support can be added by installing the `windows-curses` package:
    ```shell
    $ pip install windows-curses
    ```

    This uses wheels built from [this repository](https://github.com/zephyrproject-rtos/windows-curses),
    which is in turn based on Christoph Gohlke\'s
    [Python Extension Packages for Windows](https://www.cgohlke.com/#curses).

    See the docstring at the top of [menuconfig.py](menuconfig.py)
    for more information about the terminal menuconfig implementation.

-   [guiconfig.py](guiconfig.py)
    is a graphical configuration interface written in
    [Tkinter](https://docs.python.org/3/library/tkinter.html).
    Like `menuconfig.py`, it supports showing all symbols (with invisible symbols in red) and
    jumping directly to symbols.
    Symbol values can also be changed directly from the jump-to dialog.

    When single-menu mode is enabled, a single menu is shown at a time,
    like in the terminal menuconfig.
    Only this mode distinguishes between symbols defined with `config` and symbols defined with `menuconfig`.

    `guiconfig.py` has been tested on X11, Windows, and macOS, and is
    compatible with both Python 2 and Python 3.

    Despite being part of the Python standard library, `tkinter` often
    is not included by default in Python installations on Linux.
    These commands will install it on a few different distributions:

    -   Ubuntu/Debian:
        `sudo apt install python-tk` / `sudo apt install python3-tk`
    -   Fedora:
        `dnf install python2-tkinter` / `dnf install python3-tkinter`
    -   Arch: `sudo pacman -S tk`
    -   Clear Linux: `sudo swupd bundle-add python3-tcl`

    Screenshot below, with show-all mode enabled and the jump-to dialog
    open:
    ![image](https://raw.githubusercontent.com/zephyrproject-rtos/Kconfiglib/screenshots/screenshots/guiconfig.png)

    To avoid having to carry around a bunch of GIFs, the image data is embedded in `guiconfig.py`.
    To use separate GIF files instead, change `_USE_EMBEDDED_IMAGES` to `False` in `guiconfig.py`.
    The image files can be found in the
    [screenshots](https://github.com/zephyrproject-rtos/Kconfiglib/tree/screenshots/guiconfig)
    branch.

    I did my best with the images, but some are definitely only art adjacent.
    Touch-ups are welcome. :)

-   [pymenuconfig](https://github.com/RomaVis/pymenuconfig),
    built by [RomaVis](https://github.com/RomaVis),
    is an older portable Python 2/3 TkInter menuconfig implementation.

    Screenshot below:
    ![image](https://raw.githubusercontent.com/RomaVis/pymenuconfig/master/screenshot.PNG)

    While working on the terminal menuconfig implementation, I added a few APIs to Kconfiglib that turned out to be handy.
    `pymenuconfig` predates `menuconfig.py` and `guiconfig.py`,
    and so did not have them available.
    Blame me for any workarounds.

## Examples

### Example scripts

The [examples/](examples) directory contains some simple example scripts.
Among these are the following ones.
Make sure you run them with the latest version of Kconfiglib, as they might make use of newly added features.

-   [eval\_expr.py](examples/eval_expr.py)
    evaluates an expression in the context of a configuration.
-   [find\_symbol.py](examples/find_symbol.py)
    searches through expressions to find references to a symbol, also
    printing a \"backtrace\" with parents for each reference found.
-   [help\_grep.py](examples/help_grep.py)
    searches for a string in all help texts.
-   [print\_tree.py](examples/print_tree.py)
    prints a tree of all configuration items.
-   [print\_config\_tree.py](examples/print_config_tree.py)
    is similar to `print_tree.py`, but dumps the tree as it would appear
    in `menuconfig`, including values. This can be handy for visually
    diffing between `.config` files and different versions of `Kconfig`
    files.
-   [list\_undefined.py](examples/list_undefined.py)
    finds references to symbols that are not defined by any architecture
    in the Linux kernel.
-   [merge\_config.py](examples/merge_config.py)
    merges configuration fragments to produce a complete .config,
    similarly to `scripts/kconfig/merge_config.sh` from the kernel.
-   [menuconfig\_example.py](examples/menuconfig_example.py)
    implements a configuration interface that uses notation similar to
    `make menuconfig`. It is deliberately kept as simple as possible to
    demonstrate just the core concepts.

### Real-world examples

-   [kconfig.py](https://github.com/zephyrproject-rtos/zephyr/blob/main/scripts/kconfig/kconfig.py)
    from the [Zephyr](https://www.zephyrproject.org/) project handles
    `.config` and header file generation, also doing configuration
    fragment merging
-   [CMake and IDE integration](https://github.com/espressif/esp-idf/tree/master/tools/kconfig_new)
    from the ESP-IDF project, via a configuration server program.

These use the older Kconfiglib 1 API, which was clunkier and not as general (functions instead of properties,
no direct access to the menu structure or properties, uglier `__str__()` output):

-   [genboardscfg.py](http://git.denx.de/?p=u-boot.git;a=blob;f=tools/genboardscfg.py;hb=HEAD)
    from [Das U-Boot](http://www.denx.de/wiki/U-Boot) generates some
    sort of legacy board database by pulling information from a newly
    added Kconfig-based configuration system (as far as I understand it
    :).
-   [gen-manual-lists.py](https://git.busybox.net/buildroot/tree/support/scripts/gen-manual-lists.py?id=5676a2deea896f38123b99781da0a612865adeb0)
    generated listings for an appendix in the
    [Buildroot](https://buildroot.org) manual. (The listing has since
    been removed.)
-   [gen_kconfig_doc.py](https://github.com/espressif/esp-idf/blob/master/docs/gen-kconfig-doc.py)
    from the [esp-idf](https://github.com/espressif/esp-idf) project
    generates documentation from Kconfig files.
-   [SConf](https://github.com/CoryXie/SConf) builds an interactive
    configuration interface (like `menuconfig`) on top of Kconfiglib,
    for use e.g. with [SCons](scons.org).
-   [kconfig-diff.py](https://gist.github.com/dubiousjim/5638961) \-- a
    script by [dubiousjim](https://github.com/dubiousjim) that compares
    kernel configurations.
-   Originally, Kconfiglib was used in chapter 4 of my [master thesis](http://liu.diva-portal.org/smash/get/diva2:473038/FULLTEXT01.pdf)
    to automatically generate a \"minimal\" kernel for a given system.
    Parts of it bother me a bit now,
    but that is how it goes with old work.

### Sample `make iscriptconfig` session

The following log should give some idea of the functionality available
in the API:

``` 
$ make iscriptconfig
A Kconfig instance 'kconf' for the architecture x86 has been created.
>>> kconf  # Calls Kconfig.__repr__()
<configuration with 13711 symbols, main menu prompt "Linux/x86 4.14.0-rc7 Kernel Configuration", srctree ".", config symbol prefix "CONFIG_", warnings enabled, undef. symbol assignment warnings disabled>
>>> kconf.mainmenu_text  # Expanded main menu text
'Linux/x86 4.14.0-rc7 Kernel Configuration'
>>> kconf.top_node  # The implicit top-level menu
<menu node for menu, prompt "Linux/x86 4.14.0-rc7 Kernel Configuration" (visibility y), deps y, 'visible if' deps y, has child, Kconfig:5>
>>> kconf.top_node.list  # First child menu node
<menu node for symbol SRCARCH, deps y, has next, Kconfig:7>
>>> print(kconf.top_node.list)  # Calls MenuNode.__str__()
config SRCARCH
    string
    option env="SRCARCH"
    default "x86"
>>> sym = kconf.top_node.list.next.item  # Item contained in next menu node
>>> print(sym)  # Calls Symbol.__str__()
config 64BIT
    bool "64-bit kernel" if ARCH = "x86"
    default ARCH != "i386"
    help
      Say yes to build a 64-bit kernel - formerly known as x86_64
      Say no to build a 32-bit kernel - formerly known as i386
>>> sym  # Calls Symbol.__repr__()
<symbol 64BIT, bool, "64-bit kernel", value y, visibility y, direct deps y, arch/x86/Kconfig:2>
>>> sym.assignable  # Currently assignable values (0, 1, 2 = n, m, y)
(0, 2)
>>> sym.set_value(0)  # Set it to n
True
>>> sym.tri_value  # Check the new value
0
>>> sym = kconf.syms["X86_MPPARSE"]  # Look up symbol by name
>>> print(sym)
config X86_MPPARSE
    bool "Enable MPS table" if (ACPI || SFI) && X86_LOCAL_APIC
    default y if X86_LOCAL_APIC
    help
      For old smp systems that do not have proper acpi support. Newer systems
      (esp with 64bit cpus) with acpi support, MADT and DSDT will override it
>>> default = sym.defaults[0]  # Fetch its first default
>>> sym = default[1]  # Fetch the default's condition (just a Symbol here)
>>> print(sym)
config X86_LOCAL_APIC
    bool
    default y
    select IRQ_DOMAIN_HIERARCHY
    select PCI_MSI_IRQ_DOMAIN if PCI_MSI
    depends on X86_64 || SMP || X86_32_NON_STANDARD || X86_UP_APIC || PCI_MSI
>>> sym.nodes  # Show the MenuNode(s) associated with it
[<menu node for symbol X86_LOCAL_APIC, deps n, has next, arch/x86/Kconfig:1015>]
>>> kconfiglib.expr_str(sym.defaults[0][1])  # Print the default's condition
'X86_64 || SMP || X86_32_NON_STANDARD || X86_UP_APIC || PCI_MSI'
>>> kconfiglib.expr_value(sym.defaults[0][1])  # Evaluate it (0 = n)
0
>>> kconf.syms["64BIT"].set_value(2)
True
>>> kconfiglib.expr_value(sym.defaults[0][1])  # Evaluate it again (2 = y)
2
>>> kconf.write_config("myconfig")  # Save a .config
>>> ^D
$ cat myconfig
# Generated by Kconfiglib (https://github.com/zephyrproject-rtos/Kconfiglib)
CONFIG_64BIT=y
CONFIG_X86_64=y
CONFIG_X86=y
CONFIG_INSTRUCTION_DECODER=y
CONFIG_OUTPUT_FORMAT="elf64-x86-64"
CONFIG_ARCH_DEFCONFIG="arch/x86/configs/x86_64_defconfig"
CONFIG_LOCKDEP_SUPPORT=y
CONFIG_STACKTRACE_SUPPORT=y
CONFIG_MMU=y
...
```

## Test suite

The test suite is run with
```shell
$ python Kconfiglib/testsuite.py
```

[pypy](https://pypy.org/) works too, and is much speedier for everything
except `allnoconfig.py`/`allnoconfig_simpler.py`/`allyesconfig.py`,
where it doesn\'t have time to warm up since the scripts are run via
`make scriptconfig`.

The test suite must be run from the top-level kernel directory. It
requires that the Kconfiglib git repository has been cloned into it and
that the makefile patch has been applied.

To get rid of warnings generated for the kernel `Kconfig` files, add
`2>/dev/null` to the command to discard `stderr`.

**NOTE: Forgetting to apply the Makefile patch will cause some tests
that compare generated configurations to fail**

**NOTE: The test suite overwrites .config in the kernel root, so make
sure to back it up.**

The test suite consists of a set of selftests and a set of compatibility
tests that compare configurations generated by Kconfiglib with
configurations generated by the C tools, for a number of cases. See
[testsuite.py](testsuite.py)
for the available options.

The
[tests/reltest](tests/reltest)
script runs the test suite and all the example scripts for both Python 2
and Python 3, verifying that everything works.

Rarely, the output from the C tools is changed slightly (most recently
due to a
[change](https://www.spinics.net/lists/linux-kbuild/msg17074.html) I
added). If you get test suite failures, try running the test suite again
against the [linux-next tree](https://www.kernel.org/doc/man-pages/linux-next.html), which has
all the latest changes. I will make it clear if any
non-backwards-compatible changes appear.

A lot of time is spent waiting around for `make` and the C utilities
(which need to reparse all the Kconfig files for each defconfig test).
Adding some multiprocessing to the test suite would make sense too.

## Notes

-   This is version 2 of Kconfiglib, which is not backwards-compatible
    with Kconfiglib 1. A summary of changes between Kconfiglib 1 and
    Kconfiglib 2 can be found
    [here](https://github.com/zephyrproject-rtos/Kconfiglib/blob/screenshots/kconfiglib-2-changes.txt).

-   I sometimes see people add custom output formats, which is pretty
    straightforward to do (see the implementations of `write_autoconf()`
    and `write_config()` for a template, and also the documentation of
    the `Symbol.config_string` property). If you come up with something
    you think might be useful to other people, I\'m happy to take it in
    upstream. Batteries included and all that.

-   Kconfiglib assumes the modules symbol is `MODULES`, which is
    backwards-compatible. A warning is printed by default if
    `option modules` is set on some other symbol.

    Let me know if you need proper `option modules` support.
    It would not be that hard to add.

## Thanks

-   To [RomaVis](https://github.com/RomaVis), for making
    [pymenuconfig](https://github.com/RomaVis/pymenuconfig) and
    suggesting the `rsource` keyword.
-   To [Mitja Horvat](https://github.com/pinkfluid), for adding support
    for user-defined styles to the terminal menuconfig.
-   To [Philip Craig](https://github.com/philipc) for adding support for
    the `allnoconfig_y` option and fixing an obscure issue with
    `comment`s inside `choice`s (that didn\'t affect correctness but
    made outputs differ). `allnoconfig_y` is used to force certain
    symbols to `y` during `make allnoconfig` to improve coverage.

## License

See [LICENSE](LICENSE).
SPDX license identifiers are used in the source code.
