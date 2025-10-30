#!/usr/bin/env python3
"""
pt_order.py — fast + safe PT renamer

Exposes:
    run_with_map(root, pt_map, apply_changes=True, *,
                 dry_run_log=True, allow_parallel=True) -> int

- root: str | Path to the project root
- pt_map: dict[str, list[int]] where keys are base folders (e.g. "Brand/Model/VintageWallet")
         relative to root (POSIX '/'). Values map each file at original index i
         to its PT number (zero-based); we rename to PT{mapping[i]+2}.
- apply_changes: if False, dry-run (no mutations).
- dry_run_log: if True, prints what would happen in dry-run.
- allow_parallel: if True, plans each leaf concurrently (renames still per-leaf).

Perf notes:
- Uses os.walk/scandir for fewer syscalls.
- Compiled regex for natural sort.
- Avoids Path object churn inside tight loops.
"""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

APPLY_CHANGES_DEFAULT = True
INCLUDE_HIDDEN = False
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

# ---------- fast natural sort ----------
_DIGIT_RE = re.compile(r"(\d+)")

def _natural_key(name: str):
    parts = _DIGIT_RE.split(name)
    # int for digit runs, lowercased str otherwise
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)

# ---------- fast image listing ----------
def _list_images(dirpath: str) -> List[str]:
    try:
        with os.scandir(dirpath) as it:
            files = [
                e.name
                for e in it
                if e.is_file()
                and (INCLUDE_HIDDEN or not e.name.startswith("."))
                and os.path.splitext(e.name)[1].lower() in IMAGE_EXTS
            ]
    except FileNotFoundError:
        return []
    files.sort(key=_natural_key)
    return files

# ---------- leaf discovery ----------
def _find_leaf_dirs(base: str) -> List[str]:
    """Return all 'leaf' dirs under base. If base itself has no subdirs, return [base]."""
    base = os.path.normpath(base)
    if not os.path.isdir(base):
        return []
    leaves: List[str] = []
    has_subdir = False
    for dirpath, dirnames, _ in os.walk(base):
        # filter-out hidden dirs early if we don't include hidden files
        if not INCLUDE_HIDDEN:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if dirnames:
            has_subdir = True
        else:
            leaves.append(os.path.normpath(dirpath))
    if not has_subdir:
        leaves = [base]  # base is already a leaf
    # stable order by natural key on path
    leaves.sort(key=lambda p: _natural_key(p.replace("\\", "/")))
    return leaves

def _width_from_mapping(mapping: List[int]) -> int:
    m = max(mapping) if mapping else 0
    return max(2, len(str(m + 2)))  # consider +2 offset

def _plan_pairs_for_leaf(root: str, leaf: str, mapping: List[int]) -> List[Tuple[str, str]]:
    files = _list_images(leaf)
    if not files:
        return []
    if len(files) < len(mapping):
        rel = os.path.relpath(leaf, root).replace("\\", "/")
        raise RuntimeError(
            f"Leaf '{rel}' has fewer files ({len(files)}) than mapping length ({len(mapping)})."
        )
    width = _width_from_mapping(mapping)
    pairs: List[Tuple[str, str]] = []
    for i, fname in enumerate(files[:len(mapping)]):
        src = os.path.join(leaf, fname)
        new_num = mapping[i] + 2
        base, ext = os.path.splitext(fname)
        dst = os.path.join(leaf, f"PT{new_num:0{width}d}{ext.lower()}")
        if src != dst:
            pairs.append((src, dst))
    # Ensure uniqueness of targets
    target_names = [os.path.basename(d) for _, d in pairs]
    if len(target_names) != len(set(target_names)):
        rel = os.path.relpath(leaf, root).replace("\\", "/")
        raise RuntimeError(f"Duplicate target names in '{rel}'. Check mapping.")
    return pairs

def _two_phase_rename(pairs: List[Tuple[str, str]], apply: bool, log: bool):
    """Copy renamed files to Outputs/timestamp instead of renaming in place."""
    if not pairs:
        return
    from datetime import datetime
    import shutil
    import os
    script_dir = os.path.dirname(__file__)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # Get the root argument from the caller (run_with_map)
    import inspect
    frame = inspect.currentframe()
    while frame:
        if 'root' in frame.f_locals:
            input_root = frame.f_locals['root']
            break
        frame = frame.f_back
    else:
        input_root = None
    if input_root is None:
        raise RuntimeError("Could not determine input root for output structure.")
    input_root = os.path.abspath(str(input_root))
    output_root = os.path.join(script_dir, "Outputs", timestamp)
    os.makedirs(output_root, exist_ok=True)
    for src, final_dst in pairs:
        # Preserve full input structure under Outputs/timestamp
        rel_path = os.path.relpath(src, input_root)
        out_dir = os.path.join(output_root, os.path.dirname(rel_path))
        os.makedirs(out_dir, exist_ok=True)
        dst_name = os.path.basename(final_dst)
        out_path = os.path.join(out_dir, dst_name)
        shutil.copy2(src, out_path)

def _norm_map_keys(pt_map: Dict[str, List[int]]) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {}
    for k, v in pt_map.items():
        key = Path(str(k)).as_posix().strip("/")
        if key and isinstance(v, list) and all(isinstance(x, int) for x in v):
            out[key] = v
    return out

def run_with_map(
    root: str | Path,
    pt_map: Dict[str, List[int]],
    apply_changes: bool = APPLY_CHANGES_DEFAULT,
    *,
    dry_run_log: bool = True,
    allow_parallel: bool = True,
) -> int:
    """
    Returns: output folder path.
    """
    root_path = Path(root).resolve()
    root_str = str(root_path)
    norm = _norm_map_keys(pt_map)

    # Collect all (leaf, mapping) tasks up-front (cheap & parallelizable)
    tasks: List[Tuple[str, List[int]]] = []
    for rel_key, mapping in sorted(norm.items(), key=lambda kv: kv[0].lower()):
        base = (root_path / Path(rel_key)).resolve()
        # security: ensure base within root
        try:
            base.relative_to(root_path)
        except Exception:
            continue
        if not base.is_dir():
            continue
        for leaf in _find_leaf_dirs(str(base)):
            tasks.append((leaf, mapping))

    # Plan all pairs (optionally in parallel)
    results: List[Tuple[str, List[Tuple[str, str]]]] = []
    if allow_parallel and len(tasks) > 1:
        # small pool; planning does scandir + list ops (IO bound)
        with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as ex:
            futs = {ex.submit(_plan_pairs_for_leaf, root_str, leaf, mapping): leaf for leaf, mapping in tasks}
            for fut in as_completed(futs):
                leaf = futs[fut]
                pairs = fut.result()
                if pairs:
                    results.append((leaf, pairs))
    else:
        for leaf, mapping in tasks:
            pairs = _plan_pairs_for_leaf(root_str, leaf, mapping)
            if pairs:
                results.append((leaf, pairs))

    # Perform renames per-leaf (sequential keeps it simple/safe)
    from datetime import datetime
    import os
    script_dir = os.path.dirname(__file__)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root = os.path.join(script_dir, "Outputs", timestamp)
    acted = 0
    for leaf, pairs in results:
        _two_phase_rename(pairs, apply=bool(apply_changes), log=dry_run_log)
        acted += 1
    return output_root
