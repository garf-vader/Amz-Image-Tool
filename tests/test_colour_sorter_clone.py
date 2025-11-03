import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from colour_sorter import run_with_map


def test_clone_image_copies_to_all_colours(tmp_path):
    root = tmp_path / "Root"
    leaf = root / "Model" / "Case"
    leaf.mkdir(parents=True)

    # Create fake image files
    for idx in range(3):
        (leaf / f"{idx:02d}.jpg").write_bytes(b"test")

    col_map = {"Model/Case": ["Red", "Blue"]}
    clone_map = {"Model/Case": "02.jpg"}

    output_path = Path(run_with_map(root, col_map, apply_changes=True, clone_map=clone_map))
    target_leaf = output_path / "Model" / "Case"

    red = target_leaf / "Red"
    blue = target_leaf / "Blue"
    assert (red / "02.jpg").exists()
    assert (blue / "02.jpg").exists()

    # Clean up generated output to avoid leaking directories between tests
    if output_path.exists():
        for dirpath, dirnames, filenames in os.walk(output_path, topdown=False):
            for fname in filenames:
                Path(dirpath, fname).unlink(missing_ok=True)
            for d in dirnames:
                Path(dirpath, d).rmdir()
        output_path.rmdir()
