# SlothDesk 3-Minute Challenge Demo Script

> **Challenge:** DEV Hacktoberfest Open-Source AI Challenge Week 3: *Slow and Steady*  
> **Tagline:** Less sorting. More living.

This script guides a complete 2-to-3 minute video walkthrough or live evaluation of SlothDesk, demonstrating local AI inference, transparent fallback, collision safety, explicit approval gates, and manifest-backed undo.

---

## 1. Demo Setup (30 Seconds)

Generate the synthetic test Downloads directory with cluttered files (including documents, code, images, archives, collisions, and unsupported types):

```bash
# Run the synthetic demo setup script
uv run python scripts/setup_demo_downloads.py
```

Start the application:

```bash
# Terminal 1: Backend
uv run uvicorn app.main:app --app-dir backend --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 2. Step-by-Step Walkthrough (2 Minutes)

### Step 1: The Cluttered Downloads Folder
- **Action**: Open the Downloads folder in your file explorer or look at the **Downloads Inventory** tab in the dashboard.
- **Narrate**: *"Here is our typical chaotic Downloads directory with invoices, screenshots, code snippets, zip files, and an unsupported binary."*
- **Highlight**: Notice the header pill showing the current status:
  - If LM Studio is running with `Qwen2.5-7B-Instruct`: Green indicator displaying **Local AI: qwen2.5-7b-instruct**.
  - If LM Studio is offline: Transparent amber pill indicating **Deterministic Fallback Mode (LM Studio Offline)**. (Never falsely claiming AI inference).

### Step 2: Scan & Propose (Read-Only AI Planning)
- **Action**: Click the **Scan & Propose Plan** button.
- **Narrate**: *"SlothDesk immediately scans top-level files without altering a single byte on disk. It consults our smolagents ToolCallingAgent, which uses local inference to categorize each file into strict allowlisted folders."*
- **Highlight**: 
  - The **Proposed Plan** tab loads with color-coded category badges (`Documents`, `Images`, `Code`, `Archives`).
  - Read the generated rationale for each file.

### Step 3: Collision Detection in Action
- **Narrate**: *"Notice we had two different files that mapped to the same destination name, plus an existing file in `Documents/`. Instead of clobbering, SlothDesk's deterministic collision engine safely resolved them to `_1.pdf` and flagged a clear notice."*

### Step 4: The Unskippable Approval Gate
- **Action**: Click **Review & Approve Execution**.
- **Narrate**: *"The AI model is never allowed to execute filesystem changes on its own. The user must review the exact moves and explicitly click Confirm."*
- **Highlight**: The approval modal details the safety checklist (0 files deleted, 0 files overwritten, reversible via manifest).
- **Action**: Click **Confirm & Execute Moves**.

### Step 5: Execution & Manifest Audit
- **Narrate**: *"The backend revalidates SHA-256 hashes right before moving each file. The organization completes in milliseconds with atomic moves."*
- **Highlight**:
  - The success banner appears showing the unique **Manifest ID** (e.g. `manifest_a1b2c3d4`).
  - Open the folder to show the clean subfolders: `Documents/`, `Images/`, `Code/`, `Archives/`.

### Step 6: Safe Reversibility (Undo)
- **Action**: Click **Undo this Move** in the banner or navigate to the **History & Undo** tab and click **Undo Operation**.
- **Narrate**: *"Changed your mind? Click Undo. SlothDesk uses the immutable JSON manifest to safely restore all files back to their exact original root locations."*
- **Highlight**: The files are instantly restored, and empty category folders are cleaned up.

### Step 7: Automated Tests
- **Action**: In the terminal, run the test suite:
  ```bash
  uv run pytest backend/tests -v
  ```
- **Narrate**: *"All 28 automated tests pass, verifying path traversal rejection, symlink disallowance, tamper detection, and collision handling."*

---

## 3. Preserving & Embedding the Agent Session in DEV

To share the AI agent pair-programming transcript in your DEV challenge submission:

1. Use the **DevRelay** session tool or export the session transcript located at:
   ```text
   C:\Users\basut\.gemini\antigravity-ide\brain\88a3c0ba-b758-4403-9da0-ffc6214a38a5\.system_generated\logs\transcript.jsonl
   ```
2. When publishing your article on DEV via DevRelay (`create_article`), embed the session using the Liquid tag:
   ```markdown
   {% agent_session 88a3c0ba-b758-4403-9da0-ffc6214a38a5 %}
   ```
3. Set `ai_disclosure_level: "some_ai"` to comply with DEV community guidelines.
