# Kbuild Toolchain Functions

Kconfiglib implements Kbuild toolchain detection functions used by the Linux kernel since version 4.18,
plus the portable `$(python,...)` built-in for cross-platform boolean checks.
These preprocessor functions enable runtime detection of compiler, assembler, and linker capabilities,
allowing kernel configurations to adapt to different toolchain versions.

## Background

The [Kconfig preprocessor](https://docs.kernel.org/kbuild/kconfig-macro-language.html) introduced
in Linux 4.18 provides functions for toolchain capability detection. These are defined in
`scripts/Kconfig.include` and enable conditional configuration based on available toolchain features.

For comprehensive Kconfig syntax documentation, see the
[Kconfig Language](https://docs.kernel.org/kbuild/kconfig-language.html) specification.

## Implemented Functions

### Control Flow

`$(if-success,command,then-val,else-val)`
: Executes command via shell; returns `then-val` on success (exit 0), `else-val` otherwise.

`$(success,command)`
: Returns `y` if command succeeds, `n` otherwise. Equivalent to `$(if-success,command,y,n)`.

`$(failure,command)`
: Returns `n` if command succeeds, `y` otherwise. Inverse of `success`.

### Portable In-Process Checks

`$(python,code)`
: Evaluates a Python code string in-process via `exec()`. Returns `y` if
execution succeeds without exception, `n` otherwise. No subprocess, no shell,
no PATH dependency. Use `assert` for boolean checks.

The exec namespace provides pre-imported modules and a shell-free subprocess helper:

| Name       | Type     | Purpose                                    |
|------------|----------|--------------------------------------------|
| `os`       | module   | env vars, paths, file ops                  |
| `sys`      | module   | platform, version, `sys.executable` path   |
| `shutil`   | module   | `which()` for tool detection               |
| `platform` | module   | machine/system/architecture                |
| `run`      | function | shell-free subprocess, returns bool        |

`run(*argv)` executes a command as an argument list (`shell=False`) and returns
`True` if it exits with code 0, `False` otherwise.

Each `exec()` call receives a fresh copy of the namespace so assignments in one
`$(python,...)` invocation do not leak into subsequent calls.

`SystemExit` is handled specially: `SystemExit(0)` and `SystemExit(None)` map
to `y`; non-zero/non-empty codes map to `n`. `AssertionError` maps to `n`
silently (expected for boolean checks via `assert`). All other exceptions
(`NameError`, `SyntaxError`, etc.) map to `n` and emit a Kconfig warning
with the exception type and message, aiding diagnosis of typos in code strings.

Trust model: `$(python,...)` has the same trust level as `$(shell,...)`.
Kconfig files are trusted code (like Makefiles). The restricted globals provide
scope isolation (no parser internals visible), not security sandboxing.

### Compiler Detection

`$(cc-option,flag[,fallback])`
: Tests if C compiler supports a flag. Returns `y` or `n`.

`$(cc-option-bit,flag)`
: Tests if C compiler supports a flag. Returns the flag itself or empty string.
Primarily used in variable assignments.

### Assembler Detection

`$(as-instr,instruction[,extra-flags])`
: Tests if assembler supports a specific instruction. Returns `y` or `n`.

`$(as-option,flag[,fallback])`
: Tests if assembler (via CC) supports a flag. Returns `y` or `n`.

### Linker Detection

`$(ld-option,flag)`
: Tests if linker supports a flag. Returns `y` or `n`.

### Rust Support

`$(rustc-option,flag)`
: Tests if Rust compiler supports a flag. Returns `y` or `n`.

## Usage Examples

### Basic Capability Detection

```
# Compiler feature detection
config CC_HAS_ASM_GOTO
    def_bool $(success,$(CC) -Werror -x c /dev/null -S -o /dev/null)

config STACKPROTECTOR
    bool "Stack Protector buffer overflow detection"
    depends on $(cc-option,-fstack-protector)
```

### Assembler Instruction Detection

```
# x86 instruction set extensions
config AS_TPAUSE
    def_bool $(as-instr,tpause %ecx)
    help
      Requires binutils >= 2.31.1 or LLVM >= 7

config AS_AVX512
    def_bool $(as-instr,vpmovm2b %k1$(comma)%zmm5)
```

### Nested Functions

```
# Validate linker availability
ld-info := $(shell,$(LD) --version | head -n1)
$(error-if,$(success,test -z "$(ld-info)"),Linker not supported)
```

### Variable Assignments

```
# Architecture-specific flags
m32-flag := $(cc-option-bit,-m32)
m64-flag := $(cc-option-bit,-m64)

config HAS_32BIT
    def_bool "$(m32-flag)" != ""
```

### Portable Checks with $(python,...)

```
# Boolean checks (in-process, no subprocess)
config PYTHON_AVAILABLE
    def_bool $(python,)

config HAS_CC
    def_bool $(python,assert os.environ.get('CC'))

config IS_LINUX
    def_bool $(python,assert sys.platform == 'linux')

config IS_X86_64
    def_bool $(python,assert platform.machine() == 'x86_64')

config HAS_GCC
    def_bool $(python,assert shutil.which('gcc'))

# Shell-free subprocess checks
config CC_IS_CLANG
    def_bool $(python,assert run(sys.executable, 'scripts/detect-compiler.py', '--is', 'Clang'))

config HAVE_SDL2
    def_bool $(python,assert run('pkg-config', '--exists', 'sdl2'))
```

Commas inside `run(...)` are safe: the Kconfig preprocessor tracks parenthesis
depth and only splits on commas at the top level of the function call.

Quoted strings are also safe: the preprocessor tracks single (`'`), double (`"`),
triple-single (`'''`), and triple-double (`"""`) quoted regions. Commas and
parentheses inside quotes are treated as literal characters, not argument
separators or nesting markers. Backslash escapes (`\"`, `\'`) inside quoted
regions are handled correctly.

Use semicolons instead of commas for multi-statement code:
`$(python,import os; assert os.path.isfile('Makefile'))`.

For string-valued results (e.g., getting the compiler type name), `$(shell,...)`
remains the right tool. `$(python,...)` only returns `y` or `n`.

## Implementation

### Design

Functions are implemented in `kconfiglib.py` following these principles:

- Uniform interface through the `_functions` dictionary
- No special-case handling
- Python 3.6+ using standard library only
- Graceful error handling (missing tools return `n`)

### Shell-Free Toolchain Functions

Toolchain functions (`cc-option`, `ld-option`, `as-instr`, `as-option`,
`cc-option-bit`, `rustc-option`) use `subprocess.Popen` with argument lists
(`shell=False`) and `os.devnull` instead of Unix shell syntax. This
eliminates shell injection from environment variables and Kconfig-supplied
options, and makes the functions portable to Windows.

Internal helpers:

`_run_argv(argv, stdin_data=None)`
: Runs a command as an argument list. Returns `True` if exit code is 0.
Used by all toolchain functions.

`_run_cmd(command)`
: Runs a command via shell (`shell=True`). Used by `success`, `failure`,
and `if-success`, which accept user-supplied shell commands by design.

`_run_helper(*argv)`
: Shell-free subprocess for `$(python,...)` code strings. Exposed as `run()`
in the exec namespace.

### Environment Variables

Functions respect standard build variables:
- `CC` (default: `gcc`)
- `LD` (default: `ld`)
- `RUSTC` (default: `rustc`)

### Performance

Toolchain functions spawn subprocesses during Kconfig parsing, which can be
slow. `$(python,...)` checks that don't call `run()` execute in-process with
no subprocess overhead. For applications that parse configurations repeatedly,
consider implementing caching or using `allow_empty_macros=True` to skip
toolchain detection.

## Testing

Tests live in `tests/test_preprocess.py` (part of the pytest suite):

`test_kbuild_functions`
: Verifies toolchain functions (`cc-option`, `as-instr`, etc.) and
`$(python,...)` via Kconfig parsing. Exercises the full preprocessor path.

`test_success_failure_fns`
: Tests `success`, `failure`, and `if-success` directly in Python using
`sys.executable` as a portable true/false replacement.

`test_python_fn_isolation`
: Verifies that variable assignments in one `$(python,...)` call do not
leak into subsequent calls.

`test_python_fn_system_exit`
: Verifies `SystemExit` handling: `exit(0)` maps to `y`, non-zero to `n`.

Run:
```bash
python3 -m pytest tests/test_preprocess.py -v
```

## Compatibility

### Kernel Versions

Required for:
- Linux kernel 4.18+
- RHEL 8+, CentOS 8 Stream
- Recent Fedora, Ubuntu, Debian kernels
- Mainline kernel development

### Toolchains

Tested with:
- GCC 9+, Clang 10+
- binutils 2.31+
- rustc 1.60+ (optional)

## Portability

### Unix vs Windows

| Unix shell idiom | Portable replacement |
|---|---|
| `$(shell,cmd 2>/dev/null && echo y \|\| echo n)` | `$(python,assert run('cmd', 'arg'))` |
| `$(shell,test -n "$CC" && echo y \|\| echo n)` | `$(python,assert os.environ.get('CC'))` |
| `$(shell,scripts/foo.py --flag ...)` | `$(python,assert run(sys.executable, 'scripts/foo.py', '--flag'))` |
| `$(shell,pkg-config --exists lib && echo y \|\| echo n)` | `$(python,assert run('pkg-config', '--exists', 'lib'))` |
| `$(success,true)` | `$(python,)` |
| `$(failure,false)` | `$(python,assert False)` |

`$(shell,...)` remains necessary for string-valued output (e.g., compiler
type name, version strings). For boolean checks, prefer `$(python,...)`
on cross-platform projects.

### Toolchain functions

`cc-option`, `ld-option`, `as-instr`, `as-option`, `cc-option-bit`, and
`rustc-option` are portable by default. They use `subprocess.Popen` with
argument lists internally -- no shell involvement, no `/dev/null` path
dependency (`os.devnull` is used instead).

## Real-World Examples

From `arch/x86/Kconfig.cpu`:
```
config AS_TPAUSE
    def_bool $(as-instr,tpause %ecx)
    help
      Supported by binutils >= 2.31.1 and LLVM >= V7

config AS_SHA1_NI
    def_bool $(as-instr,sha1msg1 %xmm0$(comma)%xmm1)
```

From `init/Kconfig`:
```
config CC_HAS_ASM_GOTO
    def_bool $(success,$(CC) -Werror -x c /dev/null -S -o /dev/null)
```

From `arch/Kconfig`:
```
config SHADOW_CALL_STACK
    bool "Shadow Call Stack"
    depends on $(cc-option,-fsanitize=shadow-call-stack -ffixed-x18)
```

From a cross-platform project (Mado):
```
config CC_IS_CLANG
    def_bool $(python,assert run(sys.executable, 'scripts/detect-compiler.py', '--is', 'Clang'))

config HAVE_SDL2
    def_bool $(python,assert run('pkg-config', '--exists', 'sdl2'))

config CROSS_COMPILE_ENABLED
    def_bool $(python,assert os.environ.get('CROSS_COMPILE'))
```

## See Also

- [Kconfig Language](https://docs.kernel.org/kbuild/kconfig-language.html) - Complete syntax specification
- [Kconfig Macro Language](https://docs.kernel.org/kbuild/kconfig-macro-language.html) - Preprocessor documentation
- [scripts/Kconfig.include](https://github.com/torvalds/linux/blob/master/scripts/Kconfig.include) - Upstream implementation
