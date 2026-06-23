"""PyInstaller entry point for superclaw-ctl.

Mirrors src/superclaw_ctl/__main__.py but lives outside the package
so PyInstaller can use it as the top-level script without packaging
the module twice.
"""

from superclaw_ctl.cli import app

if __name__ == "__main__":
    app()
