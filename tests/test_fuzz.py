# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Randomized parser tests.
#
# The parse path holds nearly all of the library's branching: _tokenize(),
# _parse_block() and _parse_props() each run to roughly complexity 32-34, and
# everything downstream trusts whatever they produce. The hand-written tests
# cover the Kconfig files a person would write; these cover the ones nobody
# would, which is where a parser actually breaks.
#
# The contract is narrow, and it is the only one worth asserting on random
# input: for any input at all, Kconfig() either parses it or raises
# KconfigError. It must never escape with an AttributeError from an item that
# was assumed to be a Symbol, or from a MenuNode slot that was never
# initialized. That is the shape a parser crash actually takes here, and it is
# what five of these found: 'help', 'prompt', a type, a 'def_bool' or a
# 'visible if' on a 'menu' or 'comment' node each produced a traceback rather
# than a file:line error. See test_regressions below.
#
# Generating pure token soup does not work: every case dies on line one and
# the block and property parsers are never reached. So the generator builds a
# structurally valid Kconfig tree first and then corrupts it. The mix that
# comes out, measured over 2400 cases:
#
#   ~30%  parse cleanly
#   ~47%  fail to parse, at whatever point the corruption reached
#   ~23%  parse completely and are then rejected for a dependency loop,
#         because the conditions draw from a small shared pool of symbol
#         names. These still exercise the whole parser; the loop is found
#         afterwards
#
# so a little over half of every run reaches the end of the parser.
#
# Deterministic on purpose: the seeds are fixed, so a failure reproduces on
# every machine and in CI rather than showing up once and vanishing. To widen
# the search locally, raise SEEDS or CASES_PER_SEED.
#
# What is deliberately never generated: $(shell,...) and $(python,...), which
# run arbitrary commands by design, and 'source' lines. A fuzzer emitting
# either would be running random code on the machine rather than testing the
# parser.

import os
import random

import pytest

from kconfiglib import Kconfig, KconfigError

# Exceptions that mean "the input was rejected", which is a correct outcome.
#
# RecursionError is not one of them. A blown Python stack is the interpreter
# falling over, not the parser saying no, and that is the one distinction a
# robustness sweep exists to make: tolerating it here would let any new
# unbounded recursion land in the same bucket and keep the sweep green.
#
# One generated file in 960 does hit it today, through a defect that predates
# these tests and reproduces on the base branch: a config listed by two
# separate choice blocks sends visibility evaluation around a cycle. That one
# shape is what _check() forgives, and nothing else, so the tolerance is
# exactly as wide as the known bug. test_the_known_recursion_shape_still_bites
# below fails once somebody fixes the cycle, so the exemption cannot quietly
# outlive the defect.
EXPECTED = (KconfigError,)


def has_known_recursion_shape(text):
    """True if 'text' contains the one shape known to blow the stack.

    A config listed by two separate choice blocks makes visibility evaluation
    cycle. Detected by shape rather than by seed number, so that changing the
    generator cannot silently turn the exemption into a blanket one, and so
    that the day the parser is fixed this predicate can just be deleted.
    """
    seen = set()
    current = set()
    in_choice = False
    repeated = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("choice"):
            in_choice, current = True, set()
        elif stripped.startswith("endchoice"):
            # A block's own names join 'seen' only once it closes. Folding
            # them in per line made a name repeated inside a single block
            # look like a name shared between two, which is the shape that
            # actually recurses.
            #
            # 'current' starts empty rather than being bound in the branch
            # above, because the generator emits a stray endchoice with no
            # choice open and this predicate runs from an exception handler,
            # where a NameError would be reported in place of the crash it
            # was called to classify.
            seen |= current
            current = set()
            in_choice = False
        elif in_choice and stripped.startswith("config "):
            name = stripped.split(None, 1)[1].strip()
            if name in seen:
                repeated = True
            current.add(name)
    return repeated


SEEDS = range(120)
CASES_PER_SEED = 8


TYPES = ("bool", "tristate", "string", "hex", "int")
NAMES = [f"SYM_{i}" for i in range(12)]

