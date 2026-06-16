# superclaw-ctl

CLI tool for managing SuperClaw vLLM model serving on Linux servers with Intel Arc GPUs.

## Prerequisites

- Python 3.11+ with [`uv`](https://docs.astral.sh/uv/)
- Docker >= 24.0
- Docker Compose >= 2.24
- Intel Arc GPUs with `/dev/dri` access (for vLLM)
- Model weights at `~/.models/` (configurable via `superclaw-ctl config set paths.models_dir <path>`)

## Install

```bash
# From the repo (development)
cd tools/superclaw-ctl
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
│ URL: http://10.107.234.27:8080                                      │
│ vLLM Chat: 10.107.234.27:18103                                      │
│ vLLM Embed: 10.107.234.27:18104                                     │
│ vLLM Model Router: 10.107.234.27:8080                               │
│ Token: eJUs...                                                      │
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
| `up [--router-port PORT] [--timeout SECONDS]` | Start vLLM container (with vllm-router), wait for backend+router readiness |
| `down` | Stop and remove containers |
| `restart [service]` | Restart vllm |
| `status [--router-port PORT]` | Show container states, health checks, and endpoints |
| `logs [service] [-f] [--tail N]` | Show/follow container logs (default tail: 200 lines) |
| `pull` | Pull vLLM image |
| `models list` | List models in models directory with metadata |
| `models info <name>` | Show detailed model info |
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

## Testing

```bash
# Unit tests (works on Windows/macOS, no Docker needed)
cd tools/superclaw-ctl
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=superclaw_ctl --cov-report=term-missing
```

## Manual Smoke Test (on Linux server)

```bash
cd tools/superclaw-ctl
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

| Symptom | Cause | Fix |
|---------|-------|-----|
| `up` hangs for 5+ min | vLLM model loading is slow on first start | Wait — subsequent starts use cached weights |
| 401 on model service endpoints | Missing or wrong bearer token | Use the token from `superclaw-ctl keys show --reveal` |
| `status` shows router unhealthy | vLLM container still starting or router failed to initialize | Wait a moment and retry; check `superclaw-ctl logs` |
