#!/usr/bin/env python3
"""
ui_utils.py — shared utilities for the image UIs

This module centralises constants, helper functions and small utilities that are
used by both the colour planner UI and the reorder UI. Import from here instead
of duplicating code across scripts.
"""

from __future__ import annotations

import os
import re
import hashlib
from typing import Iterable, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PIL import Image

# --------- shared constants ---------
IMAGE_EXTS: set[str] = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
THUMB_SIZE: tuple[int, int] = (80, 80)
ROW_PAD_Y: int = 6

# Common target folder names used by the reorder phase
TARGET_FOLDER_NAMES = ["VintageWallet", "ShinyWallet", "VintWallet", "ShinyCase"]

# Reorder UI visual constants (exposed so UIs don't redefine them)
INSERT_LINE_PAD: int = 3       # gap before/after row for the insertion line
INSERT_LINE_HEIGHT: int = 4    # thickness of the insertion line


# --------- generic helpers ---------
def natural_key(name: str):
    """Return a key for natural sorting where numbers are ordered numerically."""
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", name)]


def pastel_for_name(name: str) -> str:
    """Deterministic pastel colour for a given text label (hex string)."""
    if not name:
        return "#dddddd"
    h = int(hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:6], 16)
    r = (h & 0xFF0000) >> 16
    g = (h & 0x00FF00) >> 8
    b = (h & 0x0000FF)
    # lift toward white for pastel
    r = (r + 255) // 2
    g = (g + 255) // 2
    b = (b + 255) // 2
    return f"#{r:02x}{g:02x}{b:02x}"


class ThumbItem:
    """Represents an image file plus some UI metadata (e.g., original index)."""

    def __init__(self, path: str, orig_index: int):
        self.path = path
        self.name = os.path.basename(path)
        self.orig_index = orig_index
        self.thumb = None  # lazily created PhotoImage
        # Optional field used by the colour planner
        self.assigned_color: str = ""

    def load_thumb(self):
        """Load and cache a Qt-compatible thumbnail from disk."""
        if self.thumb is None:
            img = Image.open(self.path)
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            mode = img.mode
            if mode not in ("RGB", "RGBA"):
                if mode in ("LA", "P"):
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")
                mode = img.mode

            if mode == "RGBA":
                data = img.tobytes("raw", "RGBA")
                qimage = QImage(
                    data,
                    img.width,
                    img.height,
                    img.width * 4,
                    QImage.Format_RGBA8888,
                )
            else:  # RGB
                if mode != "RGB":
                    img = img.convert("RGB")
                data = img.tobytes("raw", "RGB")
                qimage = QImage(
                    data,
                    img.width,
                    img.height,
                    img.width * 3,
                    QImage.Format_RGB888,
                )

            pixmap = QPixmap.fromImage(qimage)
            if not pixmap.isNull():
                self.thumb = pixmap.scaled(
                    THUMB_SIZE[0],
                    THUMB_SIZE[1],
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            else:
                self.thumb = QPixmap()
        return self.thumb


# --------- filesystem helpers ---------
def find_leaf_dirs(top_dir: str) -> list[str]:
    """Return all leaf directories under top_dir that contain at least one image (natural-sorted)."""
    results: list[str] = []
    for root, dirs, files in os.walk(top_dir):
        if not dirs:  # leaf = no subdirectories
            if any(os.path.splitext(f)[1].lower() in IMAGE_EXTS for f in files):
                results.append(root)
    # natural sort by relative path
    results.sort(key=lambda p: natural_key(os.path.relpath(p, top_dir)))
    return results


def has_images(path: str) -> bool:
    """True if directory contains at least one supported image file."""
    try:
        for f in os.listdir(path):
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS:
                return True
    except FileNotFoundError:
        return False
    return False


# Minimal get_output_root helper used by UI phases
def get_output_root(base_dir: str) -> str:
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Outputs", timestamp)
        os.makedirs(output_root, exist_ok=True)
        return output_root
    except Exception:
        return os.getcwd()


def pt_order_path(script_file: Optional[str] = None) -> str:
    """Location of pt_order.json beside the given script (or CWD if unknown)."""
    try:
        script_dir = os.path.dirname(os.path.abspath(script_file if script_file else __file__))
    except Exception:
        script_dir = os.getcwd()
    return os.path.join(script_dir, "pt_order.json")


def folder_key(path: str, segments: int = 3, drop_last: bool = True) -> str:
    """
    Build a label like 'Apple/iPhone 17/VintageWallet' from a path.
    - drop_last=True: discard the final segment (e.g., the colour folder 'Teal')
    - segments=3: keep last 3 segments after dropping the last
    """
    p = os.path.normpath(path)
    parts = [part for part in p.split(os.sep) if part]
    if drop_last and parts:
        parts = parts[:-1]
    if segments is not None and len(parts) > segments:
        parts = parts[-segments:]
    return "/".join(parts)
    
