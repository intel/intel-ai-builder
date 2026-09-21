<h1 align="center">Intel® AI SuperClaw</h1>

**Hybrid agentic AI for enterprises: local by default, cloud when it counts.**

SuperClaw brings hybrid agentic AI to AI PCs, workstations, agent computers, and edge devices. Built by Intel's AI Super Builder team, it helps enterprises scale intelligent agents without losing sight of cloud cost, performance, or data security.

Agentic AI can take on complex work across tools, files, code, and business data. But when every task goes to the cloud, token costs climb and sensitive context can face added privacy and control risks.

SuperClaw takes a different route: routine and sensitive work stays on-device or at the enterprise edge, while cloud models step in for advanced reasoning, planning, and external data retrieval.

For more details, read Intel's article, [Solving the Agentic AI Trilemma: Cost, Scale, and Data Security](https://newsroom.intel.com/opinion/solving-the-agentic-ai-trilemma-cost-scale-and-data-security).

---

<a name="toc"></a>
- [Overview](#overview)
- [Releases](#releases)
- [Setup Instructions](#setup-instructions)
- [App Settings](#app-settings)
- [FAQ](#faq)

## Overview

### Why SuperClaw

- **Spend cloud tokens where they matter.** Handle routine and sensitive tasks locally, and reserve cloud models for work that needs them.
- **Keep sensitive data closer.** Private data stays on-device or within the enterprise edge by default, with context minimized before cloud escalation.
- **Match the model to the moment.** Each workflow step goes to the execution layer best suited to the task.
- **Put modern Intel hardware to work.** SuperClaw is designed for Intel AI PCs and workstations, including systems with Intel® Core™ Ultra processors and Intel® Arc™ Pro B-series GPUs.
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
| **Local File Agent** | Extracts and answers questions from documents such as PDF, CSV, Markdown, DOCX, XLSX, and PPTX using local models for precision and privacy. Includes a built-in OCR tool for extracting text from images. |
| **Web Search Agent** | Returns focused, factual answers with source citations for current information from the web. |
| **File Protection (Experimental)** | An optional, off-by-default feature that detects and masks sensitive information before cloud processing. |

For example, with experimental File Protection enabled, a customer-records spreadsheet can move through a coordinated pipeline that prepares the data, attempts to detect and mask personal information, performs the analysis, and limits the context sent to the cloud.

#### Agent availability by hardware

The full specialized-agent lineup is available only on the enterprise edge server and higher-memory AI PCs. More constrained systems run an enhanced Default Agent with full tools, permissions, and skills instead of the complete set of specialized agents.

| Hardware | Local model | Available agents |
|----------|-------------|------------------|
| Edge server (4× B70) | Qwen3-Coder-Next-80B | Default, Hybrid Coding, Deep Research, Email & Calendar |
| Workstation — 1× B70, RAM ≥ 32 GB, ≥ 4800 MT/s | Qwen3.8-27B | Default, Hybrid Coding, Deep Research, Email & Calendar |
| PTL — RAM ≥ 64 GB, ≥ 6400 MT/s, iGPU B370 (10 Xe) or B390 (12 Xe) | Qwen3.6-35B | Default, Hybrid Coding, Deep Research, Email & Calendar |
| PTL — RAM ≥ 32 GB and < 64 GB, ≥ 6400 MT/s, iGPU B370 (10 Xe) or B390 (12 Xe) | Qwen3.5-4B | Enhanced Default Agent with full tools, permissions, and skills |

> **Note:** PTL refers to Intel Panther Lake (Core Ultra Series 3).

> ⚠️ **Important:** The GPU check matches the adapter name reported by Windows, which must contain `B70`, `B370`, or `B390`. A generic name such as "Intel(R) Graphics" does not match, even on supported silicon.
>
> If the adapter name or memory requirements do not match, SuperClaw installs no local chat model — only the small Qwen3.5-0.8B model used for File Protection. To run agents, configure a cloud model under **Advanced > Model Routing** or connect to an edge server.

---


### Auto Route

**Auto Route is SuperClaw's intelligent, customizable model router.** For each task, it chooses between a local model hosted on an AI PC or at the enterprise edge and a model in the cloud.

Users set the balance. Higher settings favor response quality and route more tasks to cloud models; lower settings favor cost savings and privacy by keeping more tasks local.

- **Transparent.** Users see a single assistant response while SuperClaw handles the execution strategy behind the scenes.
- **Task-aware.** Lightweight, sensitive, and repetitive work stays local; demanding reasoning and planning can be routed to cloud models.
- **User-controlled.** Users can tune Auto Route's quality tradeoff, force a local model for on-device work, or select a cloud model directly when maximum capability is required.

To enable Auto Route, configure both a local model and at least one cloud model in Settings. If only local models are available, users can select a local model and work entirely offline.

---

## Releases

### v1.3 (Current)

A single [SuperClaw v1.3 Windows app](https://aibuilder.intel.com/installers/SuperClaw-Setup-1.3.0.921.exe) provides four deployment options. The app detects your hardware at setup and configures the right solution automatically:

- **Edge-connected:** Connect to an enterprise edge server for model serving [User Guide](./superclaw-ctl/USER-GUIDE.md).
- **Standalone on a single-B70 workstation (new):** Run the model-serving workload and desktop app on a workstation with one B70 card, RAM ≥ 32 GB, and ≥ 4800 MT/s, using the Qwen3.8-27B local model with full agent capabilities.
- **Standalone on PTL 64GB:** Run the model-serving workload and desktop app on a single PTL system with RAM ≥ 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.6-35B-A3B local model with full agent capabilities.
- **Standalone on PTL 32GB:** Run standalone on a PTL system with RAM ≥ 32 GB and < 64 GB, ≥ 6400 MT/s, and a B370 (10 Xe) or B390 (12 Xe) iGPU, using the Qwen3.5-4B local model with Default Agent.

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

### Following Release (Planned)

The following release will broaden support for other Intel hardware.

---

## Setup Instructions

1. **Update the graphics driver on PTL systems.** Install [Intel® Arc™ Graphics - Windows](https://www.intel.com/content/www/us/en/download/785597/intel-arc-graphics-windows.html) version **32.0.101.8860 or later** for significantly better model-inference performance.

2. **Configure your network.** If your corporate network requires a proxy for downloads, such as fetching models from Hugging Face, configure it before installing SuperClaw.

    If SuperClaw cannot access the internet or your corporate proxy from WSL2, add the following to `C:\Users\<username>\.wslconfig` (create the file if necessary):

    ```ini
    [wsl2]
    networkingMode=mirrored
    ```

3. **Install SuperClaw and restart Windows.** The SuperClaw backend runs in an isolated WSL environment. If WSL is not already available, the SuperClaw installer installs it. Restart Windows after WSL is installed, then continue or rerun the SuperClaw installer.

4. **Connect to an edge server (optional).** For edge server installation, configuration, and connection instructions, see the [`superclaw-ctl` Edge Server User Guide](./superclaw-ctl/USER-GUIDE.md).

---

## App Settings

The **Advanced** area is where enterprises and users tailor SuperClaw to their hardware, providers, and workflows.

#### Model Routing

Configure local and cloud models, connect cloud providers using API keys or OAuth, and choose which models Auto Route can use. On PTL 32GB, PTL 64GB, or single-B70 workstation systems, you can configure a local model served with llama.cpp; alternatively, connect to an edge server for model serving. SuperClaw adds broader model support with each release and lets users tune the Auto Route parameter to balance response quality against cost and privacy.

#### Configuration

A single place for core operational settings:

- **Web Search** — Configuring a [Tavily](https://www.tavily.com/) API key is strongly recommended for higher-quality, more reliable search results. Tavily offers 1,000 free searches with sign-in. Without a key, web search falls back to DuckDuckGo, which may return lower-quality results.
- **Gmail Credentials** — Upload Google OAuth credentials to authorize the Email & Calendar Agent. SuperClaw provides setup instructions when you ask it to access your email. If you need more guidance, follow this [Gmail API setup video](https://www.youtube.com/watch?v=RsY14ltDNFM).
- **Workspace Cleanup** — Automatically remove agent-generated logs, temp files, and cache from the workspace after a configurable retention period. Your results and reports are never touched.
- **Appearance & Language** — Match the system theme or force light/dark mode, and choose the interface language.
- **File Protection (Experimental)** — Optionally detect and mask sensitive information before cloud processing for supported files used with the Default Agent and Coding Agent. This feature is off by default as detection may not be fully accurate.

#### Scheduler

Create scheduled tasks for recurring work, or start from built-in templates for common automation workflows. For best results, provide clear and detailed instructions for what the agent should do.

#### Skill

Manage reusable skills for your agents. You can create or import custom skills, or install available skills with a single click.

> 💡 **Tip:** Invoke a skill by entering `/` in the prompt window and selecting it. Built-in agents have predefined capabilities and may not automatically use installed skills. To make an installed skill available to a custom agent, add it under **Agent Customization**.

#### MCP

SuperClaw supports the **Model Context Protocol (MCP)**, an open standard for connecting AI agents to external tools and data sources. Current local MCP server support has a few setup requirements because SuperClaw's backend runs inside Docker on WSL2 while the UI runs on Windows.

For local MCP servers:

- Use **HTTP** or **SSE** transport. Stdio-based MCP servers are not supported in the current release.
- Start the MCP server on Windows. With WSL's default NAT networking, bind it to `0.0.0.0`; with mirrored networking, you can use `127.0.0.1` or `localhost`.
- Use `http://host.docker.internal:<port>/<endpoint>` with NAT networking. With mirrored networking, use the server's original loopback URL, such as `http://127.0.0.1:<port>/<endpoint>` or `http://localhost:<port>/<endpoint>`.
- Common endpoints are `/mcp` for streamable HTTP and `/sse` for SSE.

For a GitHub MCP server, add `http://localhost:19876/mcp/oauth/callback` as the OAuth callback URL. This allows the OAuth flow in the Windows browser to return the response to the SuperClaw backend running in WSL.

> ⚠️ **Important:** **Disable or remove MCP servers you are not using.** Their tools consume significant context and may introduce irrelevant options that reduce agent accuracy.

#### Channel

Deliver agent and scheduled-task results to your team's messaging tools. Slack is supported in the first release, with additional channels planned.

To configure Slack, go to [Slack API Apps](https://api.slack.com/apps), create a new app from scratch, and select your workspace. For a walkthrough, follow this [Slack app setup video](https://www.youtube.com/watch?v=eMN94wkwYME).

Under **Basic Information > App-Level Tokens**, create an app-level token (`xapp`) with the `connections:write` scope. Copy this token; you will need it to connect SuperClaw. Turn on **Socket Mode** under **Settings > Socket Mode** so the app can receive events.

To let users send the bot direct messages, open **App Home**, turn on the **Home Tab**, and check **Allow users to send slash commands and messages from the messages tab**.

Under **Features > Event Subscriptions**, turn on **Enable Events**. Under **Subscribe to bot events**, add the following events and save your changes:

```text
message.im
message.mpim
message.channels
message.groups
app_mention
```

In Slack, open **Features > OAuth & Permissions > Bot Token Scopes** and add these recommended bot token (`xoxb`) scopes for full support:

```text
app_mentions:read
channels:history
channels:join
channels:read
chat:write
chat:write.public
commands
files:read
files:write
groups:history
groups:read
im:history
im:read
im:write
incoming-webhook
mpim:history
mpim:read
reactions:read
reactions:write
users:read
```

Click **Install to Workspace** (or **Reinstall to Workspace** if you changed scopes) to generate the bot token (`xoxb`).

Minimal public-channel setup: `app_mentions:read`, `channels:read`, `chat:write`, and `users:read`. Add `channels:history` for channel context and [`chat:write.public`](https://docs.slack.dev/reference/scopes/chat:write.public) to send messages to public channels where your Slack app is not a member. After installation, copy the bot token and app token into **Advanced > Channel > Slack**, then mention the bot using your Slack app name (for example, `@YourAppName`) to start using it.

#### Agent

Create a custom agent by uploading a `.md` configuration file or entering the configuration directly. You can add installed skills and the following built-in tool groups to your agent. Built-in tool groups are disabled until you select them:

- **File & Code Engine:** Navigate source files, edit code, and control command execution.
- **Email & Calendar Operations:** Analyze inboxes, manage response workflows, and perform scheduling actions. (Available only on systems with full agent capabilities.)
- **Web & Research Retrieval:** Find evidence on the web and retrieve information for trend-oriented research.

> 💡 **Tip:** To use a custom agent, mention it with `@` in the prompt window or select it from the agent dropdown menu.

---

## FAQ

### Why does Windows Smart App Control prevent SuperClaw from starting?

If Windows Security reports that it blocked a SuperClaw component, open **Windows Security > App & browser control > Smart App Control settings** and turn Smart App Control off, then relaunch SuperClaw. Disable this protection only after confirming it is the cause; turning it off reduces application-security protection, and Windows may require a reset or reinstall before it can be enabled again.

### Which graphics driver do I need to run models locally on PTL systems?

To run a local model on a PTL system, install [Intel® Arc™ Graphics - Windows](https://www.intel.com/content/www/us/en/download/785597/intel-arc-graphics-windows.html) version **32.0.101.8860 or later** for significantly better model-inference performance. See [Setup Instructions](#setup-instructions) for the full setup sequence.

### Why must Intel VT-x virtualization be enabled for WSL?

SuperClaw uses WSL, which requires CPU virtualization to be enabled in BIOS/UEFI. If installation fails, enable Intel Virtualization Technology, also called Intel VT-x, restart Windows, and run the installer again. On managed PCs, contact your IT administrator if the setting is locked or unavailable.

Note that immediately after WSL is installed, the installer may falsely report that virtualization is not enabled even when it is. Restart the system after WSL installation, then run the installer again; this usually clears the false warning.

### What should I do if installation fails after WSL is installed or stalls around 10%?

- **WSL installed but Windows not restarted:** If WSL is installed during setup and Windows is not restarted, the SuperClaw installer may stop or have errors. Restart Windows, then run the installer again so the WSL components are fully available.
- **Installation stalls around 10%:** If `wsl.exe` reports `Wsl/CallMsi/Install/REGDB_E_CLASSNOTREG` or says WSL is corrupted, open PowerShell as Administrator, run `wsl --install --no-distribution`, restart Windows, and run the installer again. If needed, run `wsl --update` as Administrator, restart, and try again.

### How do I configure SuperClaw for corporate proxy or VPN environments?

- **Proxy setup and network switching:** If your corporate network requires a proxy for downloads, configure the required HTTP proxy before installing SuperClaw. On an open network, no proxy setup is needed. If you switch between a corporate network and an outside network, quit SuperClaw, run `wsl.exe --unregister superclaw-docker`, and reopen the app so the backend is recreated with the current network settings.
- **SuperClaw cannot reach the internet or your corporate proxy from within WSL2:** Add the following to `C:\Users\<username>\.wslconfig` (create the file if it does not exist):
  ```ini
  [wsl2]
  networkingMode=mirrored
  ```
  This makes WSL2 mirror your Windows network interfaces so that proxy and VPN routes are automatically inherited. After saving the file, run `wsl --shutdown` in PowerShell or Command Prompt to restart WSL2, then relaunch SuperClaw.

### Where does SuperClaw store my files?

SuperClaw uses `%USERPROFILE%\SuperClawProjects` as its workspace, where `%USERPROFILE%` is normally `C:\Users\<your_user_id>`. Place your files here for SuperClaw to access them, and generated results will also be saved here. Files you upload in the SuperClaw app are also saved to this folder.

### Does uninstalling SuperClaw remove local user data?

No. Data may remain under `C:\Users\<user_id>\AppData\Local\SuperClaw`.

### Which transports do local MCP servers support?

Local MCP servers must use **HTTP** or **SSE** transport. Stdio-based MCP servers are not supported in the current release. See [App Settings > MCP](#app-settings) for endpoint and networking details.


### Which cloud models should I choose?

SuperClaw works with any OpenAI-compatible cloud provider you configure under
**Advanced > Model Routing**. For the best experience, pick a standard
chat/instruct model rather than a reasoning model.

Reasoning models (also called thinking, extended thinking, or chain-of-thought
models) "think out loud" internally before giving you an answer. This makes
them slower and more expensive to run, and it can cause multi-step workflows
like the Deep Research Agent to time out without finishing. If a long-running
task keeps failing to complete, try switching to a non-reasoning model first.

SuperClaw can't turn off a model's reasoning for you — that's controlled by the
model provider. Some providers let you hide the reasoning text from the
response, but that only hides the output; it doesn't make the model faster or
cheaper to run.
