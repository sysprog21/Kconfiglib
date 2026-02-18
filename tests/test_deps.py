# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# Dependency-related tests:
# direct_dep, conditional dependencies, referenced, 'if' node removal,
# multi-def property copying, and dependency loop detection.

import pytest

from kconfiglib import Kconfig, KconfigError, expr_str

# -- Symbol/Choice.direct_dep ------------------------------------------------


def test_direct_dep():
    c = Kconfig("tests/Kdirdep")

    assert expr_str(c.syms["NO_DEP_SYM"].direct_dep) == "y"
    assert expr_str(c.syms["DEP_SYM"].direct_dep) == "A || (B && C) || !D"

    assert expr_str(c.named_choices["NO_DEP_CHOICE"].direct_dep) == "y"
    assert expr_str(c.named_choices["DEP_CHOICE"].direct_dep) == "A || B || C"


# -- Conditional dependencies ------------------------------------------------


def test_conditional_deps():
    c = Kconfig("tests/Kconddep")

    assert expr_str(c.syms["COND_DEP_1"].direct_dep) == "!B || A"
    assert expr_str(c.syms["COND_DEP_2"].direct_dep) == "!E || (C && D)"
    assert expr_str(c.syms["COND_DEP_MIXED"].direct_dep) == "A && (!C || B) && D"
    assert expr_str(c.named_choices["COND_CHOICE"].direct_dep) == "!Y || X"
    assert expr_str(c.syms["MULTI_COND"].direct_dep) == "(!B || A) && (!D || C)"


# -- MenuNode/Symbol/Choice.referenced ---------------------------------------


def test_referenced():
    c = Kconfig("tests/Kreferenced", warn=False)

    def verify_refs(item, *dep_names):
        assert tuple(sorted(item.name for item in item.referenced)) == dep_names

    verify_refs(c.top_node, "y")

    verify_refs(c.syms["NO_REFS"].nodes[0], "y")

    verify_refs(c.syms["JUST_DEPENDS_ON_REFS"].nodes[0], "A", "B")

    verify_refs(
        c.syms["LOTS_OF_REFS"].nodes[0],
        *(chr(n) for n in range(ord("A"), ord("Z") + 1)),
    )

    verify_refs(
        c.syms["INT_REFS"].nodes[0], "A", "B", "C", "D", "E", "F", "G", "H", "y"
    )

    verify_refs(c.syms["CHOICE_REF"].nodes[0], "CHOICE")

    verify_refs(c.menus[0], "A", "B", "C", "D")

    verify_refs(c.comments[0], "A", "B")

    verify_refs(c.syms["MULTI_DEF_SYM"], "A", "B", "C", "y")
    verify_refs(c.named_choices["MULTI_DEF_CHOICE"], "A", "B", "C")


# -- 'if' node removal -------------------------------------------------------


def test_if_removal():
    c = Kconfig("tests/Kifremoval", warn=False)

    nodes = tuple(c.node_iter())

    expected_names = ["A", "B", "C", "D"]
    for i, name in enumerate(expected_names):
        assert nodes[i].item.name == name

    expected_prompts = ["E", "F", "G"]
    for i, prompt in enumerate(expected_prompts):
        assert nodes[4 + i].prompt[0] == prompt

    expected_tail = ["H", "I", "J"]
    for i, name in enumerate(expected_tail):
        assert nodes[7 + i].item.name == name

    assert len(nodes) == 10, "Wrong number of nodes after 'if' removal"


# -- Multi-def property copying -----------------------------------------------


def test_multidef_property_copying():
    c = Kconfig("tests/Kdepcopy", warn=False)

    def verify_props(desc, props, prop_names):
        actual = [prop[0].name for prop in props]
        expected = prop_names.split()
        assert actual == expected, f"{desc} properties"

    verify_props(
        "default", c.syms["MULTIDEF"].defaults, "A B C D E F G H I J K L M N O P Q R"
    )

    verify_props("select", c.syms["MULTIDEF"].selects, "AA BB CC DD EE FF GG HH II JJ")

    verify_props("imply", c.syms["MULTIDEF"].implies, "AA BB CC DD EE FF GG HH II JJ")

    verify_props("select", c.syms["MULTIDEF_CHOICE"].selects, "A B C")

    verify_props("range", c.syms["MULTIDEF_RANGE"].ranges, "A B C D E F")

    verify_props("default", c.choices[1].defaults, "A B C D E")


# -- Dependency loop detection ------------------------------------------------


def test_deploop_detection():
    for i in range(11):
        filename = "tests/Kdeploop" + str(i)
        with pytest.raises(KconfigError, match="Dependency loop"):
            Kconfig(filename)


# -- Symbol.rev_dep (select) -------------------------------------------------


def test_rev_dep():
    c = Kconfig("tests/Krevdep", warn=False)

    # Symbol with no selectors: rev_dep is the constant 'n'
    assert expr_str(c.syms["PLAIN"].rev_dep) == "n"

    # Single select: rev_dep is the selector symbol
    assert expr_str(c.syms["SINGLE_TARGET"].rev_dep) == "SEL_A"

    # Multiple selectors: rev_dep is OR of all selectors
    assert expr_str(c.syms["MULTI_TARGET"].rev_dep) == "SEL_B || SEL_C"

    # Conditional select: rev_dep is (selector AND condition)
    assert expr_str(c.syms["COND_TARGET"].rev_dep) == "COND_SEL && COND_DEP"


# -- Symbol.weak_rev_dep (imply) ---------------------------------------------


def test_weak_rev_dep():
    c = Kconfig("tests/Krevdep", warn=False)

    # Symbol with no impliers: weak_rev_dep is 'n'
    assert expr_str(c.syms["PLAIN"].weak_rev_dep) == "n"

    # Single imply
    assert expr_str(c.syms["IMP_SINGLE_TARGET"].weak_rev_dep) == "IMP_A"

    # Multiple impliers
    assert expr_str(c.syms["IMP_MULTI_TARGET"].weak_rev_dep) == "IMP_B || IMP_C"

    # Conditional imply
    assert expr_str(c.syms["IMP_COND_TARGET"].weak_rev_dep) == "IMP_COND && COND_DEP"


# -- Dependency loop detection ------------------------------------------------


def test_deploop_message():
    with pytest.raises(KconfigError) as exc_info:
        Kconfig("tests/Kdeploop10")

    assert str(exc_info.value) == """
Dependency loop
===============

A (defined at tests/Kdeploop10:1), with definition...

config A
\tbool
\tdepends on B

...depends on B (defined at tests/Kdeploop10:5), with definition...

config B
\tbool
\tdepends on C = 7

...depends on C (defined at tests/Kdeploop10:9), with definition...

config C
\tint
\trange D 8

...depends on D (defined at tests/Kdeploop10:13), with definition...

config D
\tint
\tdefault 3 if E
\tdefault 8

...depends on E (defined at tests/Kdeploop10:18), with definition...

config E
\tbool

(select-related dependencies: F && G)

...depends on G (defined at tests/Kdeploop10:25), with definition...

config G
\tbool
\tdepends on H

...depends on the choice symbol H (defined at tests/Kdeploop10:32), with definition...

config H
\tbool "H"
\tdepends on I && <choice>

...depends on the choice symbol I (defined at tests/Kdeploop10:41), with definition...

config I
\tbool "I"
\tdepends on <choice>

...depends on <choice> (defined at tests/Kdeploop10:38), with definition...

choice
\tbool "choice" if J

...depends on J (defined at tests/Kdeploop10:46), with definition...

config J
\tbool
\tdepends on A

...depends again on A (defined at tests/Kdeploop10:1)"""
