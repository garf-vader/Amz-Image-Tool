
#!/usr/bin/env python3
"""
Minimal colour sorter — import-only.

Exposes:
    run_with_map(root, col_map, apply_changes=True) -> int

- root: str | Path to the top-level directory
- col_map: dict[str, list[str]] where keys are leaf paths relative to root (POSIX '/')
- apply_changes: if False, no files are moved (dry-run)

Round-robin assigns images in each leaf folder into subfolders named by the colour
sequence. Hidden files/folders are skipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Iterable
import re
import shutil

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
INCLUDE_HIDDEN = False


def _natural_key(p: Path) -> List[object]:
    parts = re.split(r"(\d+)", p.name)
    out: List[object] = []
    for s in parts:
        out.append(int(s) if s.isdigit() else s.lower())
    return out


def _is_hidden(p: Path) -> bool:
    if INCLUDE_HIDDEN:
        return False
    n = p.name
    return n.startswith(".") or n.startswith("_")


def _iter_images(folder: Path) -> Iterable[Path]:
    for e in sorted(folder.iterdir(), key=_natural_key):
        if e.is_file() and e.suffix.lower() in IMAGE_EXTS and not _is_hidden(e):
            yield e


def _ensure_colour_dirs(folder: Path, colours: List[str]) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    for c in colours:
        name = c.strip()
        if not name:
            continue
        d = folder / name
        d.mkdir(parents=True, exist_ok=True)
        out[name] = d
    return out


def _move_round_robin(files: List[Path], colour_dirs: Dict[str, Path], order: List[str], apply: bool) -> None:
    if not files or not order:
        return
    k = len(order)
    for i, src in enumerate(files):
        colour = order[i % k].strip()
        if not colour:
            continue
        dst_dir = colour_dirs.get(colour)
        if not dst_dir:
            continue
        dst = dst_dir / src.name
        if dst == src:
            continue
        if apply:
            try:
                shutil.move(str(src), str(dst))
            except Exception:
                # swallow errors to keep minimal; caller can validate end state if needed
                pass


def _process(root: Path, col_map: Dict[str, List[str]], apply: bool) -> int:
    acted = 0
    for rel, seq in col_map.items():
        rel_posix = str(rel).strip().strip("/")
        if not rel_posix:
            continue
        colours = [s.strip() for s in seq if str(s).strip()]
        if not colours:
            continue

        folder = (root / Path(rel_posix)).resolve()
        if not folder.is_dir():
            continue

        files = list(_iter_images(folder))
        if not files:
            continue

        dirs = _ensure_colour_dirs(folder, colours)
        _move_round_robin(files, dirs, colours, apply)
        vintage = False
        if vintage:
            _copy_final_to_all_colours(files, dirs, colours, apply)
        acted += 1
    return acted


def run_with_map(root: str | Path, col_map: Dict[str, List[str]], apply_changes: bool = True) -> int:
    root_path = Path(root).resolve()
    norm: Dict[str, List[str]] = {}
    for rel, seq in col_map.items():
        key = Path(str(rel)).as_posix().strip("/")
        if key:
            vals = [str(s).strip() for s in seq if str(s).strip()]
            if vals:
                norm[key] = vals
    return _process(root_path, norm, bool(apply_changes))

def _copy_final_to_all_colours(files: List[Path], colour_dirs: Dict[str, Path], order: List[str], apply: bool) -> None:
    """Copy the last (naturally sorted) image into every colour folder.
    - Assumes round-robin move already happened.
    - Determines the destination folder for the original final image based on its index and the order.
    - Skips copy for folders where the file already exists.
    """
    if not files or not order or not apply:
        return
    k = len(order)
    final_src_name = files[-1].name
    final_idx = len(files) - 1
    assigned_colour = order[final_idx % k].strip()
    src_dir = colour_dirs.get(assigned_colour)
    if src_dir is None:
        return
    src_path = src_dir / final_src_name
    if not src_path.exists():
        # If the move didn't happen or file missing, bail quietly.
        return
    for colour, d in colour_dirs.items():
        dst = d / final_src_name
        if dst.exists():
            continue
        try:
            shutil.copy2(str(src_path), str(dst))
        except Exception:
            # Keep minimal: ignore copy failures silently.
            pass
