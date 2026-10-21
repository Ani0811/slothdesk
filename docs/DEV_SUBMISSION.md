---
title: "SlothDesk — Local-First AI Downloads Organizer: Less sorting. More living."
published: false
description: "A local-first AI-powered Downloads organizer with two-phase execution, smolagents, LM Studio inference, and zero overwrites."
tags: devchallenge, opensource, ai, python, react
cover_image: https://raw.githubusercontent.com/Ani0811/slothdesk/main/frontend/public/icons.svg
canonical_url: https://github.com/Ani0811/slothdesk
---

*This is a submission for the [DEV Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges).*

---

## 🦥 What I Built

**SlothDesk** is a local-first, desktop-style dashboard that rewards laziness by safely organizing your cluttered Downloads folder with minimal user effort.

> **Tagline:** Less sorting. More living.

Downloads folders are notorious black holes where productivity goes to die. Files of every kind—invoices, design assets, archives, code scripts, and firmware—pile up in an unmanageable mess. 

Existing tools typically fall into two extremes:
1. **Dumb regex scripts** that break on edge cases and force rigid naming conventions.
2. **Cloud AI utilities** that upload your private documents and filenames to third-party APIs, charging recurring subscription fees.

SlothDesk charts a different path: **Slow and Steady**. It runs completely offline using **Hugging Face `smolagents`** and **LM Studio** (`Qwen2.5-7B-Instruct`), treating the language model as an untrusted reasoning engine rather than a reckless file manipulator.

```text
Downloads/
├── Documents/
├── Images/
├── Videos/
├── Audio/
├── Archives/
├── Code/
└── Other/
```

---

## 🔒 The "Slow and Steady" Philosophy: Safety First

Many AI file organizers give the model direct write tools or shell access (`CodeAgent`, `shutil.rmtree`, `os.rename`). If the model hallucinates or encounters ambiguous context, files can be permanently destroyed.

In SlothDesk, filesystem mutation is architecturally separated from AI reasoning:

1. **Zero Model Execution Privileges**: The model has no write tools, cannot run shell commands, and does not execute dynamic Python scripts. It is given only 3 read-only metadata inspection tools:
   - `get_file_metadata(filename)`
   - `get_allowed_categories()`
   - `validate_category(category)`
2. **Strict Scope Confinement**: Operations are locked strictly inside the configured `SLOTHDESK_ROOT`. Any path containing `..`, absolute drive letters, or symbolic links is immediately rejected.
3. **Deterministic Collision Protection**: If a destination file already exists or another file in the plan shares the name, SlothDesk safely resolves it to `{name}_{counter}{ext}` (e.g. `invoice_october_1.pdf`). **Existing files are never overwritten.**
4. **Cryptographic State Check**: At scan time, SlothDesk computes the SHA-256 hash and byte size of every file. At execution time, it re-verifies these hashes. If a file was modified or deleted while waiting for approval, the move is skipped to eliminate race conditions.
5. **Reversible Manifests**: Every approved move generates an immutable JSON audit manifest, enabling one-click rollbacks at any time.

---

## 📸 Demo & Walkthrough

Follow the complete 3-minute video walkthrough script in [`docs/DEMO_SCRIPT.md`](https://github.com/Ani0811/slothdesk/blob/main/docs/DEMO_SCRIPT.md).

### The SlothDesk Workflow

1. **Scan & Propose (Read-Only)**: Click "Scan & Propose Plan". The dashboard inspects loose files and queries `smolagents` via LM Studio. Zero files are altered.
2. **Review Rationale & Collisions**: The UI color-codes each proposed category (`Documents`, `Images`, `Code`, `Archives`, etc.) and displays the model's classification rationale and collision resolutions.
3. **Explicit Approval Gate**: A confirmation modal details the safety checklist (0 files deleted, 0 files overwritten). Execution only proceeds upon explicit user confirmation.
4. **Safe One-Click Undo**: Regret an organization? Click "Undo this Move" to instantly restore files to their exact original root locations.

---

## 🛠️ Tools & Technologies Used

- **Python 3.11 & FastAPI**: High-performance backend engine with Pydantic validation.
- **Hugging Face `smolagents` (`ToolCallingAgent`)**: Narrowly scoped, typed tool calling.
- **LM Studio**: OpenAI-compatible local inference API running `Qwen2.5-7B-Instruct` (GGUF `Q4_K_M`) on consumer hardware (NVIDIA RTX 5050 Laptop GPU / 8 GB VRAM).
- **React 19 & TypeScript**: Responsive dashboard interface with nature-inspired forest green aesthetics (`#0a130e`) and soft lime accents (`#84cc16`).
- **Vite 6**: Client build tooling and reverse-proxy.
- **lucide-react**: Lightweight icon set.
- **Podman**: Rootless, containerized deployment workflow (`infra/compose.yaml`).
- **pytest**: 28 automated unit, API, agent, and security tests.

---

## 🧠 Transparent Offline Fallback

A key requirement of SlothDesk is honesty:
- When LM Studio is running, the dashboard displays **Local AI: qwen2.5-7b-instruct** with active tool reasoning.
- When LM Studio is offline, SlothDesk automatically engages its **deterministic rule fallback engine**.
- **SlothDesk never falsely claims the AI model was used when the fallback was active.**

---

## 🤖 AI Agent Session Transcript

This application was implemented and tested pair-programming with Antigravity. To inspect the full, unedited developer trajectory and prompt history, view the embedded agent session below:

{% agent_session 88a3c0ba-b758-4403-9da0-ffc6214a38a5 %}

---

## 🔗 Repository & Code

- **GitHub Repository**: [https://github.com/Ani0811/slothdesk](https://github.com/Ani0811/slothdesk)
- **License**: MIT
- **Architecture Deep-Dive**: [`docs/ARCHITECTURE.md`](https://github.com/Ani0811/slothdesk/blob/main/docs/ARCHITECTURE.md)
- **Security Testing Report**: [`docs/SECURITY_TESTING.md`](https://github.com/Ani0811/slothdesk/blob/main/docs/SECURITY_TESTING.md)
