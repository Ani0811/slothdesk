---
title: "SlothDesk — Local-First AI Downloads Organizer: Less sorting. More living."
published: false
description: "A local-first AI-powered Downloads organizer with two-phase execution, smolagents, LM Studio inference, and zero overwrites."
tags: devchallenge, hf26challenge, ai, opensource
cover_image: https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/slothdesk_banner.jpg
canonical_url: https://github.com/Ani0811/slothdesk
ai_disclosure_level: some_ai
---

*This is a submission for the [DEV Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges).*

---

![SlothDesk Banner](https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/slothdesk_banner.jpg)

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

## 📸 Application Showcase & Screenshots

### 1. Dashboard Overview
Inspect loose files in the Downloads folder, track storage volume, and verify the local inference engine status at a glance.

![SlothDesk Dashboard Initial View](https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/dashboard_initial.png)

### 2. Read-Only AI Organization Proposal
Clicking **Scan & Propose Plan** triggers `smolagents` via LM Studio. Every file receives a color-coded category badge, destination path preview, model rationale, and automatic collision resolution.

![SlothDesk Proposed Plan](https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/proposed_plan.png)

### 3. Explicit Approval Gate
Zero files are altered until the user explicitly reviews the plan summary and safety checklist, confirming the moves in a dedicated modal dialog.

![SlothDesk Approval Modal](https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/approval_modal.png)

### 4. Downloads Inventory & Cryptographic Hashes
Inspect all top-level files with real-time size metrics, extension detection, and SHA-256 verification hashes.

![SlothDesk Downloads Inventory](https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/downloads_inventory.png)

### 5. Execution History & One-Click Undo
Every move produces an immutable JSON audit manifest. Click **Undo Operation** to instantly restore files back to their exact original root locations.

![SlothDesk History & Undo](https://raw.githubusercontent.com/Ani0811/slothdesk/main/docs/assets/history_undo.png)

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

This application was designed, implemented, and hardened pair-programming with Google Antigravity. To inspect the full, unedited developer trajectory and prompt history, view the embedded agent session below:

<!-- Uncomment below if you have synced your session via DevRelay: -->
<!-- {%% agent_session your_published_session_id %%} -->

### Agent Workflow Trajectory:
- **Architecture & Threat Modeling**: Designed two-phase execution lifecycle separating AI reasoning from filesystem mutations.
- **Safety & Confinement**: Implemented path canonicalization, symlink rejection, and collision-safe renames (_1.ext).
- **Agent Integration**: Harnessed smolagents.ToolCallingAgent with LM Studio (Qwen2.5-7B) and deterministic fallback.
- **Full-Stack Dashboard**: Built React 19 + TypeScript interface with explicit approval modal gate.
- **Testing**: 28 automated tests passing across planner, executor, API, and security suites.

---

## 🔗 Repository & Code

- **GitHub Repository**: [https://github.com/Ani0811/slothdesk](https://github.com/Ani0811/slothdesk)
- **License**: MIT
- **Architecture Deep-Dive**: [`docs/ARCHITECTURE.md`](https://github.com/Ani0811/slothdesk/blob/main/docs/ARCHITECTURE.md)
- **Security Testing Report**: [`docs/SECURITY_TESTING.md`](https://github.com/Ani0811/slothdesk/blob/main/docs/SECURITY_TESTING.md)
- **Demo Walkthrough Script**: [`docs/DEMO_SCRIPT.md`](https://github.com/Ani0811/slothdesk/blob/main/docs/DEMO_SCRIPT.md)
