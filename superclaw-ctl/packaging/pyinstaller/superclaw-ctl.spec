# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for superclaw-ctl — single onefile Linux x86_64 binary.
#
# Build (on the Linux server):
#   cd tools/superclaw-ctl
#   uv sync --extra build
#   uv run pyinstaller packaging/pyinstaller/superclaw-ctl.spec
#
# Output: dist/superclaw-ctl

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Locate the package so we can reference bundled data files
# ---------------------------------------------------------------------------
HERE = Path(SPECPATH)  # directory of this spec file
SRC = HERE.parent.parent / "src"  # tools/superclaw-ctl/src

a = Analysis(
    [str(HERE / "entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        # vllm_models.json — loaded via importlib.resources in registry.py
        (str(SRC / "superclaw_ctl" / "vllm_models.json"), "superclaw_ctl"),
        # compose templates — loaded via importlib.resources in cli.py _extract_templates
        (str(SRC / "superclaw_ctl" / "templates"), "superclaw_ctl/templates"),
    ],
    hiddenimports=[
        # httpx default transport (used by health probes)
        "httpx._transports.default",
        # huggingface_hub: file download & auth sub-modules loaded at runtime
        "huggingface_hub.file_download",
        "huggingface_hub.hf_api",
        # pydantic v2 core — often missed
        "pydantic.deprecated.class_validators",
        "pydantic_core",
    ],
    collect_submodules=[
        "huggingface_hub",
    ],
    collect_data=[],
    excludes=[
        # GUI / display toolkits never used
        "tkinter",
        "_tkinter",
        "turtle",
        "turtledemo",
        # Test frameworks — not needed at runtime
        "pytest",
        "unittest",
        # Heavy stdlib modules not used by this CLI
        "xmlrpc",
        "xml.etree",
        "lib2to3",
        "pydoc",
        "doctest",
        # Unused IPython / notebook ecosystem (may be pulled in by hf-hub)
        "IPython",
        "ipykernel",
        "jupyter",
        "notebook",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        # Unused crypto libs (not in our dep tree, but may appear via transitive)
        "Crypto",
        "cryptography",
        "OpenSSL",
    ],
    noarchive=False,
    optimize=0,  # must NOT strip docstrings — Typer uses __doc__ for command help text
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="superclaw-ctl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,       # strip debug symbols from the native binary
    upx=False,        # no UPX compression (avoids AV false positives)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
