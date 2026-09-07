"""Tests for the toolchain probe cache (see KCONFIG_SHELL_CACHE)."""

import json
import os
import sys

import pytest

import kconfiglib
from kconfiglib import Kconfig, KconfigError

KCONFIG = """\
mainmenu "probe cache"

config NOISY
	def_bool $(shell,echo noise >&2; echo y)

config OUT
	string
	default "$(shell,echo hello world)"

config OK
	def_bool $(success,true)

config NOT_OK
	def_bool $(success,false)
"""


# What _load() returns for KCONFIG above
EXPECTED = ["y", "hello world", "y", "n"]


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A Kconfig tree in a scratch directory, with the cache file enabled."""
    (tmp_path / "Kconfig").write_text(KCONFIG)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")
    return tmp_path


def _load():
    c = Kconfig("Kconfig", warn_to_stderr=False)
    return (
        [
            c.syms["NOISY"].str_value,
            c.syms["OUT"].str_value,
            c.syms["OK"].str_value,
            c.syms["NOT_OK"].str_value,
        ],
        c.warnings,
    )


def test_warm_load_matches_cold_load(tree):
    cold_values, cold_warnings = _load()
    assert (tree / "probe-cache.json").exists()

    warm_values, warm_warnings = _load()

    # A run served from the cache has to be indistinguishable from the run that
    # filled it, warnings and their locations included
    assert warm_values == cold_values
    assert warm_warnings == cold_warnings
    assert any("wrote to stderr: noise" in w for w in cold_warnings)


def test_changed_environment_discards_the_cache(tree, monkeypatch):
    _load()
    stale = (tree / "probe-cache.json").read_text()

    secret = "changed-secret-value"
    monkeypatch.setenv("ARBITRARY_PROBE_INPUT", secret)
    _load()

    assert (tree / "probe-cache.json").read_text() != stale
    assert secret not in (tree / "probe-cache.json").read_text()


def test_invocation_variables_do_not_discard_the_cache(tree, monkeypatch):
    """make's own plumbing describes the invocation, not the toolchain.

    Without this, `make menuconfig` and a recursive `make` key differently and
    evict each other, which is the workflow the cache exists for.
    """
    _load()
    stale = (tree / "probe-cache.json").read_text()

    monkeypatch.setenv("MAKELEVEL", "2")
    monkeypatch.setenv("MAKEFLAGS", "s --jobserver-fds=3,4 -j")
    monkeypatch.setenv("MFLAGS", "-s")
    monkeypatch.setenv("COLUMNS", "132")
    _load()

    # Nothing re-probed, so nothing was rewritten
    assert (tree / "probe-cache.json").read_text() == stale


def test_unreadable_cache_is_ignored(tree):
    (tree / "probe-cache.json").write_text("not json at all")
    values, _ = _load()
    assert values == EXPECTED


def test_cache_off_by_default(tree, monkeypatch):
    monkeypatch.delenv("KCONFIG_SHELL_CACHE")
    _load()
    assert not (tree / "probe-cache.json").exists()


def test_cache_off_does_not_read_deleted_working_directory(tmp_path, monkeypatch):
    kconfig = tmp_path / "Kconfig"
    kconfig.write_text('mainmenu "absolute path"\n')
    deleted_cwd = tmp_path / "deleted-cwd"
    deleted_cwd.mkdir()
    monkeypatch.setenv("srctree", str(tmp_path))

    # monkeypatch.chdir records the old cwd and restores it at teardown, which
    # keeps working after the directory it moved into is removed
    monkeypatch.chdir(deleted_cwd)
    os.rmdir(deleted_cwd)
    Kconfig(str(kconfig), warn_to_stderr=False)


def test_relative_cache_path_survives_in_parse_chdir(tmp_path, monkeypatch):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (tmp_path / "Kconfig").write_text(
        f'OUT := $(shell,echo y)\nCHANGE_DIR := $(python,os.chdir("{subdir}"))\n'
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")

    Kconfig("Kconfig", warn_to_stderr=False)

    assert (tmp_path / "probe-cache.json").exists()
    assert not (subdir / "probe-cache.json").exists()


def _counting_tree(tmp_path, monkeypatch):
    # Two identical $(shell,...) calls, each appending to a file we can count
    counter = tmp_path / "runs"
    (tmp_path / "Kconfig").write_text(
        'mainmenu "memo"\n\n'
        "config A\n"
        f'\tdef_bool $(shell,echo x >> "{counter}"; echo y)\n\n'
        "config B\n"
        f'\tdef_bool $(shell,echo x >> "{counter}"; echo y)\n'
    )
    monkeypatch.chdir(tmp_path)
    return counter


def test_shell_is_not_memoized_by_default(tmp_path, monkeypatch):
    """$(shell,...) runs arbitrary commands, so it must run every time."""
    counter = _counting_tree(tmp_path, monkeypatch)

    Kconfig("Kconfig", warn_to_stderr=False)

    assert counter.read_text() == "x\nx\n"


def test_shell_is_memoized_when_the_cache_is_on(tmp_path, monkeypatch):
    counter = _counting_tree(tmp_path, monkeypatch)
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")

    Kconfig("Kconfig", warn_to_stderr=False)

    # Same command twice in the Kconfig, one fork
    assert counter.read_text() == "x\n"


def test_pure_probes_are_always_memoized(tmp_path, monkeypatch):
    """$(cc-option,...) and friends are pure, and need no opt-in."""
    (tmp_path / "Kconfig").write_text(
        'mainmenu "pure"\n\nconfig A\n\tdef_bool $(cc-option,-fno-such-flag-at-all)\n'
    )
    monkeypatch.chdir(tmp_path)

    c = Kconfig("Kconfig", warn_to_stderr=False)

    key = c._probe_cache.key(("cc-option", "-fno-such-flag-at-all"))
    assert c._probe_cache.get(key) == ("n", "")


def test_probe_cache_tracks_in_parse_environment_changes(tmp_path, monkeypatch):
    (tmp_path / "Kconfig").write_text(
        "config A\n"
        "\tdef_bool $(cc-option,-flag)\n"
        'CHANGE_CC := $(python,os.environ["CC"]="bad")\n'
        "config B\n"
        "\tdef_bool $(cc-option,-flag)\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CC", "good")
    monkeypatch.setattr(
        kconfiglib, "_run_argv", lambda argv, stdin_data=None: argv[0] == "good"
    )

    c = Kconfig("Kconfig", warn_to_stderr=False)

    assert c.syms["A"].str_value == "y"
    assert c.syms["B"].str_value == "n"


def test_save_leaves_no_temporary_files(tree):
    """save() writes elsewhere and renames into place. Nothing else survives."""
    _load()
    assert sorted(os.listdir(tree)) == ["Kconfig", "probe-cache.json"]


def test_damaged_entries_are_dropped_not_trusted(tree):
    """A mangled cache costs a re-probe, never a crash or a wrong answer."""
    _load()
    path = tree / "probe-cache.json"
    cached = json.loads(path.read_text())
    good = dict(cached["results"])
    keys = list(good)
    cached["results"] = {
        **good,
        keys[0]: 42,  # not a pair
        keys[1]: ["only one"],
        keys[2]: ["y", "", "extra"],
    }
    path.write_text(json.dumps(cached))

    values, _ = _load()
    assert values == EXPECTED


def test_old_cache_format_is_discarded(tree):
    _load()
    path = tree / "probe-cache.json"
    cached = json.loads(path.read_text())
    cached["version"] = -1
    path.write_text(json.dumps(cached))

    values, _ = _load()
    assert values == EXPECTED


# --- the context contract ----------------------------------------------------
#
# Probe results are only valid for the environment and working directory they
# were measured in, and $(python,...) can move both mid-parse. Each test below
# corresponds to a way that was found to break; all three produce a silently
# wrong configuration rather than an error, so none of them announce
# themselves.


def _cc_probe_tree(tmp_path, monkeypatch, body):
    """A tree whose probes answer 'y' only while CC is 'good'."""
    (tmp_path / "Kconfig").write_text(body)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CC", "good")
    monkeypatch.setattr(
        kconfiglib, "_run_argv", lambda argv, stdin_data=None: argv[0] == "good"
    )


def test_probe_after_the_parse_sees_a_new_environment(tmp_path, monkeypatch):
    """eval_string() runs after arbitrary host code we never saw."""
    _cc_probe_tree(tmp_path, monkeypatch, "PROBE = $(cc-option,-flag)\n")
    c = Kconfig("Kconfig", warn_to_stderr=False)

    assert c.eval_string("$(cc-option,-flag)") == 2  # y

    os.environ["CC"] = "bad"
    assert c.eval_string("$(cc-option,-flag)") == 0  # n


def test_variable_expansion_after_the_parse_sees_a_new_environment(
    tmp_path, monkeypatch
):
    """Variable.expanded_value is the other public way back into _fn_val()."""
    _cc_probe_tree(tmp_path, monkeypatch, "PROBE = $(cc-option,-flag)\n")
    c = Kconfig("Kconfig", warn_to_stderr=False)

    assert c.variables["PROBE"].expanded_value == "y"

    os.environ["CC"] = "bad"
    assert c.variables["PROBE"].expanded_value == "n"


@pytest.mark.parametrize("entry", ["eval", "variable"])
def test_probe_after_parse_is_persisted(tmp_path, monkeypatch, entry):
    _cc_probe_tree(tmp_path, monkeypatch, "PROBE = $(cc-option,-flag)\n")
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")
    c = Kconfig("Kconfig", warn_to_stderr=False)

    if entry == "eval":
        assert c.eval_string("$(cc-option,-flag)") == 2
    else:
        assert c.variables["PROBE"].expanded_value == "y"

    assert (
        "cc-option\0-flag"
        in json.loads((tmp_path / "probe-cache.json").read_text())["results"]
    )
    assert not c._probe_cache._dirty


def test_eval_string_persists_probe_before_parse_error(tmp_path, monkeypatch):
    _cc_probe_tree(tmp_path, monkeypatch, "")
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")
    c = Kconfig("Kconfig", warn_to_stderr=False)

    with pytest.raises(KconfigError):
        c.eval_string("$(cc-option,-flag) && $(unterminated")

    assert (
        "cc-option\0-flag"
        in json.loads((tmp_path / "probe-cache.json").read_text())["results"]
    )


def test_probe_nested_inside_a_user_function_sees_the_new_environment(
    tmp_path, monkeypatch
):
    """A KCONFIG_FUNCTIONS function can move the environment and then expand.

    The change happens before the function returns, so anything that waits
    until afterwards to notice serves the nested probe a stale result.
    """
    (tmp_path / "probe_cache_fns.py").write_text(
        "import os\n\n"
        "def change_and_probe(kconf, _):\n"
        '    os.environ["CC"] = "bad"\n'
        '    return kconf.variables["PROBE"].expanded_value\n\n'
        'functions = {"change-and-probe": (change_and_probe, 0, 0)}\n'
    )
    _cc_probe_tree(
        tmp_path,
        monkeypatch,
        "PROBE = $(cc-option,-flag)\nA := $(PROBE)\nB := $(change-and-probe)\n",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("KCONFIG_FUNCTIONS", "probe_cache_fns")
    monkeypatch.delitem(sys.modules, "probe_cache_fns", raising=False)

    c = Kconfig("Kconfig", warn_to_stderr=False)

    assert c.variables["A"].value == "y"
    assert c.variables["B"].value == "n"


def test_persisted_entries_belong_to_the_files_context(tmp_path, monkeypatch):
    """The file is stamped with one context, so only that context's results go in.

    Without this, a probe measured after an in-parse environment change is
    written under the pre-change stamp and served to the next warm run.
    """
    _cc_probe_tree(
        tmp_path,
        monkeypatch,
        "A := $(cc-option,-flag)\n"
        'CHANGE := $(python,os.environ["CC"]="bad")\n'
        "B := $(cc-option,-other)\n",
    )
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")

    cold = Kconfig("Kconfig", warn_to_stderr=False)
    assert (cold.variables["A"].value, cold.variables["B"].value) == ("y", "n")

    # A second process would start in the original context, not in the one the
    # first run's $(python,...) left behind
    os.environ["CC"] = "good"

    # It must reach the same answers, rather than reusing anything measured
    # after the change
    warm = Kconfig("Kconfig", warn_to_stderr=False)
    assert (warm.variables["A"].value, warm.variables["B"].value) == ("y", "n")

    stored = json.loads((tmp_path / "probe-cache.json").read_text())["results"]
    assert "cc-option\0-other" not in stored, "post-change result was persisted"


@pytest.mark.parametrize("entry", ["eval", "variable"])
def test_probe_after_the_parse_sees_a_new_working_directory(
    tmp_path, monkeypatch, entry
):
    """The cwd half of the context contract.

    The environment is compared on every lookup, but the working directory
    costs a syscall, so it is only re-read when something may have moved it.
    Between the parse and a later call, host code we never saw has run, which
    is what context_may_have_changed() at those two entry points declares.
    Without them the environment tests still pass and this one does not.
    """
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "Kconfig").write_text("PROBE = $(shell,pwd)\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")

    c = Kconfig("Kconfig", warn_to_stderr=False)

    def probe():
        if entry == "variable":
            return c.variables["PROBE"].expanded_value
        return "y" if c.eval_string(f'"$(shell,pwd)" = "{os.getcwd()}"') == 2 else "n"

    before = probe()
    os.chdir(sub)
    after = probe()

    if entry == "variable":
        assert before != after
        assert after.endswith("sub")
    else:
        # The probe is compared against the live cwd, so a stale cached result
        # from the old directory no longer matches
        assert (before, after) == ("y", "y")


def test_context_is_snapshotted_after_the_functions_module_is_imported(
    tmp_path, monkeypatch
):
    """Importing KCONFIG_FUNCTIONS runs arbitrary top-level Python.

    It can chdir or write to os.environ, so the cache has to snapshot the
    context its probes will actually run in. Snapshotting before the import
    stamped the file with one context and measured probes in another, and a
    later run was then served a result from a directory it never ran in.
    """
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    for d in (a, b):
        (d / "Kconfig").write_text("OUT := $(shell,pwd)\n")
    # Triggered by a file rather than the environment, which the fingerprint
    # would otherwise notice on its own
    (tmp_path / "mover.py").write_text(
        "import os\n"
        f"if os.path.exists({str(tmp_path / 'MOVE')!r}):\n"
        f"    os.chdir({str(b)!r})\n"
        "functions = {}\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("KCONFIG_FUNCTIONS", "mover")
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", str(tmp_path / "probe-cache.json"))
    monkeypatch.chdir(a)

    def load():
        sys.modules.pop("mover", None)
        os.chdir(a)
        return Kconfig("Kconfig", warn_to_stderr=False).variables["OUT"].value

    # Measured in a, then a run whose import moves to b must not reuse it
    assert load().endswith("/a")
    (tmp_path / "MOVE").touch()
    assert load().endswith("/b")

    # And the reverse: a b-measured result must not be served to a run in a
    (tmp_path / "probe-cache.json").unlink()
    assert load().endswith("/b")
    (tmp_path / "MOVE").unlink()
    assert load().endswith("/a")


def test_import_time_environ_write_does_not_kill_persistence(tmp_path, monkeypatch):
    """A functions module setting os.environ at import is ordinary.

    With the context snapshotted before the import it looked like a mid-parse
    change, so the cache went non-pristine before the first probe and the file
    was never written -- silently, on every run.
    """
    (tmp_path / "envmod.py").write_text(
        'import os\nos.environ["MY_SDK_ROOT"] = "/opt/sdk"\nfunctions = {}\n'
    )
    (tmp_path / "Kconfig").write_text("PROBE := $(shell,echo y)\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("KCONFIG_FUNCTIONS", "envmod")
    monkeypatch.setenv("KCONFIG_SHELL_CACHE", "probe-cache.json")
    monkeypatch.chdir(tmp_path)

    sys.modules.pop("envmod", None)
    c = Kconfig("Kconfig", warn_to_stderr=False)

    assert c._probe_cache._pristine
    assert (tmp_path / "probe-cache.json").exists()
