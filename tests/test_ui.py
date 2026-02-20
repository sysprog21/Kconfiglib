# Copyright (c) 2011-2019 Ulf Magnusson
# SPDX-License-Identifier: ISC
#
# UI search logic tests: verify that the jump-to search in menuconfig and
# guiconfig correctly strips the config prefix and matches symbol names.

import re

import pytest

from kconfiglib import Kconfig


def _strip_prefix(search_text, config_prefix="CONFIG_"):
    """Replicate the prefix stripping logic used by both UIs.

    The 'config_prefix' parameter mirrors Kconfig.config_prefix (default
    "CONFIG_"), allowing tests to exercise custom prefixes like "BR2_".
    """
    prefix = config_prefix.lower()
    prefix_len = len(prefix)
    return [
        re.compile(token[prefix_len:] if token.startswith(prefix) else token).search
        for token in search_text.lower().split()
    ]


def _matches_symbol(regex_searches, sym_name):
    """Return True if all regexes match the symbol name (same logic as UIs)."""
    name_lower = sym_name.lower()
    return all(search(name_lower) for search in regex_searches)


def test_config_prefix_stripped():
    """Searching for CONFIG_FOO should match a symbol named FOO."""
    searches = _strip_prefix("CONFIG_MODULES")
    assert _matches_symbol(searches, "MODULES")


def test_config_prefix_case_insensitive():
    """The prefix strip is case-insensitive since the whole string is lowered."""
    for prefix in ("CONFIG_", "config_", "Config_", "cOnFiG_"):
        searches = _strip_prefix(prefix + "FOO")
        assert _matches_symbol(searches, "FOO"), f"failed for prefix {prefix!r}"


def test_no_prefix_still_works():
    """Searching without CONFIG_ prefix still works normally."""
    searches = _strip_prefix("MODULES")
    assert _matches_symbol(searches, "MODULES")


def test_config_prefix_only_at_start():
    """CONFIG_ embedded in the middle of a token should not be stripped."""
    searches = _strip_prefix("MY_CONFIG_FOO")
    assert not _matches_symbol(searches, "FOO")
    assert _matches_symbol(searches, "MY_CONFIG_FOO")


def test_config_prefix_multiple_tokens():
    """Multiple search tokens each get their prefix stripped independently."""
    searches = _strip_prefix("CONFIG_NET CONFIG_IPV6")
    # Should match only if both "net" and "ipv6" match
    assert not _matches_symbol(searches, "NET")
    assert not _matches_symbol(searches, "IPV6")
    # A name containing both substrings would match
    assert _matches_symbol(searches, "NET_IPV6")


def test_config_prefix_with_regex():
    """Regex patterns after CONFIG_ prefix are preserved."""
    searches = _strip_prefix("CONFIG_DEBUG.*")
    assert _matches_symbol(searches, "DEBUG_INFO")
    assert _matches_symbol(searches, "DEBUG")
    # re.search matches anywhere, so "debug.*" finds "debug" inside "NODEBUG"
    assert _matches_symbol(searches, "NODEBUG")
    assert not _matches_symbol(searches, "RELEASE")


def test_config_prefix_with_real_kconfig():
    """End-to-end: search with CONFIG_ prefix against a real Kconfig parse."""
    c = Kconfig("tests/Kmisc")
    sym_names = [s for s in c.syms if not s.startswith("UNAME_RELEASE")]
    assert len(sym_names) > 0, "Kmisc should define symbols"

    target = sym_names[0]
    searches = _strip_prefix("CONFIG_" + target)
    assert _matches_symbol(
        searches, target
    ), f"CONFIG_{target} should match symbol {target}"


def test_bare_config_search():
    """Searching for just 'CONFIG_' (with nothing after) becomes empty regex,
    which matches everything -- same as searching for empty string."""
    searches = _strip_prefix("CONFIG_")
    # Empty regex matches any string
    assert _matches_symbol(searches, "ANYTHING")


def test_config_prefix_bad_regex():
    """Stripping CONFIG_ can expose an invalid regex (e.g. CONFIG_[ becomes [).
    Both UIs catch re.error and show 'Bad regular expression'. Verify that the
    stripping itself doesn't suppress the error."""
    with pytest.raises(re.error):
        _strip_prefix("CONFIG_[")


def test_custom_prefix():
    """Projects can set a custom config prefix (e.g. BR2_ for Buildroot).
    The stripping logic should use the actual prefix, not hardcoded CONFIG_."""
    # With BR2_ prefix, "BR2_PACKAGE" should match symbol "PACKAGE"
    searches = _strip_prefix("BR2_PACKAGE", config_prefix="BR2_")
    assert _matches_symbol(searches, "PACKAGE")
    # re.search finds "package" inside "br2_package" too (substring match)
    assert _matches_symbol(searches, "BR2_PACKAGE")

    # CONFIG_ should NOT be stripped when the prefix is BR2_
    searches = _strip_prefix("CONFIG_FOO", config_prefix="BR2_")
    assert not _matches_symbol(searches, "FOO")
    assert _matches_symbol(searches, "CONFIG_FOO")

    # Empty prefix means nothing is stripped
    searches = _strip_prefix("CONFIG_BAR", config_prefix="")
    assert _matches_symbol(searches, "CONFIG_BAR")
