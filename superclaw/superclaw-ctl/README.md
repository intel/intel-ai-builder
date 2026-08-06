# superclaw-ctl

CLI tool for managing SuperClaw vLLM model serving on Linux servers with Intel Arc GPUs.

## Prerequisites

- Python 3.11+ with [`uv`](https://docs.astral.sh/uv/)
- Docker >= 24.0
- Docker Compose >= 2.24
- Intel Arc GPUs with `/dev/dri` access (for vLLM)
- Model weights at `/models/` (configurable via `superclaw-ctl config set paths.models_dir <path>`)

## Install

```bash
# From the repo (development)
cd superclaw/superclaw-ctl
uv sync --extra dev

# Run directly
uv run superclaw-ctl --help
```

## Quick Start

```bash
# 1. Initialize — checks environment, detects GPUs, downloads models, generates API keys
superclaw-ctl init

# 2. Start containers (override router port with --router-port if needed)
superclaw-ctl up

# 3. Check health
superclaw-ctl status

# 4. View logs
superclaw-ctl logs -f

# 5. Stop containers
superclaw-ctl down
```

After `superclaw-ctl up` succeeds, vllm-router is available on the configured
router port (default `8080`):

```
╭──────────────────────────── Connection ─────────────────────────────╮
│ URL: http://<server-ip>:8080                                        │
│ vLLM Chat: <server-ip>:18103                                        │
│ vLLM Embed: <server-ip>:18104                                       │
│ vLLM Model Router: <server-ip>:8080                                 │
│ Token: <api-key>...                                                 │
╰─────────────────────────────────────────────────────────────────────╯
```

Use the **URL** (`/v1/chat/completions` and `/v1/embeddings`) in any OpenAI-compatible client.
If you start with a non-default port (for example `superclaw-ctl up --router-port 9090`),
use the same `--router-port` value when running `superclaw-ctl status`.

The router runs in IGW mode and registers the chat and embedding workers with
their model IDs so requests land on the right backend.

### Verify the model service with curl

```bash
# Get the token (unredacted)
TOKEN=$(uv run superclaw-ctl keys show --reveal | grep vllm_api_key | awk '{print $NF}')
ROUTER_PORT=8080

# List models via model service (proxied to :18103)
curl -s -H "Authorization: Bearer $TOKEN" \
  http://127.0.0.1:$ROUTER_PORT/v1/models | jq .

# Chat completion via model service
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen3-Coder-Next","messages":[{"role":"user","content":"Say hi in one short sentence."}]}' \
  http://127.0.0.1:$ROUTER_PORT/v1/chat/completions | jq .

# Embeddings via model service (proxied to :18104)
curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"KaLM-embedding-v2.5","input":"SuperClaw model service check"}' \
  http://127.0.0.1:$ROUTER_PORT/v1/embeddings | jq .
```

## Commands

| Command | Description |
|---|---|
| `init` | Check environment, detect GPUs, download models, generate keys, save config |
| `upgrade [--force]` | Safely refresh model directory layout and bundled compose file(s) for an existing install, without rotating `VLLM_API_KEY` |
| `up [--router-port PORT] [--timeout SECONDS]` | Start vLLM container (with vllm-router), wait for backend+router readiness |
| `down` | Stop and remove containers |
| `restart [service]` | Restart vllm |
| `status [--router-port PORT]` | Show container states, health checks, and endpoints |
| `logs [service] [-f] [--tail N]` | Show/follow container logs (default tail: 200 lines) |
| `pull` | Pull vLLM image |
| `models list` | List models in models directory with metadata |
| `models info <name>` | Show detailed model info |
| `models download [--model ...] [--verify]` | Download/repair model files or verify model integrity |
| `models migrate-layout [--model ...] [--apply]` | Preview or apply legacy-to-canonical model directory renames |
| `doctor` | Run diagnostics without changing state |
| `config show` | Show effective config (secrets redacted) |
| `config set <key> <value>` | Update a config value |
| `keys show [--reveal]` | Show stored API keys |
| `keys rotate` | Generate new API keys |
| `clean containers` | Remove containers |
| `clean images` | Remove docker images |
| `clean volumes` | Remove docker volumes |
| `clean config` | Remove config directory |
| `clean all [--dry-run]` | Remove everything |
| `version` | Show CLI, Docker, and Compose versions |

## Configuration

Config is stored at `~/.config/superclaw-ctl/`:

| File | Purpose | Permissions |
|------|---------|-------------|
| `config.toml` | Non-secret settings (mode, image refs, paths) | 0644 |
| `secrets.toml` | vLLM API key | 0600 |

### Environment Variable Overrides

| Variable | Overrides |
|---|---|
| `SUPERCLAW_VLLM_API_KEY` | secrets.vllm_api_key |
| `SUPERCLAW_MODELS_DIR` | config.paths.models_dir |
| `SUPERCLAW_ALLOW_DEMO_KEY` | When truthy (`1`/`true`/`yes`/`on`), allows known demo/weak tokens (e.g. `intel123`). Empty keys are still rejected. Intended for local testing only. |

### Proxy Support

`superclaw-ctl up` passes `HTTP_PROXY`/`HTTPS_PROXY` (or lowercase `http_proxy`/`https_proxy`) to the Docker Compose environment. Set these on the host if the vLLM container needs outbound internet access.

Model downloads during `init` also respect `HTTP_PROXY`/`HTTPS_PROXY` and `HF_ENDPOINT` (for HuggingFace mirror sites).

By default, vLLM logs are written under `~/.config/superclaw-ctl/logs/` alongside the rest of the CLI state. Override `config.paths.logs_dir` if you want them elsewhere.

`superclaw-ctl up --timeout` controls both the CLI readiness probes and the in-container
backend wait budget (`VLLM_BACKEND_READY_TIMEOUT_SECONDS`), so one value keeps startup
timeouts aligned.

## Compose File Location

`superclaw-ctl` always uses compose files from `~/.config/superclaw-ctl/compose/` (the directory written by `superclaw-ctl init`). The path can be changed via `config.paths.compose_dir` in `config.toml`.

### Compose overrides (`config.compose.extra_files`)

Use `config.compose.extra_files` to add extra Compose `-f` files (for local overrides/patches) on top of `docker-compose.vllm.yml`.

```bash
# Set as JSON because this key is a list
uv run superclaw-ctl config set compose.extra_files '["compose.override.yml","/opt/superclaw/custom.yml"]'
```

- Relative paths are resolved from `config.paths.compose_dir`.
- Absolute paths are used as-is.
- To clear overrides:

```bash
uv run superclaw-ctl config set compose.extra_files '[]'
```

> **Note:** `superclaw-ctl` targets vLLM-only serving and does not manage an application container.

## Manual Smoke Test (on Linux server)

```bash
cd superclaw/superclaw-ctl
uv sync --extra dev

uv run superclaw-ctl init
uv run superclaw-ctl doctor
uv run superclaw-ctl up
uv run superclaw-ctl status
uv run superclaw-ctl models list
uv run superclaw-ctl keys show
uv run superclaw-ctl logs --tail 5
uv run superclaw-ctl restart vllm
uv run superclaw-ctl version
uv run superclaw-ctl down
```

## Troubleshooting

### Breaking change: model directory naming

`superclaw-ctl` now uses canonical owner-scoped model directories derived from HuggingFace repo IDs:

- `owner/name` -> `owner--name`

Legacy repo-tail directories (for example `Qwen3.5-2B`) are no longer auto-detected by `doctor`, `init`, or `models download`.
Use the explicit migration command:

```bash
# Preview
superclaw-ctl models migrate-layout

# Apply renames
superclaw-ctl models migrate-layout --apply
```

You can scope migration to one model selector:

```bash
superclaw-ctl models migrate-layout --model Qwen/Qwen3.5-2B --apply
```

After migration, integrity checks/downloads should target canonical selectors and paths:

```bash
superclaw-ctl models download --model Qwen/Qwen3.5-2B --verify
```

The legacy directory name for each registry entry is read from the explicit
`legacy_local_dir_name` field in `vllm_models.json` — it is **not** guessed from
the repo id, since a model's old hand-picked `local_dir_name` may not match its
HuggingFace repo's tail (e.g. `KaLM-Embedding/KaLM-embedding-multilingual-mini-instruct-v2.5`
had legacy directory name `KaLM-embedding-v2.5`, not the repo tail).

