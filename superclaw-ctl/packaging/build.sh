#!/usr/bin/env bash
# build.sh — Build the superclaw-ctl single-file Linux binary with PyInstaller.
#
# Prerequisites on the build host:
#   - Python 3.11+
#   - uv  (https://docs.astral.sh/uv/)
#   - binutils (for --strip; usually pre-installed: `sudo apt install binutils`)
#
# The produced binary is tied to the glibc of this build machine.
# Target machines must run the same or a newer glibc version (distro).

set -euo pipefail

# Ensure ~/.local/bin is on PATH (uv install default location)
export PATH="${HOME}/.local/bin:${PATH}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"   # tools/superclaw-ctl/
SPEC="${SCRIPT_DIR}/pyinstaller/superclaw-ctl.spec"
DIST_DIR="${TOOL_DIR}/dist"

# ── Guards ──────────────────────────────────────────────────────────────────
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "ERROR: This build script must run on Linux (PyInstaller cannot cross-compile)." >&2
  echo "       Please run this build script on a Linux machine." >&2
  exit 1
fi

if ! command -v uv &>/dev/null; then
  echo "ERROR: 'uv' not found. Install it from https://docs.astral.sh/uv/" >&2
  exit 1
fi

if ! command -v strip &>/dev/null; then
  echo "WARNING: 'strip' (binutils) not found — binary will not be stripped." >&2
  echo "         Install with: sudo apt install binutils" >&2
fi

# ── Install deps (runtime + build group) ────────────────────────────────────
echo "==> Syncing dependencies (runtime + build)..."
cd "${TOOL_DIR}"
uv sync --extra build

# ── Run PyInstaller ──────────────────────────────────────────────────────────
echo "==> Running PyInstaller..."
uv run pyinstaller "${SPEC}" \
  --distpath "${DIST_DIR}" \
  --workpath "${TOOL_DIR}/build/.pyinstaller-work" \
  --noconfirm

BINARY="${DIST_DIR}/superclaw-ctl"

if [[ ! -f "${BINARY}" ]]; then
  echo "ERROR: Build failed — ${BINARY} not found." >&2
  exit 1
fi

# ── Report ───────────────────────────────────────────────────────────────────
SIZE=$(du -sh "${BINARY}" | cut -f1)
echo ""
echo "==> Build complete!"
echo "    Binary : ${BINARY}"
echo "    Size   : ${SIZE}"
echo ""
echo "Quick smoke test:"
echo "    ${BINARY} --help"
echo "    ${BINARY} version"
