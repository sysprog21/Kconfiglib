# Kbuild Toolchain Functions

Kconfiglib implements Kbuild toolchain detection functions used by the Linux kernel since version 4.18.
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

## Implementation

### Design

Functions are implemented in `kconfiglib.py` following these principles:

- Uniform interface through the `_functions` dictionary
- No special-case handling
- Python 3.6+ using standard library only
- Graceful error handling (missing tools return `n`)

### Environment Variables

Functions respect standard build variables:
- `CC` (default: `gcc`)
- `LD` (default: `ld`)
- `RUSTC` (default: `rustc`)

### Performance

Functions execute shell commands during Kconfig parsing, which can be slow.
For applications that parse configurations repeatedly, consider implementing
caching or using `allow_empty_macros=True` to skip toolchain detection.

## Testing

Four test suites validate the implementation:

`test_issue111.py`
: Validates basic toolchain function parsing.

`test_issue109.py`
: Tests nested function calls and complex expressions.

`test_kbuild_complete.py`
: Comprehensive suite with 35+ test cases covering all functions, edge cases, and error conditions.

`test_kernel_compat.py`
: Real-world kernel Kconfig snippets from init/Kconfig, arch/x86/Kconfig, etc.

Run all tests:
```bash
python3 test_basic_parsing.py && \
python3 test_issue111.py && \
python3 test_issue109.py && \
python3 test_kbuild_complete.py && \
python3 test_kernel_compat.py
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

## See Also

- [Kconfig Language](https://docs.kernel.org/kbuild/kconfig-language.html) - Complete syntax specification
- [Kconfig Macro Language](https://docs.kernel.org/kbuild/kconfig-macro-language.html) - Preprocessor documentation
- [scripts/Kconfig.include](https://github.com/torvalds/linux/blob/master/scripts/Kconfig.include) - Upstream implementation
