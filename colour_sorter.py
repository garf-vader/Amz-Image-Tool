
#!/usr/bin/env python3
"""
Minimal colour sorter — import-only.

Exposes:
    run_with_map(root, col_map, apply_changes=True, *, clone_map=None) -> str

- root: str | Path to the top-level directory
- col_map: dict[str, list[str]] where keys are leaf paths relative to root (POSIX '/')
- apply_changes: if False, no files are moved (dry-run)
- clone_map: optional dict[str, str] mapping leaf paths to image names to clone into every colour folder

Round-robin assigns images in each leaf folder into subfolders named by the colour
sequence. Hidden files/folders are skipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Iterable, Optional
import re
import shutil
from datetime import datetime

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
INCLUDE_HIDDEN = False


from logic_utils import natural_key


def _is_hidden(p: Path) -> bool:
    if INCLUDE_HIDDEN:
        return False
    n = p.name
    return n.startswith(".") or n.startswith("_")


def _iter_images(folder: Path) -> Iterable[Path]:
    for e in sorted(folder.iterdir(), key=lambda p: natural_key(p.name)):
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


def _process(
    root: Path,
    col_map: Dict[str, List[str]],
    apply: bool,
    clone_map: Optional[Dict[str, str]] = None,
    output_root: Optional[Path] = None,
) -> int:
    # Use provided output folder or create timestamped one
    if output_root is None:
        import os
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        script_dir = Path(os.path.dirname(__file__))
        output_root = script_dir / "Outputs" / timestamp
        output_root.mkdir(parents=True, exist_ok=True)
    acted = 0
    clone_map = clone_map or {}

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

        # Get list of indices to duplicate to all colors
        dup_indices = set(duplicate_indices.get(rel_posix, []))
        
        # Separate normal files from duplicate-to-all files
        # Important: We skip duplicate-to-all images in the color sequence
        normal_files = []
        duplicate_all_files = []
        for i, f in enumerate(files):
            if i in dup_indices:
                duplicate_all_files.append(f)
            else:
                normal_files.append(f)

        # Create output dirs for colours
        out_dirs = {}
        for c in colours:
            name = c.strip()
            if not name:
                continue
            d = output_root / rel_posix / name
            d.mkdir(parents=True, exist_ok=True)
            out_dirs[name] = d

        # Copy normal files round-robin to output dirs
        # These files get their color assignment based on their position in the FILTERED list
        # (skipping the duplicate-to-all images)
        k = len(colours)
        for i, src in enumerate(normal_files):
            colour = colours[i % k].strip()
            if not colour:
                continue
            dst_dir = out_dirs.get(colour)
            if not dst_dir:
                continue
            dst = dst_dir / src.name
            shutil.copy2(src, dst)

        clone_name = clone_map.get(rel_posix)
        if apply and clone_name and out_dirs:
            _clone_selected_to_all_colours(out_dirs, clone_name)
        acted += 1
    return acted


def run_with_map(
    root: str | Path,
    col_map: Dict[str, List[str]],
    apply_changes: bool = True,
    *,
    clone_map: Optional[Dict[str, str]] = None,
) -> str:
    root_path = Path(root).resolve()
    norm: Dict[str, List[str]] = {}
    for rel, seq in col_map.items():
        key = Path(str(rel)).as_posix().strip("/")
        if key:
            vals = [str(s).strip() for s in seq if str(s).strip()]
            if vals:
                norm[key] = vals
    clone_norm: Dict[str, str] = {}
    if clone_map:
        for rel, name in clone_map.items():
            key = Path(str(rel)).as_posix().strip("/")
            if key and name:
                clone_norm[key] = Path(str(name)).name
    # Create output folder path ONCE at the beginning
    from datetime import datetime
    import os
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    script_dir = Path(os.path.dirname(__file__))
    output_root = script_dir / "Outputs" / timestamp
    output_root.mkdir(parents=True, exist_ok=True)
    _process(root_path, norm, bool(apply_changes), clone_norm, output_root)
    return str(output_root)

def _clone_selected_to_all_colours(colour_dirs: Dict[str, Path], selected_name: str) -> None:
    """Copy the selected image into every colour directory if missing."""
    selected_name = Path(selected_name).name
    if not selected_name:
        return

    source_path = None
    for d in colour_dirs.values():
        candidate = d / selected_name
        if candidate.exists():
            source_path = candidate
            break

    if source_path is None:
        return

    for target_dir in colour_dirs.values():
        dst = target_dir / selected_name
        if dst.exists():
            continue
        try:
            shutil.copy2(str(source_path), str(dst))
        except Exception:
            # Ignore copy failures to keep behaviour non-fatal for the UI.
            pass
