# Security Policy — SlothDesk

SlothDesk is built on a core foundational philosophy:
> **Make file organization effortless for the user; do not make filesystem changes effortless for an untrusted AI model.**

## Security Architecture & Threat Model

SlothDesk operates directly on the user's filesystem (specifically the configured Downloads folder). To eliminate the risk of accidental data loss, malicious file manipulation, or model hallucinations causing damage, SlothDesk implements strict multi-layer defense.

### 1. Zero Model Execution Privileges
- **No Code Execution**: SlothDesk never uses `CodeAgent`, Python `exec`/`eval`, shell commands, or dynamic script runners.
- **Narrow Tooling Interface**: The AI agent (`smolagents.ToolCallingAgent`) is provided only read-only metadata helper functions:
  - `get_inventory_file(filename)`: Inspect file size, name, and extension.
  - `get_allowed_categories()`: Read permitted category names.
  - `validate_category(category)`: Test category validity.
- The model has **zero access to the filesystem**, cannot execute moves, cannot delete files, and cannot create directories.

### 2. Strict Scope Containment (`SLOTHDESK_ROOT`)
- SlothDesk enforces strict boundary confinement to `SLOTHDESK_ROOT`.
- **Absolute Path Rejection**: Any path starting with `/` or Windows drive letter (e.g. `C:\`) provided as a relative path parameter is immediately rejected.
- **Path Traversal Rejection**: Paths containing `..`, parent references, or resolving outside the canonical root boundary are aborted with HTTP 400.
- **Symlink Disallowance**: Symbolic links and directory junctions are explicitly rejected during scanning, planning, execution, and undo. SlothDesk will never traverse, move, or recreate a symlink.
- **Internal Metadata Exclusions**: SlothDesk's internal manifest and data directories (e.g. `.slothdesk*`) are strictly ignored during inventory scanning.

### 3. Separation of Planning from Execution
- **Two-Phase Architecture**:
  1. *Planning Phase (`POST /api/plan`)*: Read-only inventory scan and classification. Files are never modified.
  2. *Approval Gate*: The user explicitly reviews all proposed moves, warnings, and collision reports on the dashboard.
  3. *Execution Phase (`POST /api/execute/{plan_id}`)*: Backend independently validates the plan ID, expiration time, source file existence, cryptographic hash (SHA-256), and file modification timestamp before any filesystem move is attempted.
- Frontend safeguards are never trusted by themselves; the backend enforces atomic validation right before each move.

### 4. Overwrite Prevention & Collision Policy
- **Never Delete**: SlothDesk does not have a delete function. Files are only relocated into categorized subdirectories.
- **Never Overwrite**: SlothDesk will never overwrite an existing file. If a destination already exists or multiple source files share a destination name, SlothDesk flags a collision and resolves it deterministically (e.g. `name_1.ext`). If the destination appears after planning, execution skips the move safely.

### 5. Cryptographic State Verification & Expiration
- Every proposed operation stores the source file's SHA-256 hash, size, and modification timestamp at scan time.
- Plans expire after a configurable interval (default: 15 minutes).
- If a file is modified, deleted, or replaced between the planning phase and execution, the executor skips the move to prevent race conditions or moving unexpected content.

### 6. Atomic, Validated Undo System
- Every execution produces an immutable JSON manifest stored in `SLOTHDESK_DATA_DIR`.
- Manifest data is treated as untrusted input: before an undo operation is executed, paths are revalidated for containment, symlink status, and non-collision.
- If the original location has since been re-occupied, SlothDesk halts the restore for that file and reports the condition rather than overwriting.

### 7. Local-First Privacy Guarantee
- All inference is executed locally through LM Studio via `http://localhost:1234/v1` (or container internal bridge).
- No user file contents, filenames, or directory structures are ever transmitted to third-party cloud APIs.
- SlothDesk only inspects filenames, extensions, and metadata—it does not read file contents to determine categorization.

## Reporting Security Issues

If you discover a security vulnerability in SlothDesk, please report it via GitHub Private Vulnerability Reporting or open an issue labeled `security`.
