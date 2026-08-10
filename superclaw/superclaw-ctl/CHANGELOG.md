# Changelog

All notable changes to `superclaw-ctl` are documented here.

## [1.2.0] - 2026-08-10

### Added

- Added `superclaw-ctl upgrade [--force]` as the safe upgrade path for existing
  installations.
- Added `superclaw-ctl models migrate-layout` with dry-run and `--apply` modes
  for migrating legacy model directories.
- Added flexible model selectors for model download and verification, including
  model IDs, names, repository IDs, and local directory names.
- Added compose-template staleness warnings and safe refresh/rollback handling
  during upgrades.
- Added validation for model-directory paths before initialization.

### Fixed

- Improved GPU detection fallback when `xpu-smi` is unavailable

### Changed

- Model directories now use owner-scoped names derived from Hugging Face
  repository IDs, such as `Qwen--Qwen3-Coder-Next`.
- The upgrade flow refreshes the bundled compose template without rotating the
  existing vLLM API key or rewriting `secrets.toml`.
- Model downloads support configured proxy settings and Hugging Face mirror
  fallback.
- Weak or commonly used API-key values are rejected by default. The
  `SUPERCLAW_ALLOW_DEMO_KEY` escape hatch is available for local testing only.

### Packaging

- Updated the package metadata and native-Linux PyInstaller build instructions
  for the 1.2.0 release.

For upgrade procedures and compatibility notes, see
[MIGRATION.md](MIGRATION.md).
