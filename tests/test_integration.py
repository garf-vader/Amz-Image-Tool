import os
import sys
from pathlib import Path
import shutil
from datetime import datetime
import time

# Ensure repo root is in sys.path for imports
repo_dir = os.path.dirname(os.path.dirname(__file__))
if repo_dir not in sys.path:
    sys.path.insert(0, repo_dir)

from colour_sorter import run_with_map as colour_run_with_map
from pt_order import run_with_map as pt_run_with_map
from amz_rename import process_root


def test_integration_workflow():
    """Integration test for the full workflow: colour_sorter -> pt_order -> amz_rename.
    
    This test is intended to be run manually when needed, not as part of regular test suite.
    """
    # Use repo root as script_dir
    input_root = os.path.join(repo_dir, "Inputs")
    col_map = {"Google/Pixel 9a/VintageWallet": ["Brown"]}
    pt_map = {"Google/Pixel 9a/VintageWallet/Brown": [0, 5, 4, 2, 3, 1]}

    # Step 1: Run colour_sorter
    print("Running colour_sorter...")
    colour_output = colour_run_with_map(input_root, col_map, apply_changes=True)
    colour_output = Path(colour_output)
    assert colour_output.exists() and colour_output.is_dir(), f"No output from colour_sorter! Got: {colour_output}"
    print(f"colour_sorter output folder: {colour_output}")

    # Wait to ensure a new timestamp for pt_order
    time.sleep(1)

    # Step 2: Run pt_order on colour_sorter output
    print("Running pt_order...")
    pt_output = pt_run_with_map(str(colour_output), pt_map, apply_changes=True, dry_run_log=False, allow_parallel=False)
    pt_output = Path(pt_output)
    assert pt_output.exists() and pt_output.is_dir(), f"No output from pt_order! Got: {pt_output}"
    print(f"pt_order output folder: {pt_output}")

    # Wait to ensure a new timestamp for amz_rename
    time.sleep(1)

    # Step 3: The test fixture `tests/conftest.py` provides `sku2asin.csv` during pytest
    # Step 4: Run amz_rename on pt_order output
    print("Running amz_rename...")
    amz_output = process_root(str(pt_output))
    if isinstance(amz_output, str):
        amz_output_path = Path(amz_output)
    else:
        amz_output_path = amz_output
    assert amz_output_path.exists() and amz_output_path.is_dir(), f"No output from amz_rename! Got: {amz_output_path}"
    print(f"amz_rename output folder: {amz_output_path}")

    # Cleanup: delete all output folders except amz_rename one, rename amz_rename output

    # Find all output folders in repo_dir/Outputs
    outputs_dir = os.path.join(repo_dir, "Outputs")
    if amz_output_path.parent == Path(outputs_dir):
        # Delete all other folders in Outputs except amz_rename output
        for item in Path(outputs_dir).iterdir():
            if item != amz_output_path and item.is_dir():
                shutil.rmtree(item)
        # Rename amz_rename output folder
        date_str = datetime.now().strftime("%Y%m%d")
        renamed_path = amz_output_path.parent / f"{date_str}_Renamed"
        amz_output_path.rename(renamed_path)
        print(f"Renamed amz_rename output folder to: {renamed_path}")
    else:
        print("amz_rename output folder is not in Outputs directory; cleanup skipped.")

    print("Integration test completed.")
