import os

import setuptools

# Make sure that README.md decodes in environments that use the C locale
# (which implies ASCII), by explicitly giving the encoding.
with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()


setuptools.setup(
    name="kconfiglib",
    # MAJOR.MINOR.PATCH, per http://semver.org
    version="14.1.1a4",
    description="A flexible Python Kconfig implementation",
    long_description=long_description,
    url="https://github.com/sysprog21/Kconfiglib",
    author="Zephyr Project",
    author_email="ci@zephyrproject.org",
    keywords="kconfig, kbuild, menuconfig, configuration-management",
    license="ISC",
    py_modules=(
        "kconfiglib",
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
    ),
    entry_points={
        "console_scripts": (
            "menuconfig = menuconfig:_main",
            "guiconfig = guiconfig:_main",
            "genconfig = genconfig:main",
            "oldconfig = oldconfig:_main",
            "olddefconfig = olddefconfig:main",
            "savedefconfig = savedefconfig:main",
            "defconfig = defconfig:main",
            "alldefconfig = alldefconfig:main",
            "allnoconfig = allnoconfig:main",
            "allmodconfig = allmodconfig:main",
            "allyesconfig = allyesconfig:main",
            "listnewconfig = listnewconfig:main",
            "setconfig = setconfig:main",
        )
    },
    # Note: windows-curses is not automatically installed on Windows anymore,
    # because it made Kconfiglib impossible to install on MSYS2 with pip
    python_requires=">=3.6",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
