<p align="center">
  <img src="https://raw.githubusercontent.com/langchain-ai/deepagents/main/libs/code/images/tui.png" alt="Morgan" width="600"/>
</p>

# 🌌 Morgan

**The next-generation autonomous coding harness. Morgan is a high-performance AI agentic environment featuring a stunning TUI, strict security isolation, and a modular architecture for frontier AI engineering.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyPI Version](https://img.shields.io/pypi/v/deepagents-code?label=core_version)](https://pypi.org/project/deepagents-code/#history)
[![Twitter](https://img.shields.io/twitter/follow/langchain_oss?label=Follow)](https://x.com/langchain_oss)

---

## ⚡ Quick Start

Get Morgan running in your terminal with a single command:

```bash
pip install git+https://github.com/RavaniRoshan/morgan.git#subdirectory=libs/code
```

**Launch the interface:**
```bash
dcode
```

---

## 💡 Why Morgan?

Morgan isn't just another wrapper. It's an engineered environment for developers who need **speed**, **security**, and **autonomy**.

- **🚀 Raw Performance**: A buttery-smooth, fully-animated TUI built on Textual for zero-latency interaction.
- **🛡️ Hardened Security**: Enforced POSIX permissions (`0o600`/`0o700`) for credentials and advanced SSRF protections to keep your host safe.
- **🤖 Agentic Orchestration**: Native support for autonomous sub-agents that can handle complex, asynchronous tasks in parallel.
- **🔌 MCP Native**: Full Model Context Protocol (MCP) integration for an infinitely extensible tool ecosystem.

---

## ✨ Core Features

| Feature | Description | Benefit |
| :--- | :--- | :--- |
| **Interactive TUI** | Professional terminal interface with streaming responses | 10x faster dev loop |
| **Autonomous Delegation** | Spawn isolated sub-agents for complex sub-tasks | Solve bigger problems faster |
| **Project grounding** | Local `.deepagents/agent.md` for custom project rules | Zero-shot context injection |
| **Secure Vault** | Pydantic `SecretStr` and credential lockdowns | Enterprise-grade security |
| **Custom Skills** | Extend the agent with your own slash commands | Tailor the AI to your workflow |

---

## 🏗️ Repository Map

This repository is structured as a monorepo to separate the core engine from the high-level harness:

- **[`libs/code/`](./libs/code)** $\rightarrow$ **The Heart of Morgan.** Contains the `deepagents-code` package, the TUI logic, and tool registries. **[Full Technical README here](./libs/code/README.md)**
- **`examples/`** $\rightarrow$ Reference implementations of custom skills.
- **`tests/`** $\rightarrow$ Comprehensive unit and integration suites.

---

## 🛠️ Essential Commands

Once inside the Morgan TUI, use these shortcuts:
- `/skills` $\rightarrow$ Manage your custom agent capabilities.
- `/mcp` $\rightarrow$ Configure Model Context Protocol tools.
- `/settings` $\rightarrow$ Edit your `config.toml` on the fly.
- `/auth` $\rightarrow$ Securely manage API keys and provider tokens.

---

## ⚠️ Security Warning

> [!WARNING]
> Morgan provides powerful shell access. While it includes advanced isolation, always ensure you are running the agent in a directory you trust or utilize a remote sandbox backend for untrusted code.

---

## 🤝 Contributing

We are building the future of agentic engineering. 
1. **Fork** $\rightarrow$ **Branch** $\rightarrow$ **Implement** $\rightarrow$ **Test** $\rightarrow$ **PR**.
2. Refer to the [Contributing Guide](https://docs.langchain.com/oss/python/contributing/overview) for quality standards.

---

## 📄 License

**SPDX License Identifier: MIT**  
Copyright (c) 2026 Ravani Roshan