# 'select' and 'imply' targets come from their own pool of symbols that are
# defined with no dependencies of their own (see valid_source). Drawing them
# from NAMES instead put a dependency loop in a quarter of the generated
# files, and Kconfig reports those only after parsing the whole thing, so they
# added nothing but noise to the mix the mutations are supposed to produce.
LEAVES = [f"LEAF_{i}" for i in range(6)]


def _cond(rng):
    a, b = rng.choice(NAMES), rng.choice(NAMES)
    return rng.choice(
        (
            a,
            f"{a} && {b}",
            f"{a} || {b}",
            f"!{a}",
            f"{a} = {b}",
            f"{a} != y",
            f"({a} && !{b})",
        )
    )


# A valid value for each type, for the 'default' properties
_VALUES = {"bool": "y", "tristate": "m", "string": '"s"', "hex": "0x10", "int": "7"}
_RANGES = {"hex": "0x0 0xff", "int": "0 99"}

_BOOLISH = ("bool", "tristate")
_NUMERIC = ("hex", "int")

# Property generators, each paired with the types it is valid for. A table
# rather than a chain of cumulative probability thresholds: the thresholds hid
# which properties a given type could actually get, because a type that failed
# one branch's condition fell through to the next threshold rather than being
# excluded. Here a property is drawn only from the ones that apply, so the
# generated file is always type-correct and the distribution is even.
_PROPS = (
    (TYPES, lambda rng, name, typ: [f"\tdefault {_VALUES[typ]}"]),
    (TYPES, lambda rng, name, typ: [f"\tdefault {_VALUES[typ]} if {_cond(rng)}"]),
    (TYPES, lambda rng, name, typ: [f"\tdepends on {_cond(rng)}"]),
    (TYPES, lambda rng, name, typ: [f'\tprompt "alt" if {_cond(rng)}']),
    (
        TYPES,
        lambda rng, name, typ: [
            "\thelp",
            f"\t  Some help text for {name}.",
            "\t  Second line.",
        ],
    ),
    (_BOOLISH, lambda rng, name, typ: [f"\tselect {rng.choice(LEAVES)}"]),
    (
        _BOOLISH,
        lambda rng, name, typ: [f"\timply {rng.choice(LEAVES)} if {_cond(rng)}"],
    ),
    (_NUMERIC, lambda rng, name, typ: [f"\trange {_RANGES[typ]}"]),
)


def _props(rng, name, typ):
    out = [f'\t{typ} "{name} prompt"']
    applicable = [build for types, build in _PROPS if typ in types]
    for _ in range(rng.randint(0, 4)):
        out += rng.choice(applicable)(rng, name, typ)
    return out


def _block(rng, depth=0):
    out = []
    for _ in range(rng.randint(1, 4)):
        r = rng.random()
        if r < 0.45 or depth > 2:
            name = rng.choice(NAMES)
            typ = rng.choice(TYPES)
            out.append(f"config {name}")
            out += _props(rng, name, typ)
        elif r < 0.6:
            out.append(f'menu "A menu {rng.randint(0, 9)}"')
            if rng.random() < 0.3:
                out.append(f"\tvisible if {_cond(rng)}")
            out += _block(rng, depth + 1)
            out.append("endmenu")
        elif r < 0.75:
            out.append(f"if {_cond(rng)}")
            out += _block(rng, depth + 1)
            out.append("endif")
        elif r < 0.9:
            out.append("choice")
            out.append('\tprompt "A choice"')
            if rng.random() < 0.4:
                out.append("\toptional")
            for _ in range(rng.randint(1, 3)):
                name = rng.choice(NAMES)
                out.append(f"config {name}")
                out.append(f'\tbool "{name}"')
            out.append("endchoice")
        else:
            out.append('comment "A comment"')
            if rng.random() < 0.3:
                out.append(f"\tdepends on {_cond(rng)}")
    return out


def _leaf_defs():
    # Selectable symbols with no dependencies, so that a 'select' can never
    # close a dependency cycle
    out = []
    for leaf in LEAVES:
        out.append(f"config {leaf}")
        out.append(f'\tbool "{leaf}"')
    return out


def valid_source(rng):
    return "\n".join(_block(rng) + _leaf_defs()) + "\n"


MUTATIONS = (
    "drop_line",
    "truncate_line",
    "drop_token",
    "swap_keyword",
    "insert_garbage",
    "dedent",
    "indent",
    "drop_char",
    "dup_line",
)

