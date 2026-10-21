# Security Testing & Verification Report — SlothDesk

This document outlines the security testing methodology, threat scenarios, and automated test coverage implemented in SlothDesk to guarantee safe filesystem manipulation and robust isolation.

## 1. Summary of Automated Security Test Results

All security tests are automated with `pytest` in `backend/tests/test_security.py` and run as part of the continuous integration verification suite:

```bash
uv run pytest backend/tests/test_security.py -v
```

| Test Case | Threat Vector | Mitigation Mechanism | Status |
|:---|:---|:---|:---|
| `test_path_traversal_variations` | Relative directory traversal (`../`, `..\\`, `....//`) | Canonical root containment validation (`Path.relative_to`) | **PASSED** |
| `test_absolute_path_escape` | Absolute root paths (`/etc/passwd`, `C:\Windows\...`) | Explicit rejection of leading `/` and Windows drive colons | **PASSED** |
| `test_symlink_rejection` | Symlink / junction evasion outside managed root | Path traversal check rejects `os.path.islink()` at all levels | **PASSED** (Skipped on non-elevated Win dev mode) |
| `test_hash_tampering_detected` | Source file modified between planning and execution | Cryptographic SHA-256 and byte-size revalidation | **PASSED** |
| `test_malicious_manifest_path_injection_in_undo` | Manifest injection attacking rollback paths | Manifest entries treated as untrusted input; revalidated | **PASSED** |

---

## 2. Threat Scenarios & Implementation Details

### 2.1 Directory Traversal (`..`)
- **Threat**: A crafted filename, malformed plan, or manipulated API payload attempts to write or move files outside the configured `SLOTHDESK_ROOT`.
- **Implementation**:
  ```python
  clean_rel = rel_path.strip().replace("\\", "/")
  parts = clean_rel.split("/")
  if ".." in parts:
      return False, f"Path traversal ('..') is prohibited: {rel_path}", None
  
  resolved_root = root_path.resolve()
  target_candidate = (resolved_root / clean_rel).resolve()
  target_candidate.relative_to(resolved_root) # Raises ValueError on escape
  ```
- **Result**: Any path resolving outside canonical `SLOTHDESK_ROOT` is rejected before any filesystem read or write.

### 2.2 Symlink & Directory Junction Evasion
- **Threat**: An attacker places a symbolic link pointing to a sensitive system folder (e.g. `C:\Users\username\.ssh` or `/etc`), tricking the application into organizing or altering files outside the Downloads scope.
- **Implementation**:
  - `scanner.py` ignores symlinks during directory scanning (`entry.is_symlink()` / `follow_symlinks=False`).
  - `validate_path_safety()` walks the path up to the canonical root and asserts `not curr.is_symlink() and not os.path.islink(curr)`.
- **Result**: Symlinks are never read, moved, followed, or created.

### 2.3 Destination Collisions & Overwrites
- **Threat**: Multiple files propose the same destination name (e.g. `Documents/report.pdf`), or a destination already exists on disk.
- **Implementation**:
  - The planner tracks all claimed destinations in `claimed_destinations: Set[str]`.
  - If `{category}/{filename}` exists on disk OR is already claimed, SlothDesk deterministically resolves a safe suffix: `{stem}_{counter}{suffix}` (e.g. `report_1.pdf`).
  - The executor revalidates right before moving: if `dest_path.exists()`, the move is aborted and recorded in `skipped_moves`.
- **Result**: Existing files are never overwritten.

### 2.4 Stale & Expired Plans (Race Conditions)
- **Threat**: A plan generated hours or days earlier is approved after the underlying filesystem has changed.
- **Implementation**:
  - Plans carry a strict TTL (`PLAN_EXPIRY_SECONDS=900`, 15 minutes).
  - Calling `POST /api/execute/{plan_id}` on an expired plan returns `HTTP 400 Bad Request`.
  - Once executed, the plan is immediately deleted from memory and disk so it cannot be replayed.

### 2.5 File Content Alteration After Planning
- **Threat**: A file is modified or substituted by another process while waiting for user approval.
- **Implementation**:
  - At scan time, SlothDesk computes the SHA-256 hash and file size.
  - At execution time, the executor reads the current file size and SHA-256. If either differs from the planned values, the move is skipped with an explicit safety notice: `"Source file content modified after planning; move skipped."`

### 2.6 Manipulated Manifests During Undo
- **Threat**: An attacker edits an audit manifest JSON file in `SLOTHDESK_DATA_DIR` to insert malicious paths (e.g. `"source_rel_path": "../../target"`).
- **Implementation**:
  - `undo_execution()` never assumes manifest data is valid.
  - Every path in `completed_moves` is passed through `validate_path_safety()`.
  - If the original restore destination is occupied, the restore is refused rather than overwriting the user's file.
