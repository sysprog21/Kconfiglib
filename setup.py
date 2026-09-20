import os

import setuptools
from setuptools.command.build_py import build_py

try:
    from setuptools.command.editable_wheel import editable_wheel
except ImportError:
    # PEP 660 support arrived in setuptools 64. pyproject.toml pins that floor
    # for PEP 517 builds; a legacy "python setup.py sdist/bdist_wheel" against
    # an older setuptools still works, it just cannot install editable.
    editable_wheel = None

_PACKAGE = "kconfiglib"

_MODULES = (
    _PACKAGE,
    "rawterm",
    "menuconfig",
    "guiconfig",
    "genconfig",
    "oldconfig",
    "olddefconfig",
    "savedefconfig",
    "defconfig",
    "alldefconfig",
    "allnoconfig",
    "allmodconfig",
    "allyesconfig",
    "listnewconfig",
    "setconfig",
)


class _BuildPy(build_py):
    # The sources live flat in the repository root so that "python menuconfig.py"
    # keeps working from a checkout. Map them into the package explicitly rather
    # than globbing the root, which would sweep in setup.py, lint.py and friends.
    def find_package_modules(self, package, package_dir):
        if package != _PACKAGE:
            return super().find_package_modules(package, package_dir)
        return [
            (
                package,
                "__init__" if module == _PACKAGE else module,
                os.path.join(package_dir, module + ".py"),
            )
            for module in _MODULES
        ]


_CMDCLASS = {"build_py": _BuildPy}

if editable_wheel is not None:

    class _EditableWheel(editable_wheel):
        def finalize_options(self):
            super().finalize_options()
            # Lenient and compat both bypass the source-to-package output
            # mapping above: they point the package name at the project root,
            # where kconfiglib.py is a module rather than a package, so
            # importing a submodule fails. Strict is the only mode this
            # layout can honour, so fill it in as the default and say so
            # rather than silently substituting when one of the others was
            # asked for.
            if self.mode is None:
                self.mode = "strict"
            elif self.mode.lower() != "strict":
                raise SystemExit(
                    f"editable_mode={self.mode} cannot work while the sources "
                    "live flat in the project root: it maps kconfiglib at the "
                    "root, where kconfiglib.py shadows the package. Use "
                    "editable_mode=strict."
                )

    _CMDCLASS["editable_wheel"] = _EditableWheel


# Make sure that README.md decodes in environments that use the C locale
# (which implies ASCII), by explicitly giving the encoding.
with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()


setuptools.setup(
    name="kconfiglib",
    # MAJOR.MINOR.PATCH, per http://semver.org
    version="15.0.0",
    description="A flexible Python Kconfig implementation",
    long_description=long_description,
    url="https://github.com/sysprog21/Kconfiglib",
    author="Zephyr Project",
    author_email="ci@zephyrproject.org",
    keywords="kconfig, kbuild, menuconfig, configuration-management",
    license="ISC",
    packages=(_PACKAGE,),
    package_dir={_PACKAGE: "."},
    cmdclass=_CMDCLASS,
    entry_points={
        "console_scripts": (
            "menuconfig = kconfiglib.menuconfig:_main",
            "guiconfig = kconfiglib.guiconfig:_main",
            "genconfig = kconfiglib.genconfig:main",
            "oldconfig = kconfiglib.oldconfig:_main",
            "olddefconfig = kconfiglib.olddefconfig:main",
            "savedefconfig = kconfiglib.savedefconfig:main",
            "defconfig = kconfiglib.defconfig:main",
            "alldefconfig = kconfiglib.alldefconfig:main",
            "allnoconfig = kconfiglib.allnoconfig:main",
            "allmodconfig = kconfiglib.allmodconfig:main",
            "allyesconfig = kconfiglib.allyesconfig:main",
            "listnewconfig = kconfiglib.listnewconfig:main",
            "setconfig = kconfiglib.setconfig:main",
        )
    },
    # No C extensions or third-party dependencies required.
    # menuconfig uses pure-Python terminal I/O instead of curses.
    python_requires=">=3.8",
    project_urls={
        "GitHub repository": "https://github.com/sysprog21/Kconfiglib",
        "Examples": "https://github.com/sysprog21/Kconfiglib/tree/main/examples",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Operating System Kernels :: Linux",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
