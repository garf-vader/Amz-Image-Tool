import sys
import os
from pathlib import Path

# Allow running this test directly with `python tests/test_front_image.py` by
# ensuring the repository root is on sys.path. When run under pytest this is a
# no-op because pytest already adjusts sys.path.
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from front_image import copy_front_images


def _direct_run():
    """Run front_image on the real Front Images folder and copy into a temp
    folder, then print all old vs new paths and delete the temp folder.
    """
    import tempfile
    import shutil as sh

    front_images_dir = str(repo_root / "Front Images")
    if not os.path.isdir(front_images_dir):
        print(f"ERROR: Front Images folder not found at {front_images_dir}")
        return

    # Create temp_front folder inside tests directory
    temp_front = repo_root / "tests" / "temp_front"
    if temp_front.exists():
        sh.rmtree(temp_front)
    temp_front.mkdir(parents=True, exist_ok=True)

    print(f"Scanning Front Images: {front_images_dir}")
    print(f"Temp output: {temp_front}")
    print("-" * 80)

    # Track mappings: capture file paths before and after
    mappings = []
    
    # Walk the Front Images directory to collect all image files
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    for dirpath, _, files in os.walk(front_images_dir):
        for fname in files:
            name, ext = os.path.splitext(fname)
            if ext.lower() not in IMAGE_EXTS:
                continue
            src_path = os.path.join(dirpath, fname)
            # compute relative path from front_images_dir
            rel = os.path.relpath(dirpath, front_images_dir).replace("\\", "/").strip("/")
            colour = name.strip()
            # Destination in temp_front: rel/colour/MAIN.jpg
            dst_dir = temp_front / rel / colour
            dst_path = dst_dir / "MAIN.jpg"
            mappings.append((src_path, str(dst_path)))

    # Now run the actual copy_front_images into temp_front
    result = copy_front_images(front_images_dir, str(temp_front))

    # Print all mappings
    if mappings:
        for src, dst in mappings:
            print(f"{src} -> {dst}")
    else:
        print("No files found.")

    print("-" * 80)
    print(f"Result: {result}")
    
    # Check if files were actually copied
    if temp_front.exists():
        copied_files = list(temp_front.rglob("*.jpg"))
        print(f"\nActually copied {len(copied_files)} files to temp_front:")
        for f in copied_files:
            print(f"  {f.relative_to(temp_front)}")
    
    # Clean up temp_front
    if temp_front.exists():
        sh.rmtree(temp_front)
        print(f"\nCleaned up: {temp_front}")


if __name__ == '__main__':
    _direct_run()
