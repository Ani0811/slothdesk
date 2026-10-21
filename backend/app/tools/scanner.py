"""Scanner and filesystem safety validation module for SlothDesk."""

import hashlib
import os
from pathlib import Path
from typing import List, Optional, Tuple
from fastapi import HTTPException

from app.schemas import FileItem, ALLOWED_CATEGORIES

# Common extension to category mapping
EXTENSION_CATEGORY_MAP = {
    # Documents
    ".pdf": "Documents",
    ".docx": "Documents",
    ".doc": "Documents",
    ".txt": "Documents",
    ".md": "Documents",
    ".markdown": "Documents",
    ".rtf": "Documents",
    ".odt": "Documents",
    ".xlsx": "Documents",
    ".xls": "Documents",
    ".pptx": "Documents",
    ".ppt": "Documents",
    ".csv": "Documents",
    ".tsv": "Documents",
    ".epub": "Documents",
    ".pages": "Documents",
    ".numbers": "Documents",
    ".key": "Documents",
    # Images
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
    ".webp": "Images",
    ".svg": "Images",
    ".bmp": "Images",
    ".ico": "Images",
    ".tiff": "Images",
    ".tif": "Images",
    ".raw": "Images",
    ".heic": "Images",
    ".psd": "Images",
    ".ai": "Images",
    # Videos
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".avi": "Videos",
    ".mov": "Videos",
    ".wmv": "Videos",
    ".flv": "Videos",
    ".webm": "Videos",
    ".m4v": "Videos",
    ".mpeg": "Videos",
    ".mpg": "Videos",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".aac": "Audio",
    ".ogg": "Audio",
    ".m4a": "Audio",
    ".wma": "Audio",
    ".aiff": "Audio",
    ".opus": "Audio",
    # Archives
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".tar.gz": "Archives",
    ".tgz": "Archives",
    ".7z": "Archives",
    ".rar": "Archives",
    ".bz2": "Archives",
    ".xz": "Archives",
    ".dmg": "Archives",
    ".iso": "Archives",
    # Code
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".jsx": "Code",
    ".tsx": "Code",
    ".html": "Code",
    ".css": "Code",
    ".json": "Code",
    ".yaml": "Code",
    ".yml": "Code",
    ".sh": "Code",
    ".bat": "Code",
    ".ps1": "Code",
    ".rs": "Code",
    ".go": "Code",
    ".c": "Code",
    ".cpp": "Code",
    ".h": "Code",
    ".hpp": "Code",
    ".java": "Code",
    ".sql": "Code",
    ".rb": "Code",
    ".php": "Code",
    ".xml": "Code",
    ".toml": "Code",
    ".dockerfile": "Code",
}


def classify_by_extension(filename: str) -> str:
    """Deterministically classify a file based on its extension."""
    ext = Path(filename).suffix.lower()
    return EXTENSION_CATEGORY_MAP.get(ext, "Other")


def compute_file_sha256(path: Path) -> str:
    """Compute the SHA-256 hash of a file efficiently in chunks."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def validate_path_safety(rel_path: str, root_path: Path) -> Tuple[bool, str, Optional[Path]]:
    """
    Strictly validate a relative path against root escape, directory traversal,
    absolute paths, and symlink attempts.

    Returns:
        (is_valid, error_message, resolved_path)
    """
    if not rel_path or not rel_path.strip():
        return False, "Path cannot be empty", None

    clean_rel = rel_path.strip().replace("\\", "/")

    # Reject leading slashes or Windows drive indicators
    if clean_rel.startswith("/") or (len(clean_rel) > 1 and clean_rel[1] == ":"):
        return False, f"Absolute paths are rejected: {rel_path}", None

    # Reject traversal tokens
    parts = clean_rel.split("/")
    if ".." in parts:
        return False, f"Path traversal ('..') is prohibited: {rel_path}", None

    resolved_root = root_path.resolve()
    target_candidate = (resolved_root / clean_rel).resolve()

    # Verify containment within root
    try:
        # Raises ValueError if target_candidate is not within resolved_root
        target_candidate.relative_to(resolved_root)
    except ValueError:
        return False, f"Path escapes configured root: {rel_path}", None

    # Check for symlinks along the resolved path
    curr = target_candidate
    while curr != resolved_root and curr != curr.parent:
        if curr.is_symlink() or os.path.islink(curr):
            return False, f"Symlinks are prohibited: {rel_path}", None
        curr = curr.parent

    return True, "", target_candidate


def scan_downloads_folder(root_path: Path) -> List[FileItem]:
    """
    Scans only files directly inside root_path.
    Ignores hidden files, metadata folders, and does not reorganize existing subfolders.
    """
    items: List[FileItem] = []
    if not root_path.exists() or not root_path.is_dir():
        return items

    for entry in os.scandir(root_path):
        name = entry.name

        # Ignore hidden files or internal metadata folders
        if name.startswith(".") or name.startswith("~") or name == "Thumbs.db":
            continue

        # Skip subdirectories (we only organize direct files in the root folder)
        if entry.is_dir(follow_symlinks=False):
            continue

        # Strictly reject symlinks
        if entry.is_symlink():
            continue

        file_path = Path(entry.path)
        try:
            stat = entry.stat(follow_symlinks=False)
            size = stat.st_size
            mtime = stat.st_mtime
            ext = file_path.suffix.lower()
            sha256 = compute_file_sha256(file_path)
            category = classify_by_extension(name)

            items.append(
                FileItem(
                    filename=name,
                    relative_path=name,
                    size_bytes=size,
                    extension=ext,
                    mtime=mtime,
                    sha256=sha256,
                    detected_category=category,
                )
            )
        except (OSError, PermissionError):
            continue

    # Sort stably by filename
    items.sort(key=lambda x: x.filename.lower())
    return items