**Future removal:** `models migrate-layout` is a transitional command for users
upgrading from the pre-owner-scoped directory layout. Once the release(s) using
the old layout are no longer supported, remove it entirely:
- `models_migrate_layout()` command in `src/superclaw_ctl/cli.py`
- the `legacy_local_dir_name` field in `VllmModelEntry` (`src/superclaw_ctl/registry.py`) and its entries in `vllm_models.json`
- the `test_models_migrate_layout_*` tests in `tests/test_cli.py`
- this "Breaking change: model directory naming" section

### Upgrading an existing install

Do **not** re-run `superclaw-ctl init` to pick up fixes on an existing install:
`init` unconditionally generates a brand-new `VLLM_API_KEY` every time it runs,
so re-running it silently rotates your API key and breaks anything still using
the old one (browser sessions, external clients, saved `.env` files).

Instead, use the dedicated upgrade command, which never generates or writes
`secrets.toml` (it may read it, read-only, solely to verify no containers are
currently running):

```bash
superclaw-ctl upgrade
superclaw-ctl up
```

`upgrade` does two things safely:

1. Migrates on-disk model directories from the legacy layout to the canonical
   owner-scoped layout (same underlying logic as `models migrate-layout --apply`).
2. Refreshes the bundled `docker-compose.vllm.yml` in `config.paths.compose_dir`
   so `vllm serve` points at the canonical model directory.

