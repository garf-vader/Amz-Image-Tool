import os
import shutil
from pathlib import Path
from typing import Optional, List
import re
from logic_utils import natural_key


# Accept common image extensions for front images
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def copy_front_images(front_images_dir: str, root_dir: str) -> dict:
    """
    For each model/producttype/colour.<ext> in front_images_dir,
    copy it into model/producttype/colour/MAIN.jpg in root_dir.
    Returns a dict with counts: {'copied': int, 'skipped': int}
    """
    copied = 0
    skipped = 0
    for dirpath, _, files in os.walk(front_images_dir):
        for fname in files:
            name, ext = os.path.splitext(fname)
            if ext.lower() not in IMAGE_EXTS:
                # skip non-image files
                continue
            colour = name.strip()
            rel = os.path.relpath(dirpath, front_images_dir).replace("\\", "/").strip("/")
            target_dir = os.path.join(root_dir, rel, colour)
            
            # If target_dir doesn't exist, create it if the parent leaf exists
            if not os.path.isdir(target_dir):
                leaf_dir = os.path.join(root_dir, rel)
                if not os.path.isdir(leaf_dir):
                    # Leaf doesn't exist, create it
                    os.makedirs(leaf_dir, exist_ok=True)
                # Now create the colour subfolder
                os.makedirs(target_dir, exist_ok=True)
            src = os.path.join(dirpath, fname)
            dst = os.path.join(target_dir, "MAIN.jpg")
            try:
                shutil.copy2(src, dst)
                copied += 1
            except Exception:
                skipped += 1
    return {"copied": copied, "skipped": skipped}


def is_image_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMAGE_EXTS


def find_front_image(folder: Path) -> Optional[Path]:
    """
    Returns the most likely 'front' image in the folder.
    Heuristic: prefers files named 'main', 'front', or '01', else first image by natural sort.
    """
    candidates: List[Path] = [f for f in folder.iterdir() if is_image_file(f)]
    if not candidates:
        return None
    # Prefer files with 'main', 'front', or '01' in name
    preferred = [f for f in candidates if re.search(r"main|front|01", f.stem, re.IGNORECASE)]
    if preferred:
        # If multiple, pick the first by natural sort
        preferred.sort(key=lambda p: natural_key(p.name))
        return preferred[0]
    # Otherwise, pick first by natural sort
    candidates.sort(key=lambda p: natural_key(p.name))
    return candidates[0]
