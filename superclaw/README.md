<h1 align="center">Intel® AI SuperClaw</h1>

**Hybrid agentic AI for enterprises: local by default, cloud when it counts.**

SuperClaw brings hybrid agentic AI to AI PCs, workstations, agent computers, and edge devices. Built by Intel's AI Super Builder team, it helps enterprises scale intelligent agents without losing sight of cloud cost, performance, or data security.

Agentic AI can take on complex work across tools, files, code, and business data. But when every task goes to the cloud, token costs climb and sensitive context can face added privacy and control risks.

SuperClaw takes a different route: routine and sensitive work can stay on-device or at the enterprise edge, while cloud models step in for advanced reasoning, planning, and external data retrieval.

For more details, read Intel's article, [Solving the Agentic AI Trilemma: Cost, Scale, and Data Security](https://newsroom.intel.com/opinion/solving-the-agentic-ai-trilemma-cost-scale-and-data-security).

---

<a name="toc"></a>
- [Overview](#overview)
- [What's New in v2.0](#whats-new-in-v20)
- [Releases](#releases)
- [Setup Instructions](#setup-instructions)
- [Upgrading from v1.x](#upgrading-from-v1x)
- [App Settings](#app-settings)
- [FAQ](#faq)

## Overview

### Why SuperClaw

- **Spend cloud tokens where they matter.** Handle routine and sensitive tasks locally, and reserve cloud models for work that needs them.
- **Keep sensitive data closer.** With a local model or an edge server, private data can stay on-device or within the enterprise edge, and optional File Protection masks sensitive details before files are sent to the cloud.
- **Match the model to the moment.** Each workflow step goes to the execution layer best suited to the task.
- **Put modern Intel hardware to work.** SuperClaw is designed for Intel AI PCs and workstations, including systems with Intel® Core™ Ultra processors and Intel® Arc™ Pro B-series GPUs.
- **Install it like any Windows app.** SuperClaw runs natively on Windows with built-in sandboxing: no WSL, no Docker, and no virtual machine.
- **Move beyond chat.** Specialized agents work with files, code, email, calendars, web research, and MCP-connected tools.
- **Make automation repeatable.** Scheduling and agent collaboration keep routine enterprise workflows moving consistently.

---

### Agents

SuperClaw ships with a team of purpose-built agents. Each can work independently or join a coordinated workflow.

| Agent | What it does |
|-------|--------------|
| **Default Agent** | A generalist for answering questions, reading and editing files, running tools, and coordinating specialists for larger tasks. |
| **Hybrid Coding Agent** | A coding specialist for reading, writing, editing, debugging, running scripts, and handling git operations through explore, edit, and test loops. |
| **Deep Research Agent** | Runs multi-step research by delegating focused subtasks to web-search and file specialists, then synthesizes a cited answer. |
| **Email & Calendar Agent** | Runs locally for security while listing, searching, summarizing, and prioritizing email; drafting replies; scheduling meetings; building daily plans; and tracking action items. |
| **Local File Agent** | Extracts and answers questions from documents such as PDF, CSV, Markdown, DOCX, XLSX, and PPTX, using the local model when one is available. Includes a built-in OCR tool for extracting text from images. |
| **Web Search Agent** | Returns focused, factual answers with source citations for current information from the web. |
| **File Protection (Experimental)** | An optional, off-by-default feature that detects and masks sensitive information before cloud processing. |

For example, with experimental File Protection enabled, a customer-records spreadsheet can move through a coordinated pipeline that prepares the data, attempts to detect and mask personal information, performs the analysis, and limits the context sent to the cloud.

#### Agent availability by hardware

The full specialized-agent lineup is available on the enterprise edge server and higher-memory AI PCs. More constrained systems run an enhanced Default Agent with full tools, permissions, and skills instead of the complete set of specialized agents. Any system that connects to an edge server gets the full Pro lineup.

| Tier | Hardware | Local model | Available agents |
|------|----------|-------------|------------------|
| **Pro** | Edge server (4× B70) | Qwen3.8-Flash-Next | Default, Hybrid Coding, Deep Research, Email & Calendar |
| **Pro** | Workstation — 1× B70, RAM ≥ 32 GB, ≥ 4800 MT/s | Qwen3.8-27B | Default, Hybrid Coding, Deep Research, Email & Calendar |
| **Pro** | PTL — RAM ≥ 64 GB, ≥ 6400 MT/s, iGPU B370 (10 Xe) or B390 (12 Xe) | Qwen3.6-35B-A3B (default) or Gemma 4 26B-A4B (experimental) | Default, Hybrid Coding, Deep Research, Email & Calendar |
| **Standard** | PTL — RAM ≥ 32 GB and < 64 GB, ≥ 6400 MT/s, iGPU B370 (10 Xe) or B390 (12 Xe) | Qwen3.5-4B (default) or Gemma 4 E4B (experimental) | Enhanced Default Agent with full tools, permissions, and skills |
| **Lite** | Other Intel systems with RAM ≥ 16 GB and ≥ 5600 MT/s | None | Enhanced Default Agent with a cloud model; the full Pro lineup when connected to an edge server |

> **Note:** Lite is officially supported starting with v2.0. Systems that do not meet the Lite requirements are not supported.

#### Local model details

| Model | Details |
|-------|---------|
| **Qwen3.8-Flash-Next** | Edge server model, Intel W4A16 AutoRound (INT4), served with vLLM |
| **Qwen3.8-27B** | Dense, Q4_K_M GGUF |
| **Qwen3.6-35B-A3B** | MoE, 3B active, UD-Q4_K_M GGUF |
| **Gemma 4 26B-A4B** (Experimental) | MoE, 4B active, UD-Q4_K_M GGUF; limited testing |
| **Qwen3.5-4B** | Dense with MTP head, Q4_K_M GGUF |
| **Gemma 4 E4B** (Experimental) | Q4_K_M GGUF; limited testing |

> **Note:** PTL refers to Intel Panther Lake (Core Ultra Series 3).

> **Note:** Edge servers set up for v1.3 serve Qwen3-Coder-Next-80B and remain compatible with v2.0. Switching an edge server to Qwen3.8-Flash-Next downloads about 181 GB; allow about 185 GB of free disk space.

> ⚠️ **Important:** The GPU check matches the adapter name reported by Windows, which must contain `B70`, `B370`, or `B390`. A generic name such as "Intel(R) Graphics" does not match, even on supported silicon.
>
> If the adapter name or memory requirements do not match, SuperClaw installs no local chat model and runs as Lite. To run agents, configure a cloud model under **Settings > Model Routing** or connect to an edge server.

---

### Auto Route

**Auto Route is SuperClaw's intelligent, customizable model router.** For each task, it chooses between a local model hosted on an AI PC or at the enterprise edge and a model in the cloud.

Users set the balance. Higher settings favor response quality and route more tasks to cloud models; lower settings favor cost savings and privacy by keeping more tasks local.

- **Transparent.** Users see a single assistant response while SuperClaw handles the execution strategy behind the scenes.
- **Task-aware.** Lightweight, sensitive, and repetitive work stays local; demanding reasoning and planning can be routed to cloud models.
- **User-controlled.** Users can tune Auto Route's quality tradeoff, force a local model for on-device work, or select a cloud model directly when maximum capability is required.

To enable Auto Route, configure both a local model and at least one cloud model in Settings. If only local models are available, users can select a local model and work entirely offline.

---

## What's New in v2.0

v2.0 is the biggest change to SuperClaw since v1.0. The backend no longer runs in WSL and Docker; it now runs as native Windows processes in a built-in sandbox. SuperClaw is also open source starting with v2.0: see [intel/intel-ai-builder-superclaw](https://github.com/intel/intel-ai-builder-superclaw).

### Native Windows app

- **No WSL, Docker, or virtual machine.** You no longer need to enable Intel VT-x in BIOS, install WSL, or edit `.wslconfig`.
- **Built-in sandboxing.** SuperClaw's background components each run under a separate restricted Windows account, with file access limited to the folders they need. On first launch, Windows asks for administrator approval to set this up, once per user.

> **Note:** In v2.0 the sandbox restricts which files agents can reach. It does not yet restrict network access: agents have the same internet access as your Windows account.

### Install, update, and uninstall

- **Hardware Review in the installer.** The installer checks the processor, memory, and Intel graphics driver, and links to a driver update when one is recommended. The checks are advisory and never block installation.
- **In-app updates.** Check for, download, and install updates from the version button in the sidebar. See [How do I update SuperClaw?](#how-do-i-update-superclaw)
- **Choose what uninstall removes.** Uninstall keeps your data unless you select otherwise. See [Does uninstalling SuperClaw remove local user data?](#does-uninstalling-superclaw-remove-local-user-data)
- **Upgrade in place from v1.x.** Your project files, downloaded models, and v1.1 to v1.3 chat sessions carry over. See [Upgrading from v1.x](#upgrading-from-v1x).

### Models

- **Gemma 4 (experimental).** Gemma 4 26B-A4B on PTL 64GB systems and Gemma 4 E4B on PTL 32GB systems, as alternatives to the default Qwen models.
- **New edge server model.** The edge server now serves Qwen3.8-Flash-Next.
- **Lite tier, now supported.** Intel systems that cannot run a local chat model run the Lite tier, using cloud models or an edge server.

### MCP and tools

- **Local (stdio) MCP servers.** Add an MCP server as a local command, such as `npx` or `uvx`. SuperClaw ships its own Node.js and uv, so you do not need to install them.
- **Per-tool permissions.** Allow or deny each tool an MCP server offers.
- **Run on this computer.** Servers that need your desktop, such as computer-use servers, can run outside the sandbox as your user account. You approve each tool call, and a bar at the top of the window shows what is running, with **Stop all**.
- **SuperClaw browser.** Playwright MCP can drive a dedicated, visible InPrivate Microsoft Edge window instead of your own signed-in browser.
- **Document creation skills.** Built-in skills create PowerPoint (`.pptx`) and Word (`.docx`) files.

### Dictation and read-aloud

- **Dictation.** Speak into the prompt box, with recognition on your computer (English only) or through a cloud speech service. See [Dictation](#dictation).
- **Shortcut and Dictionary.** The default push-to-talk key is Right Alt. Add names and terms to the Dictionary to improve recognition; SuperClaw also learns words from the corrections you make.
- **Clean up dictated text.** Optionally have a model tidy up dictated text before it is sent.
- **More read-aloud voices.** Choose from more English voices for reading replies aloud.

### Chat

- **Search and favorites.** Search across your chat sessions, and pin sessions to favorites.
- **Token totals.** See token totals for each reply, split between local and cloud models.
- **Image input.** Paste or drop images into the prompt box.
- **Answering agent questions.** When an agent asks a question, type your own answer, skip the question, or dismiss it.

### Privacy and Slack

- **File Protection on every tier.** File Protection now also works on Lite systems. Its privacy models download the first time you turn it on, after you confirm, instead of being bundled with the installer. See [Privacy](#privacy).
- **Telemetry choices.** The installer asks whether to share installation telemetry and crash logs. You can change either choice later under **Settings > Privacy**.
- **Guided Slack setup.** You no longer create and configure the Slack app by hand. SuperClaw creates it in your workspace with the right permissions; you approve the install and paste two tokens.
- **Slack sender approval (action needed after upgrading).** The Slack bot now answers only people you approve. See [Slack](#slack).

---

## Releases

### v2.0 (Current)

SuperClaw v2.0 is open source. The [source code](https://github.com/intel/intel-ai-builder-superclaw) is available now; the Windows installer will follow.

<!-- TODO(release managers): replace with the final build number and download link once the installer is published. -->
A single [SuperClaw v2.0 Windows app](https://aibuilder.intel.com/installers/SuperClaw-Setup-2.0.0.XXXX.exe) (coming soon) runs natively on Windows, with no WSL or Docker, and provides five deployment options. The app detects your hardware at setup and configures the right solution automatically:

- **Edge-connected (Pro):** Connect to an enterprise edge server running Qwen3.8-Flash-Next for model serving [User Guide](./superclaw-ctl/USER-GUIDE.md).
- **Standalone on a single-B70 workstation (Pro):** Run the model-serving workload and desktop app on a workstation with one B70 card, RAM ≥ 32 GB, and ≥ 4800 MT/s, using the Qwen3.8-27B local model with full agent capabilities.
- **Standalone on PTL 64GB (Pro):** Run the model-serving workload and desktop app on a single PTL system with RAM ≥ 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.6-35B-A3B local model (or experimental Gemma 4 26B-A4B) with full agent capabilities.
- **Standalone on PTL 32GB (Standard):** Run standalone on a PTL system with RAM ≥ 32 GB and < 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.5-4B local model (or experimental Gemma 4 E4B) with Default Agent.
- **No local model (Lite, new):** Run on other Intel systems with RAM ≥ 16 GB and ≥ 5600 MT/s, using a cloud model or an edge server connection.

### v1.3 (Past Release)

A single [SuperClaw v1.3 Windows app](https://aibuilder.intel.com/installers/SuperClaw-Setup-1.3.0.922.exe) provides four deployment options. The app detects your hardware at setup and configures the right solution automatically:

- **Edge-connected (Pro):** Connect to an enterprise edge server for model serving [User Guide](./superclaw-ctl/USER-GUIDE.md).
- **Standalone on a single-B70 workstation (Pro, new):** Run the model-serving workload and desktop app on a workstation with one B70 card, RAM ≥ 32 GB, and ≥ 4800 MT/s, using the Qwen3.8-27B local model with full agent capabilities.
- **Standalone on PTL 64GB (Pro):** Run the model-serving workload and desktop app on a single PTL system with RAM ≥ 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.6-35B-A3B local model with full agent capabilities.
- **Standalone on PTL 32GB (Standard):** Run standalone on a PTL system with RAM ≥ 32 GB and < 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.5-4B local model with Default Agent.

### v1.2 (Past Release)

A single [SuperClaw v1.2 Windows app](https://aibuilder.intel.com/installers/SuperClaw-Setup-1.2.0.813.exe) provides three deployment options. The app detects your hardware at setup and configures the right solution automatically:

- **Edge-connected:** Connect to an enterprise edge server for model serving [User Guide](./superclaw-ctl/USER-GUIDE.md).
- **Standalone on PTL 64GB:** Run the model-serving workload and desktop app on a single PTL system with RAM ≥ 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.6-35B-A3B local model with full agent capabilities.
- **Standalone on PTL 32GB:** Run standalone on a PTL system with RAM ≥ 32 GB and < 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.5-4B local model with Default Agent.

### v1.1 (Past Release)

A single SuperClaw Windows app provides two deployment options. The app detects your hardware at setup and configures the right solution automatically:

- **Edge-connected:** Connect to an enterprise edge server for model serving [User Guide](./superclaw-ctl/USER-GUIDE.md).
- **Standalone on PTL 64GB:** Run both the model-serving workload and the [SuperClaw v1.1 Windows app](https://aibuilder.intel.com/installers/SuperClaw-Setup-1.1.0.731.exe) on a single PTL system with at least 64GB of RAM running at 8,000 MT/s or faster and a B370 (10 Xe) or B390 (12 Xe) iGPU.

### v1.0 (Past Release)

SuperClaw v1.0 supports only edge-connected deployment and requires a two-system configuration:

- **An AI PC companion device**, such as a Wildcat Lake system with 16GB of memory, runs the [SuperClaw v1.0 Windows app](https://aibuilder.intel.com/installers/SuperClaw-Setup-1.0.0.623.exe).
- **An enterprise edge server**, configured as a model-serving workstation with four B70 cards, runs Qwen3-Coder-Next-80B.

Users interact with SuperClaw on the AI PC while the model workload runs on the edge server.

---

## Setup Instructions

<!-- TODO(release managers): remove this note once the installer is published. -->
> **Note:** These steps use the v2.0 Windows installer. Until it is published, you can build SuperClaw from the [source code](https://github.com/intel/intel-ai-builder-superclaw); see that repository's README for build instructions.

1. **Update the graphics driver on PTL systems.** Install [Intel® Arc™ Graphics - Windows](https://www.intel.com/content/www/us/en/download/785597/intel-arc-graphics-windows.html) version **32.0.101.8860 or later** for significantly better model-inference performance. The installer's Hardware Review page also checks the driver version and links to the update.

2. **Configure your network.** If your corporate network requires a proxy for downloads, such as fetching models from Hugging Face, configure it in Windows before installing SuperClaw. SuperClaw uses your Windows proxy settings, including a proxy auto-config script, or the `HTTPS_PROXY` environment variable.

3. **Download and run the installer** from [Releases](#releases). The installer shows a Hardware Review page, asks about telemetry, and installs the Microsoft Visual C++ Redistributable if it is missing. When it finishes, choose **Restart Now** (recommended): the installer changes a graphics memory setting that takes effect after a restart.

4. **Approve the administrator prompt on first launch.** The first time SuperClaw starts, Windows asks for administrator approval so SuperClaw can set up its sandbox, once per user. If you decline or the prompt times out, click **Retry** and approve it. On a managed PC without administrator rights, ask your IT administrator to approve it.

5. **Wait for the first-run model download.** On PTL and B70 systems, SuperClaw downloads its local model on first launch: about 23 GB for Qwen3.6-35B-A3B, 21 GB for Qwen3.8-27B, or 3.4 GB for Qwen3.5-4B. Keep the app open until the download finishes. Later launches skip it. On Lite systems there is nothing to download; add a cloud model under **Settings > Model Routing** or connect to an edge server.

6. **Connect to an edge server (optional).** For edge server installation, configuration, and connection instructions, see the [`superclaw-ctl` Edge Server User Guide](./superclaw-ctl/USER-GUIDE.md). If the edge server is on your intranet, select **Bypass HTTP proxy** when you add it under **Settings > Model Routing**.

---

## Upgrading from v1.x

Run the v2.0 installer over your existing installation. It upgrades any v1.0 to v1.3 installation in place.

**What carries over:**

- Your project files in `%USERPROFILE%\SuperClawProjects`.
- Downloaded models.
- Chat sessions from v1.1 to v1.3. SuperClaw copies them out of the old WSL environment once, on the first v2.0 launch. Sessions from v1.0 are not imported.

**What does not carry over:**

- **Sign-ins and keys.** Sign in again to your cloud model providers, MCP servers, Tavily, GitHub, and Gmail.
- **Undo history and tool results** in imported sessions; the messages themselves are kept.
- **Slack access.** After upgrading, a connected Slack bot stops answering until you approve each person. See [Slack](#slack).

If an MCP server URL uses `host.docker.internal`, change it to `localhost` or `127.0.0.1`; v2.0 does not run in Docker.

After the chat sessions are imported, SuperClaw removes its old WSL distro (`superclaw-docker`) and frees several GB of disk space. If the import does not finish, SuperClaw keeps the distro, because it may hold the only copy of your sessions. Once your old sessions appear in v2.0, or you no longer need them, remove it by running `wsl --unregister superclaw-docker`.

---

## App Settings

**Settings** (in the sidebar) is where enterprises and users tailor SuperClaw to their hardware, providers, and workflows. In v2.0 its tabs are **General**, **Model Routing**, **Privacy**, **Connections**, **Dictation**, **Agents**, **Skills**, **MCP**, and **Schedulers**.

#### General

- **Appearance & Language** — Match the system theme or force light/dark mode, and choose the interface language.
- **Workspace Cleanup** — Automatically remove agent-generated logs, temp files, and cache from the workspace after a configurable retention period. Your results and reports are never touched.

#### Model Routing

Configure local and cloud models, connect cloud providers using API keys or OAuth, and choose which models Auto Route can use. On PTL 32GB, PTL 64GB, or single-B70 workstation systems, you can use a local model served with llama.cpp, including the experimental Gemma 4 models on PTL; alternatively, connect to an edge server for model serving. On Lite systems, configure a cloud model or connect to an edge server. SuperClaw adds broader model support with each release and lets users tune the Auto Route parameter to balance response quality against cost and privacy.

#### Privacy

- **File Protection (Experimental)** — Optionally detect and mask sensitive information before cloud processing for supported files (CSV, Excel, Parquet, TXT, Markdown, HTML, and Word) used with the Default Agent and Hybrid Coding Agent. Turn it on or off; before analyzing a protected file, SuperClaw asks whether to mask it. The first time you turn it on, SuperClaw asks to download its privacy models (about 536 MB). This feature is off by default as detection may not be fully accurate.
- **Telemetry** — Change the installation telemetry and crash log choices you made in the installer.

#### Connections

- **Web Search** — Configuring a [Tavily](https://www.tavily.com/) API key is strongly recommended for higher-quality, more reliable search results. Tavily offers 1,000 free searches with sign-in. Without a key, web search falls back to DuckDuckGo, which may return lower-quality results.
- **Gmail Credentials** — Upload Google OAuth credentials to authorize the Email & Calendar Agent. SuperClaw provides setup instructions when you ask it to access your email. If you need more guidance, follow this [Gmail API setup video](https://www.youtube.com/watch?v=RsY14ltDNFM).
- **Slack** — Deliver agent and scheduled-task results to your team in Slack. See [Slack](#slack).

#### Slack

To connect Slack, open **Settings > Connections > Slack**, click **Connect Slack**, and follow the three steps in the app:

1. On Slack's [Your Apps](https://api.slack.com/apps) page, under **Your App Configuration Tokens**, generate a token for your workspace and paste the access token into SuperClaw. SuperClaw uses it once to create the Slack app and does not save it.
2. Approve the install in the browser tab that opens. If your workspace requires an admin to approve new apps, ask them to approve SuperClaw, then start again.
3. On the app's **Socket Mode** page, turn on **Enable Socket Mode**, generate an app-level token (`xapp-`), and paste it into SuperClaw.

The app is named **SuperClaw** in Slack. Send it a direct message, or use it in a channel: invite it first with `/invite @SuperClaw`, then mention `@SuperClaw`. It does not see channels it has not been invited to.

> ⚠️ **Important:** The Slack bot answers only people you approve. The first time someone messages the bot, Slack tells them how to request access. Approve or remove people under **Settings > Connections > Slack**; changes take effect immediately, with no restart.

#### Dictation

Choose **Local** recognition (on your computer, English only, offline after a one-time ~630 MB download, up to 2 minutes per recording) or **Cloud** recognition (follows your system language). Set up to four shortcut keys or mouse buttons (Right Alt by default), manage the Dictionary of names and terms, choose the read-aloud voice, and optionally turn on **Clean up dictated text**, which uses a model to tidy what you dictated. Read-aloud downloads its English voices (about 337 MB) the first time you use it.

#### Agents

Create a custom agent by uploading a `.md` configuration file or entering the configuration directly. You can add installed skills and the following built-in tool groups to your agent. Built-in tool groups are disabled until you select them:

- **File & Code Engine:** Navigate source files, edit code, and control command execution.
- **Email & Calendar Operations:** Analyze inboxes, manage response workflows, and perform scheduling actions. (Available only on systems with full agent capabilities.)
- **Web & Research Retrieval:** Find evidence on the web and retrieve information for trend-oriented research.

> 💡 **Tip:** To use a custom agent, mention it with `@` in the prompt window or select it from the agent dropdown menu.

#### Skills

Manage reusable skills for your agents. You can create or import custom skills, or install available skills with a single click. Click a skill card to preview its `SKILL.md`. Built-in skills include creating PowerPoint and Word documents.

> 💡 **Tip:** Invoke a skill by entering `/` in the prompt window and selecting it. Built-in agents have predefined capabilities and may not automatically use installed skills. To make an installed skill available to a custom agent, add it under **Agents**.

#### MCP

SuperClaw supports the **Model Context Protocol (MCP)**, an open standard for connecting AI agents to external tools and data sources. Add a server from the catalog, or click **Add MCP** and enter either:

- **Remote URL** — an HTTP or SSE endpoint, such as `http://localhost:<port>/mcp` (streamable HTTP) or `http://localhost:<port>/sse` (SSE).
- **Local command** — a stdio server started by a command, such as `npx -y <package>` or `uvx <package>`. SuperClaw includes Node.js and uv, so you do not need to install them.

Local commands run inside SuperClaw's sandbox by default. For servers that need your desktop, such as computer-use servers, turn on **Run on this computer**: the server then runs outside the sandbox as your user account, and SuperClaw asks you to approve each tool call. A bar at the top of the window shows what is running and offers **Stop all**.

For browser automation with Playwright MCP, turn on **Use SuperClaw browser**. The agent then drives a dedicated, visible InPrivate Microsoft Edge window rather than your own signed-in browser.

Click a configured server to allow or deny each of its tools.

For a GitHub MCP server, add `http://127.0.0.1:19876/mcp/oauth/callback` as the OAuth callback URL in your GitHub OAuth app.

> ⚠️ **Important:** **Disable or remove MCP servers you are not using**, and deny tools you do not need. Their tools consume significant context and may introduce irrelevant options that reduce agent accuracy.

#### Schedulers

Create scheduled tasks for recurring work, or start from built-in templates for common automation workflows. For best results, provide clear and detailed instructions for what the agent should do.

---

## FAQ

### Why does SuperClaw ask for administrator approval when it first starts?

SuperClaw v2.0 runs its backend in a native Windows sandbox, with each component under its own restricted Windows account. Creating those accounts and setting their folder permissions needs administrator approval once per user on each computer. If you decline the prompt or it times out, SuperClaw shows why it could not start; click **Retry** and approve the prompt. On a managed PC without administrator rights, ask your IT administrator to approve it.

### What does the SuperClaw sandbox protect?

In v2.0 the sandbox limits which files and folders agents can read and write, and keeps backend components apart from each other and from your user account. It does not yet restrict network access. MCP servers you set to **Run on this computer** run outside the sandbox as your user account; SuperClaw asks you to approve each of their tool calls.

### Do I still need WSL or Intel VT-x virtualization?

No. v2.0 does not use WSL, Docker, or a virtual machine, so neither WSL nor virtualization in BIOS is required.

### Why does SuperClaw seem stuck the first time it starts?

The first start after installing or updating SuperClaw can take longer, especially with Windows Smart App Control turned on: Windows checks each SuperClaw component the first time it runs. If SuperClaw is still starting after a few minutes and is not showing a model download, close it and open it again. Later starts are faster. You do not need to turn off Smart App Control.

<!-- TODO(release managers): drop this entry if the first-start timeout fix lands before v2.0 ships. -->

### Which graphics driver do I need to run models locally on PTL systems?

To run a local model on a PTL system, install [Intel® Arc™ Graphics - Windows](https://www.intel.com/content/www/us/en/download/785597/intel-arc-graphics-windows.html) version **32.0.101.8860 or later** for significantly better model-inference performance. See [Setup Instructions](#setup-instructions) for the full setup sequence.

### How do I configure SuperClaw for corporate proxy or VPN environments?

SuperClaw uses your Windows proxy settings, including a proxy auto-config (PAC) script, so it normally works on a corporate network or VPN without extra setup. You can also set the `HTTPS_PROXY` environment variable. If an edge server is on your intranet, select **Bypass HTTP proxy** when you add it under **Settings > Model Routing**. The v1.x `.wslconfig` and network-switching workarounds are no longer needed.

### How do I update SuperClaw?

Click the version button in the sidebar to check for updates. If an update is available, click it again to download it; when the download is ready, click **Restart and install**. You can also download and run the latest installer.

### My Slack bot stopped replying after I upgraded. Why?

v2.0 answers only Slack users you have approved. Each person who messages the bot is told once how to get access. Approve them under **Settings > Connections > Slack**.

### Where does SuperClaw store my files?

SuperClaw uses `%USERPROFILE%\SuperClawProjects` as its workspace, where `%USERPROFILE%` is normally `C:\Users\<your_user_id>`. Place your files here for SuperClaw to access them, and generated results will also be saved here. Files you upload in the SuperClaw app are also saved to this folder. Downloaded models, backend data, and logs are stored under `%LOCALAPPDATA%\SuperClaw`; app settings and window data are stored in the `com.aibuilder.superclaw` folders under `%APPDATA%` and `%LOCALAPPDATA%`.

### Does uninstalling SuperClaw remove local user data?

Only if you choose. The uninstall dialog has two options, both unchecked by default:

- **Remove downloaded models** — deletes the local models SuperClaw downloaded.
- **Remove app settings and data** — deletes saved settings, API keys, and logs.

Select both to remove downloaded models and app settings and data. A silent uninstall keeps your data. Your project files in `%USERPROFILE%\SuperClawProjects` are never removed.

### Which transports do MCP servers support?

Remote servers can use **HTTP** (streamable HTTP) or **SSE**. Local servers can use **stdio**, started from a command such as `npx` or `uvx`. See [App Settings > MCP](#mcp).

### Which cloud models should I choose?

SuperClaw supports the cloud providers listed under **Settings > Model Routing**. For the best experience, pick a standard
chat/instruct model rather than a reasoning model.

Reasoning models (also called thinking, extended thinking, or chain-of-thought
models) "think out loud" internally before giving you an answer. This makes
them slower and more expensive to run, and it can cause multi-step workflows
like the Deep Research Agent to time out without finishing. If a long-running
task keeps failing to complete, try switching to a non-reasoning model first.

SuperClaw cannot reliably turn off a model's reasoning — that's mostly controlled by the
model provider. Some providers let you hide the reasoning text from the
response, but that only hides the output; it doesn't make the model faster or
cheaper to run.
