#!/usr/bin/env python3
# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC

"""Time the phases of a Kconfig load and of the UI hot paths.

Reports each phase separately so that a regression can be attributed rather
than just noticed. Prints a plain table by default, or JSON with --json for
storing as a CI artifact.

There are no pass/fail thresholds here on purpose. Timings taken on shared CI
runners against an external kernel tree are too noisy to gate on until a stable
baseline exists.

Usage:

  # This repository's own Kconfig
  scripts/benchmark.py

  # The kernel tree the conformance job checks out
  cd linux && ARCH=x86 SRCARCH=x86 KERNELVERSION=6.18 \\
      /path/to/scripts/benchmark.py --tree .

  scripts/benchmark.py --json > timings.json
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _positive_int(value):
    value = int(value)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def _best(fn, repeat):
    # Not timeit: its template disables the garbage collector around the timed
    # loop, and how the collector behaves during a parse is exactly what the
    # load phase is here to measure.
    #
    # Best of N. The minimum is the honest number for a CPU-bound phase: noise
    # only ever adds time, so the fastest run is the one least polluted by it.
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - start)
    return best


def bench_load(kconfig_file, repeat):
    """Kconfig() start to finish: parse, finalize, dep graph, loop check."""
    import kconfiglib

    kconf = None

    def once():
        nonlocal kconf
        kconf = kconfiglib.Kconfig(kconfig_file, warn=False)

    seconds = _best(once, repeat)
    return (
        kconf,
        seconds,
        {
            "symbols": len(kconf.unique_defined_syms),
            "choices": len(kconf.unique_choices),
            "menus": len(kconf.menus),
            "files": len(kconf.kconfig_filenames),
        },
    )


def bench_write_config(kconf, repeat):
    """Rendering and writing a .config, which is what genconfig does."""
    devnull = os.devnull
    # save_old=False: write_config() would otherwise try to rename os.devnull
    # to os.devnull + ".old" on every repeat. The rename normally fails and is
    # swallowed, but it succeeds for a privileged user, and destroying /dev/null
    # to time a benchmark is not a trade worth making. It also keeps a stat and
    # a rename out of the measurement.
    return _best(lambda: kconf.write_config(devnull, save_old=False), repeat), {}


def _bench_menu_walk(kconf, repeat, walk):
    # Shared so the two phases cannot drift apart while claiming to walk the
    # same menus
    menus = [kconf.top_node] + [n for n in kconf.menus if n.list]

    def once():
        for menu in menus:
            walk(menu)

    return _best(once, repeat), {"menus_walked": len(menus)}


def bench_shown_nodes(kconf, repeat):
    """menuconfig._shown_nodes() over every menu -- the TUI's per-redraw walk."""
    import menuconfig

    menuconfig._s = menuconfig._State()
    menuconfig._s.kconf = kconf
    menuconfig._s.show_all = False
    return _bench_menu_walk(kconf, repeat, menuconfig._shown_nodes)


def bench_node_str(kconf, repeat):
    """menuconfig._node_str() for every node -- one call per visible row."""
    import menuconfig

    menuconfig._s = menuconfig._State()
    menuconfig._s.kconf = kconf
    menuconfig._s.show_all = True
    menuconfig._s.show_name = False

    nodes = list(kconf.node_iter())

    def once():
        for n in nodes:
            menuconfig._node_str(n)

    return _best(once, repeat), {"nodes": len(nodes)}


def bench_gui_tree_walk(kconf, repeat):
    """guiconfig._shown_full_nodes() -- the part of _update_tree() that scales.

    _update_tree() itself is inseparable from a live Treeview, so this times
    the tree walk it drives rather than the widget updates. A regression in
    how many nodes get visited shows up here; one in Tk itself does not.
    """
    try:
        import guiconfig
    except ImportError as e:
        # guiconfig pulls in tkinter, which is an optional part of a Python
        # installation. Skip this one phase rather than taking the whole run
        # down with it; main() already renders a phase with no timing.
        return None, {"skipped": f"{type(e).__name__}: {e}"}

    guiconfig._kconf = kconf
    guiconfig._show_all = False
    return _bench_menu_walk(kconf, repeat, guiconfig._shown_full_nodes)


def bench_rawterm_render(repeat):
    """rawterm text rendering into an offscreen region, no terminal needed."""
    import rawterm

    # A Terminal built without entering raw mode. Region only stashes it and
    # never calls into it while drawing, so nothing more needs to exist
    term = object.__new__(rawterm.Terminal)

    height, width = 50, 120
    region = rawterm.Region(term, height, width, 0, 0)

    line = "[*] A configuration symbol with a reasonably long prompt"
    style = rawterm.Style(fg=rawterm.Color.WHITE, bg=rawterm.Color.BLUE, bold=True)

    def once():
        for y in range(height):
            region.write(y, 0, line, style, max_len=width)

    return _best(once, repeat), {"cells": height * width}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tree",
        default=".",
        help="directory to run in (default: the current directory)",
    )
    parser.add_argument(
        "--kconfig",
        default="Kconfig",
        help="top-level Kconfig file, relative to --tree (default: Kconfig)",
    )
    parser.add_argument(
        "-n",
        "--repeat",
        type=_positive_int,
        default=5,
        help="runs per phase; the best is reported (default: 5)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    os.chdir(args.tree)
    if not os.path.exists(args.kconfig):
        sys.exit(f"benchmark: no {args.kconfig} in {os.getcwd()}")

    results = {}

    def record(name, phase):
        seconds, info = phase
        results[name] = {"seconds": seconds, **info}

    # bench_load hands back the tree it just parsed, so the later phases do not
    # pay to parse it again -- on a kernel tree that is the single most
    # expensive thing this script does
    kconf, seconds, info = bench_load(args.kconfig, args.repeat)
    results["load"] = {"seconds": seconds, **info}

    record("write_config", bench_write_config(kconf, args.repeat))
    record("menuconfig_shown_nodes", bench_shown_nodes(kconf, args.repeat))
    record("menuconfig_node_str", bench_node_str(kconf, args.repeat))
    record("guiconfig_tree_walk", bench_gui_tree_walk(kconf, args.repeat))
    record("rawterm_render", bench_rawterm_render(args.repeat))

    results["meta"] = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "tree": os.getcwd(),
        "repeat": args.repeat,
    }

    if args.json:
        json.dump(results, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return

    print(f"{'phase':<26} {'best':>10}   detail")
    print("-" * 72)
    for phase, data in results.items():
        if phase == "meta":
            continue
        seconds = data.get("seconds")
        detail = ", ".join(
            f"{k}={v}" for k, v in sorted(data.items()) if k != "seconds"
        )
        if seconds is None:
            print(f"{phase:<26} {'skipped':>10}   {detail}")
        else:
            print(f"{phase:<26} {seconds * 1000:>9.2f}ms   {detail}")
    print("-" * 72)
    meta = results["meta"]
    print(f"Python {meta['python']} on {meta['platform']}, best of {meta['repeat']}")
    print(f"Tree: {meta['tree']}")


if __name__ == "__main__":
    main()