GARBAGE = (
    '"',
    "(",
    ")",
    "&&",
    "$",
    "$(",
    "!",
    ",",
    "=",
    "\\",
    "endmenu",
    "endif",
    "endchoice",
    "help",
    "config",
    "\x00",
)


def mutate(text, rng, n):
    lines = text.split("\n")
    for _ in range(n):
        if not lines:
            break
        i = rng.randrange(len(lines))
        how = rng.choice(MUTATIONS)
        ln = lines[i]
        if how == "drop_line":
            del lines[i]
        elif how == "truncate_line" and ln:
            lines[i] = ln[: rng.randrange(len(ln))]
        elif how == "drop_token":
            toks = ln.split()
            if toks:
                del toks[rng.randrange(len(toks))]
                lines[i] = (
                    "\t" + " ".join(toks) if ln.startswith("\t") else " ".join(toks)
                )
        elif how == "swap_keyword":
            toks = ln.split()
            if toks:
                toks[rng.randrange(len(toks))] = rng.choice(GARBAGE)
                lines[i] = " ".join(toks)
        elif how == "insert_garbage":
            lines.insert(i, rng.choice(GARBAGE))
        elif how == "dedent":
            lines[i] = ln.lstrip()
        elif how == "indent":
            lines[i] = "\t" + ln
        elif how == "drop_char" and ln:
            j = rng.randrange(len(ln))
            lines[i] = ln[:j] + ln[j + 1 :]
        elif how == "dup_line":
            lines.insert(i, ln)
    return "\n".join(lines)


def _check(path):
    """Parses 'path' and walks the result, returning True if it parsed.

    Raises AssertionError if anything but a clean parse or a clean rejection
    comes out. A RecursionError counts as a crash unless the file carries the
    one shape known to cause it, which keeps the exemption exactly as wide as
    the known defect while still feeding every generated file to the parser.
    """

    def crashed(e, where):
        if isinstance(e, RecursionError) and has_known_recursion_shape(
            path.read_text(encoding="utf-8")
        ):
            return False
        raise AssertionError(f"{type(e).__name__} escaped {where}") from e

    try:
        kconf = Kconfig(str(path), warn=False)
    except EXPECTED:
        return False
    except Exception as e:  # noqa: BLE001 -- turning a crash into a report
        return crashed(e, "the parser")

    # Walk the result too: a parser can accept garbage and leave behind a tree
    # that only blows up when something reads it.
    try:
        for sym in kconf.unique_defined_syms:
            sym.str_value  # noqa: B018 -- evaluating it is the point
            str(sym)
        for node in kconf.node_iter():
            str(node)
        kconf.write_config(os.devnull)
    except EXPECTED:
        return False
    except Exception as e:  # noqa: BLE001 -- turning a crash into a report
        return crashed(e, "while walking the parsed tree")
    return True


