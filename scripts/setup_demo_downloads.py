"""Helper script to create a synthetic cluttered Downloads folder for demonstration and testing."""

import os
from pathlib import Path


def create_demo_downloads(base_dir: str = "./test_downloads"):
    root = Path(base_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    print(f"Generating synthetic cluttered Downloads folder in: {root}")

    # Documents
    (root / "annual_financial_report_2026.pdf").write_text("PDF content: Q3 Financial Summary")
    (root / "meeting_notes_october.docx").write_text("DOCX content: Strategy & Roadmap")
    (root / "quick_todo_notes.txt").write_text("TXT content: Buy groceries, organize files")

    # Images
    (root / "family_vacation_photo.jpg").write_text("JPEG image binary placeholder")
    (root / "app_architecture_diagram.png").write_text("PNG image binary placeholder")

    # Archives
    (root / "project_backup_v1.zip").write_text("ZIP archive bytes")

    # Code
    (root / "data_pipeline_transform.py").write_text("print('Executing data pipeline')")

    # Unsupported / Unknown extension
    (root / "proprietary_firmware.bin").write_text("BIN binary payload")

    # Collision test setup:
    # 1. An existing file in Documents/
    docs_dir = root / "Documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "invoice_october.pdf").write_text("Existing previous invoice already filed in Documents")

    # 2. A loose file in root that will collide with the above
    (root / "invoice_october.pdf").write_text("New incoming invoice with same name")

    print("Created synthetic demo files:")
    for f in root.iterdir():
        if f.is_file():
            print(f"  - [File] {f.name}")
        elif f.is_dir():
            print(f"  - [Dir]  {f.name}/ ({len(list(f.iterdir()))} files)")

    print("\nSynthetic demo directory ready! Run SlothDesk and click 'Scan & Propose Plan'.")


if __name__ == "__main__":
    create_demo_downloads()
