# Morgan 🚀

Morgan is a state-of-the-art, low-latency autonomous coding harness and agentic AI environment, designed with a stunning Terminal User Interface (TUI) reminiscent of Claude Code. Engineered for raw speed and security, Morgan integrates seamlessly into your local development environment while maintaining strict isolation protocols.

## Features

- **Blazing Fast TUI**: A buttery-smooth, fully-animated terminal user interface built on Textual. 
- **Autonomous Subagents**: Out-of-the-box support for delegating complex, asynchronous tasks to isolated subagent processes.
- **Dynamic Configuration (`agent.md`)**: Project-level custom instructions automatically injected into the core system prompt via local `.deepagents/agent.md` files.
- **Slash Commands**: Powerful chat commands (`/skills`, `/mcp`, `/settings`, `/notifications`) for seamless configuration without ever leaving the TUI.
- **Tight Security**: Enforced `0o600` and `0o700` POSIX file permissions for all API keys, local credentials, and configuration states, alongside advanced SSRF protections.
- **MCP Integration**: Fully supports the Model Context Protocol (MCP) for extensible tool development and seamless OAuth authentication.

## Installation

You can install Morgan directly from this GitHub repository using `pip`:

```bash
pip install git+https://github.com/RavaniRoshan/morgan.git#subdirectory=libs/code
```

*Note: Morgan relies on the `deepagents-code` subsystem which is located in the `libs/code` directory of this repository.*

## Quick Start

Once installed, simply activate your environment and launch the interactive TUI:

```bash
dcode
```

### Essential Commands
Within the chat window, type `/help` to see all commands, or use these quick shortcuts:
- `/mcp`: Open your local MCP configuration directory.
- `/skills`: Open your custom skills directory.
- `/settings`: Launch your settings (`config.toml`) in your default text editor.
- `/auth`: Manage your provider and service credentials securely.

## Configuration

Morgan relies on the `.deepagents` directory to store its state safely. You can define project-level customizations by creating an `agent.md` file in your repository:

```bash
mkdir -p .deepagents
echo "Always use strict TypeScript types." > .deepagents/agent.md
```
Morgan will detect this file during initialization and ground the system prompt in your project's custom rules.

## Security Model

Morgan is built to be security-driven:
- **No API Leaks**: Pydantic `SecretStr` protects your tokens in memory, and crash logs automatically redact sensitive credentials.
- **Filesystem Lockdown**: The agent enforces read/write lockdowns on its credential stores.
- **Local Sandbox Execution**: Commands execute strictly inside monitored sandboxes, isolating operations from critical host OS components.

## License

MIT License. See `LICENSE` for more details.