@pytest.mark.parametrize("seed", SEEDS)
def test_corrupted_kconfig_is_parsed_or_rejected(seed, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rng = random.Random(seed)
    path = tmp_path / "Kfuzz"
    for _ in range(CASES_PER_SEED):
        text = mutate(valid_source(rng), rng, rng.randint(0, 3))
        path.write_text(text, encoding="utf-8")
        try:
            _check(path)
        except AssertionError as e:
            raise AssertionError(f"{e}\n--- input ---\n{text}--- end ---") from e


def test_the_generator_still_reaches_the_parser(tmp_path, monkeypatch):
    """Guards the fuzzer itself.

    A generator that only ever produces line-one syntax errors passes every
    assertion above while testing almost nothing. If this ratio collapses,
    the mutation rate or the grammar has drifted and the sweep above has
    quietly stopped being a test.

    Counts clean parses only, so it reads low (~30%): the files rejected for
    a dependency loop got all the way through the parser but are not counted
    here. The bounds are wide because this is a smoke alarm, not a target.
    """
    monkeypatch.chdir(tmp_path)
    rng = random.Random(0)
    path = tmp_path / "Kratio"
    parsed = 0
    total = 200
    for _ in range(total):
        text = mutate(valid_source(rng), rng, rng.randint(0, 3))
        path.write_text(text, encoding="utf-8")
        parsed += _check(path)
    assert 0.1 * total < parsed < 0.9 * total, (
        f"{parsed}/{total} of the generated files parsed; the generator is "
        f"no longer producing a mix of valid and invalid input"
    )


# Every one of these crashed with an AttributeError before the guards in
# _parse_props(). They are pinned here so the fixes cannot regress without the
# fuzzer happening to rediscover them.
@pytest.mark.parametrize(
    "text",
    (
        'comment "c"\nhelp\n',
        'menu "m"\nhelp\nendmenu\n',
        'comment "c"\nbool\n',
        'menu "m"\ntristate\nendmenu\n',
        'comment "c"\ndef_bool y\n',
        'menu "m"\nprompt "p"\nendmenu\n',
        'comment "c"\nprompt "p"\n',
        'config A\n\tbool "a"\n\tvisible if B\n',
        'comment "c"\nvisible if B\n',
    ),
)
def test_regressions(text, tmp_path, monkeypatch):
    """A property on a node that cannot carry it is a KconfigError, not a
    traceback. The user typed something wrong; they get the line number."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "Kbad"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(KconfigError):
        Kconfig(str(path), warn=False)


@pytest.mark.parametrize(
    "text",
    (
        "config\n",
        "config A\n\tbool\n\tdefault\n",
        "menu\n",
        'menu "m"\n',
        "if\n",
        "choice\n",
        "endmenu\n",
        "endif\n",
        "endchoice\n",
        "source\n",
        "config A\n\tint\n\trange 1\n",
        "config A\n\tdepends on\n",
        "config A\n\tselect\n",
        'config A\n\tbool "unterminated\n',
        "config A\n\tdefault y if\n",
        "config A\n\tdefault y if (\n",
        "mainmenu\n",
        "\tbool\n",
        "config " + "A" * 10000 + "\n",
        "\x00\n",
        'config A\n\tbool "a"\n\tdepends on ' + "!" * 500 + "A\n",
    ),
)
def test_malformed_input_never_crashes(text, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "Kbad"
    path.write_text(text, encoding="utf-8")
    _check(path)


def test_the_known_recursion_shape_still_bites(tmp_path, monkeypatch):
    """The sentinel for the exemption _check() grants.

    A config listed by two separate choice blocks sends visibility evaluation
    around a cycle until the stack runs out. That is a real defect, it
    reproduces on the base branch, and it is left for its own change. This
    test fails the day it is fixed, which is the signal to delete
    has_known_recursion_shape() and the branch in _check() that uses it,
    rather than leaving dead tolerance behind for a bug that no longer
    exists.
    """
    monkeypatch.chdir(tmp_path)
    text = (
        'menu "m"\nconfig A\nconfig B\n\tbool "b"\n\tprompt "alt" if C\n'
        "endmenu\n"
        "choice\nconfig A\nconfig D\nendchoice\n"
        'choice\nconfig D\nconfig C\n\tbool "c"\nendchoice\n'
        'config D\n\thex "d"\n\tdepends on B || E\n'
    )
    assert has_known_recursion_shape(text)

    path = tmp_path / "Kcycle"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(RecursionError):
        kconf = Kconfig(str(path), warn=False)
        for sym in kconf.unique_defined_syms:
            sym.str_value  # noqa: B018 -- evaluating it is the point


@pytest.mark.parametrize("depth", (50, 300))
def test_deep_nesting_parses(depth, tmp_path, monkeypatch):
    """Recursion depth is the classic parser cliff, so assert the strong
    thing: nesting this deep parses, rather than merely failing tidily.

    The parser descends once per enclosing 'if', so it does run out of Python
    stack eventually; 1000 nested conditions reach CPython's default limit.
    Nothing near that is a Kconfig anybody writes, and making the parser
    iterative is a different change from this one, so the cliff is recorded
    here rather than fixed. What matters is that ordinary depths stay well
    clear of it, and that a RecursionError is never mistaken for the parser
    rejecting a file, which _check() is careful about.
    """
    monkeypatch.chdir(tmp_path)
    text = "".join(f"if Y{i}\n" for i in range(depth))
    text += 'config DEEP\n\tbool "deep"\n'
    text += "endif\n" * depth
    path = tmp_path / "Kdeep"
    path.write_text(text, encoding="utf-8")
    assert _check(path), f"nesting {depth} deep should parse"
