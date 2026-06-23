# tools/superclaw-ctl/packaging

Owns the build tooling for distributing `superclaw-ctl` as a single self-contained
binary.

## Ownership

| Area | Owner |
|------|-------|
| PyInstaller spec | platform/release team |
| Build script | platform/release team |

**Allowed dependencies:** `pyinstaller` (build-only, via `[build]` optional-dep group).
Not allowed to add runtime deps here.

## Layout

```
packaging/
  pyinstaller/
    entry.py               # PyInstaller entry shim (calls superclaw_ctl.cli.app)
    superclaw-ctl.spec     # PyInstaller spec (onefile, strip, hidden imports, data files)
  build.sh                 # Build script for the Linux server
  README.md                # This file
```

## Build

PyInstaller **cannot cross-compile** — the binary must be built natively on Linux.

```bash
cd <path-to>/superclaw/superclaw-ctl
chmod +x packaging/build.sh
./packaging/build.sh

# Output: dist/superclaw-ctl
```

### Prerequisites on the build host

| Tool | Minimum | Install |
|------|---------|---------|
| Python | 3.11 | system / pyenv |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| binutils (`strip`) | any | `sudo apt install binutils` |

## Smoke test (run on the server after build)

```bash
BINARY=dist/superclaw-ctl

# Basic interface
$BINARY --help
$BINARY version
$BINARY models list
$BINARY config show
```

All commands should complete without `ModuleNotFoundError`.

## glibc compatibility

The binary is tied to the glibc of the build machine. Target machines must run
**the same or a newer glibc version** (distro).

Current build baseline: **glibc 2.39** (Ubuntu 24.04).

Check with:

```bash
ldd --version            # on the build machine
ldd dist/superclaw-ctl   # shows minimum glibc requirement
```
