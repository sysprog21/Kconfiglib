# Changelog

## Integrated from Zephyr Upstream

| Zephyr Commit | Description | This Project |
|---------------|-------------|--------------|
| `9b1ae78` | Fix file leaks (try/finally) | Implemented at lines 1140-1151, 3115-3118 |
| `0380400` | Menu visibility fix when leaving | Implemented at lines 1328-1333 (try/except) |
| `1e6f644` | Fix crash from unsupported locales | `23b7e61` |
| `407b92b` | NULL character input handling | `d546545` |
| `c3f7865` | Macro expansion empty string check | `a8c4929` |
| `82fdbda` | Modules property support | `bdfe32c` |
| `f58717e` | Symbol value origin tracking | `9938058` |
| `601f63d`, `6eae2bf` | Symbol.ranges 4-tuple unpacking | `a5b6ecd` |
| `ffb5459` | Dark mode support | `1dc26ef` (more comprehensive) |

## Features Unique to This Project

### guiconfig Enhancements
- Dark/light theme toggle with keyboard shortcut (Ctrl+T)
- Blue gear icon (replacing green X)
- Interactive search in jump-to dialog (`54aa1c9`)
- Enhanced UI experience (`b228109`)
- Select/imply origin display in menu (`b69b31e`)
- Missing `import re` fixed (ulfalizer#105, ulfalizer#136 resolved)

### menuconfig Enhancements
- Scrollbar support (`029e3d1`)
- Enhanced UI layout

### Testing
- Replaced testsuite.py with pytest: 120 tests across 10 modules under tests/.
  Added `pytest.ini`, `tests/conftest.py`, and `tests/test_*.py` modules.
  Compatibility tests (kernel C tool comparison) in `tests/test_compat.py`.
  CI runs pytest on all platforms including Windows.
- Added tests for previously-untested public APIs: `expr_value()`,
  `Symbol.config_string`, `Symbol.rev_dep`, `Symbol.weak_rev_dep`,
  `Kconfig.missing_syms`, and `Symbol.user_loc`.

### API Cleanup
- Removed deprecated `KconfigSyntaxError` alias (use `KconfigError`).
- Removed `InternalError` exception (was never raised).
- Removed 10 `enable_*/disable_*` warning methods on `Kconfig`
  (use the `warn`, `warn_to_stderr`, `warn_assign_undef`,
  `warn_assign_override`, `warn_assign_redun` attributes directly).
- Removed deprecated module-level `load_allconfig()` function
  (use `Kconfig.load_allconfig()` method).

### Core Features
- Kbuild toolchain test functions (`ced27d6`)
- Headless mode support (`27a8a0d`)
- Windows Python 3.12 compatibility (`15d3d98`)
- `transitional` keyword parsing (zephyr#25 parser support; full behavior parity tracked in TODO P1)
- `modules` keyword support (both `option modules` and bare `modules` forms)

## Version History

| Date | Action | Commits |
|------|--------|---------|
| 2025-10 | Symbol.ranges fix | `a5b6ecd` |
| 2025-10 | Kbuild toolchain support | `ced27d6` |
| 2025-10 | Dark/light theme | `1dc26ef` |
| 2025-10 | Interactive search | `54aa1c9` |