Safety behavior:
- **Refuses to run while containers are running** — run `superclaw-ctl down` first.
- **Refuses to overwrite a hand-modified compose file** unless you pass `--force`
  (a `.bak` backup of the previous file is written before any overwrite).
  Detection works by forward-migrating any recognized legacy model path in the
  on-disk file's `vllm serve` command and checking whether the result is then
  byte-identical to the currently-bundled template — if so, the only
  difference was a known/tracked legacy path and it's provably safe to
  auto-replace. Any other difference (an unrelated hand-edit, or a template
  change we have no registry-tracked knowledge of) requires `--force`.
- **Aborts with no changes made** if model directories are ambiguous/in conflict
  (same rule as `models migrate-layout`).
- If the compose refresh fails after directories were renamed, the renames are
  rolled back — `upgrade` never leaves a partially-upgraded install.
- Running `upgrade` again once everything is current is a no-op.

**Out of scope:** `upgrade` only manages `superclaw-ctl`'s own `compose_dir`
base template and (read-only, for warning purposes) any files listed in
`config.compose.extra_files`. It does **not** touch:
- Entries in `config.compose.extra_files` that reference a legacy model
  directory — these must be edited by hand.

`superclaw-ctl up` also prints a non-fatal warning before starting containers
if it detects a compose file still referencing a legacy model directory, or an
expected canonical model directory that doesn't exist on disk — either state
means vLLM is likely to fail to start.

Do **not** remove `_model_matches_selector`, `_build_adhoc_model_entry`, or
`_adhoc_local_dir_name` — those are shared with `models download --model`'s
flexible selector matching and are unrelated to migration.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `up` hangs for 5+ min | vLLM model loading is slow on first start | Wait — subsequent starts use cached weights |
| 401 on model service endpoints | Missing or wrong bearer token | Use the token from `superclaw-ctl keys show --reveal` |
| `status` shows router unhealthy | vLLM container still starting or router failed to initialize | Wait a moment and retry; check `superclaw-ctl logs` |
| `status` shows router unhealthy after custom port start | `up` used `--router-port`, but `status` defaulted to 8080 | Run `superclaw-ctl status --router-port <same-port>` |
| PII detector download fails | No outbound internet / proxy not set | Set `HTTP_PROXY`/`HTTPS_PROXY` on host before `up` |
