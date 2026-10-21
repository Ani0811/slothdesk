"""End-to-end verification script for SlothDesk planning, execution, and undo."""

from pathlib import Path
import sys

# Ensure backend is on sys.path
sys.path.insert(0, str(Path("backend").resolve()))

from app.config import settings
from app.tools.scanner import scan_downloads_folder
from app.tools.planner import generate_plan
from app.tools.executor import execute_plan, undo_execution, list_manifests

def verify():
    root = settings.root_path
    print(f"=== SlothDesk End-to-End Verification ===")
    print(f"Testing on root: {root}")

    # 1. Scan
    initial_files = scan_downloads_folder(root)
    print(f"\n[1] Scanned initial root files: {len(initial_files)}")
    for f in initial_files:
        print(f"    - {f.filename} ({f.size_bytes} bytes, ext: {f.extension}, cat: {f.detected_category})")

    # 2. Plan
    plan = generate_plan(root)
    print(f"\n[2] Generated plan ID: {plan.plan_id}")
    print(f"    Inference mode: {plan.model_mode} ({plan.model_name})")
    print(f"    Operations count: {plan.operations_count}")
    print(f"    Collisions resolved: {len(plan.warnings)}")
    for op in plan.operations:
        collision_note = f" [COLLISION RESOLVED -> {op.dest_rel_path}]" if op.has_collision else ""
        print(f"    - {op.source_rel_path} -> {op.dest_rel_path} ({op.category}){collision_note}")

    # Check collision handling
    invoice_ops = [op for op in plan.operations if "invoice" in op.source_rel_path]
    assert len(invoice_ops) == 1
    assert invoice_ops[0].dest_rel_path == "Documents/invoice_october_1.pdf"
    assert invoice_ops[0].has_collision is True
    print("\n[V] Collision verification passed: pre-existing 'Documents/invoice_october.pdf' was protected; new file mapped to 'invoice_october_1.pdf'!")

    # 3. Execute
    exec_res = execute_plan(plan.plan_id, root)
    print(f"\n[3] Executed plan: status={exec_res.status}")
    print(f"    Moved: {exec_res.total_moved}, Skipped: {exec_res.total_skipped}, Failed: {exec_res.total_failed}")
    print(f"    Audit Manifest ID: {exec_res.manifest_id}")
    assert exec_res.total_moved == len(plan.operations)

    # Verify filesystem
    remaining_root_files = scan_downloads_folder(root)
    print(f"    Remaining loose files in root: {len(remaining_root_files)}")
    assert len(remaining_root_files) == 0

    # 4. Undo
    print(f"\n[4] Reverting execution via manifest {exec_res.manifest_id}...")
    undo_res = undo_execution(exec_res.manifest_id, root)
    print(f"    Undo status: {undo_res.status}, Restored count: {undo_res.restored_count}")
    assert undo_res.status == "undone"
    assert undo_res.restored_count == exec_res.total_moved

    # Verify restored filesystem
    restored_root_files = scan_downloads_folder(root)
    print(f"    Restored files in root: {len(restored_root_files)}")
    assert len(restored_root_files) == len(initial_files)

    print("\n=== ALL END-TO-END VERIFICATIONS PASSED CLEANLY! ===")

if __name__ == "__main__":
    verify()
