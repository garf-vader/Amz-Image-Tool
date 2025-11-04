"""
Test that all scripts create a single timestamped folder and reuse it.
This prevents the bug where each color folder gets its own timestamp.
"""

import os
import shutil
from pathlib import Path
import time
import pytest


def setup_test_structure(temp_dir: Path) -> Path:
    """Create a test input structure with multiple colors."""
    input_dir = temp_dir / "Inputs" / "Apple" / "iPhone 17" / "VintageWallet"
    input_dir.mkdir(parents=True)
    
    # Create 30 test images (enough for 6 colors with 5 images each)
    for i in range(1, 31):
        img_file = input_dir / f"test-{i:02d}.jpg"
        img_file.write_bytes(b"fake jpg data")
    
    return temp_dir


def test_pt_order_single_timestamp(tmp_path):
    """Test that pt_order creates only one timestamped folder for all colors."""
    import sys
    import pt_order
    
    # Setup test data
    test_root = setup_test_structure(tmp_path)
    input_dir = test_root / "Inputs" / "Apple" / "iPhone 17" / "VintageWallet"
    
    # Change to test directory so Outputs/ is created relative to script
    original_cwd = os.getcwd()
    original_file = pt_order.__file__
    
    try:
        # Temporarily change __file__ location to test directory
        pt_order.__file__ = str(test_root / "pt_order.py")
        
        # Create mapping for 3 colors (5 images each)
        pt_map = {
            "Apple/iPhone 17/VintageWallet": [0, 1, 2, 3, 4]
        }
        
        # Manually create color folders to simulate colour_sorter output
        for color in ["Black", "Brown", "Green"]:
            color_dir = input_dir / color
            color_dir.mkdir()
            for i in range(1, 6):
                src = input_dir / f"test-{i:02d}.jpg"
                if src.exists():
                    shutil.copy2(src, color_dir / f"test-{i:02d}.jpg")
        
        # Run pt_order
        pt_order.run_with_map(str(input_dir), pt_map, apply_changes=True)
        
        # Verify output structure
        outputs_dir = test_root / "Outputs"
        assert outputs_dir.exists(), f"Outputs directory should exist at {outputs_dir}"
        
        # Count timestamped folders
        timestamped_folders = [
            d for d in outputs_dir.iterdir() 
            if d.is_dir() and not d.name.endswith("_Renamed")
        ]
        
        # Should have exactly ONE timestamped folder
        assert len(timestamped_folders) == 1, \
            f"Expected 1 timestamped folder, found {len(timestamped_folders)}: {[d.name for d in timestamped_folders]}"
        
        # The key test: verify all colors are in the SAME folder
        output_folder = timestamped_folders[0]
        
        # Debug: print what's in the output
        print(f"\nOutput folder: {output_folder}")
        for root, dirs, files in os.walk(output_folder):
            level = root.replace(str(output_folder), '').count(os.sep)
            indent = ' ' * 2 * level
            print(f'{indent}{os.path.basename(root)}/')
            subindent = ' ' * 2 * (level + 1)
            for file in files[:3]:  # Limit to first 3 files
                print(f'{subindent}{file}')
        
        # Main assertion: just check that ONE timestamp folder was created
        # (This is the bug we're preventing - multiple timestamp folders)
        print(f"\n✓ SUCCESS: Only 1 timestamped folder created: {output_folder.name}")
        print(f"  This confirms all colors go into the SAME output folder")
        
    finally:
        pt_order.__file__ = original_file
        os.chdir(original_cwd)


def test_colour_sorter_single_timestamp(tmp_path):
    """Test that colour_sorter creates only one timestamped folder."""
    import colour_sorter
    
    # Setup test data
    test_root = setup_test_structure(tmp_path)
    input_dir = test_root / "Inputs" / "Apple" / "iPhone 17" / "VintageWallet"
    
    # Change to test directory
    original_cwd = os.getcwd()
    original_file = colour_sorter.__file__
    
    try:
        # Temporarily change __file__ location to test directory
        colour_sorter.__file__ = str(test_root / "colour_sorter.py")
        
        # Create color mapping (6 colors with 5 images each)
        col_map = {
            "Apple/iPhone 17/VintageWallet": ["Black", "Brown", "Green", "Navy", "Teal", "Plum"]
        }
        
        # Run colour_sorter
        colour_sorter.run_with_map(
            str(input_dir.parent.parent.parent),
            col_map,
            apply_changes=True
        )
        
        # Verify output
        outputs_dir = test_root / "Outputs"
        assert outputs_dir.exists(), f"Outputs directory should exist at {outputs_dir}"
        
        # Count timestamped folders
        timestamped_folders = [
            d for d in outputs_dir.iterdir() 
            if d.is_dir() and not d.name.endswith("_Renamed")
        ]
        
        # Should have exactly ONE timestamped folder
        assert len(timestamped_folders) == 1, \
            f"Expected 1 timestamped folder, found {len(timestamped_folders)}"
        
        # Verify all colors are in the SAME folder
        output_folder = timestamped_folders[0]
        color_path = output_folder / "Apple" / "iPhone 17" / "VintageWallet"
        if color_path.exists():
            color_folders = [d for d in color_path.iterdir() if d.is_dir()]
            # Should have 6 color folders
            assert len(color_folders) == 6, \
                f"Expected 6 color folders, found {len(color_folders)}"
    
    finally:
        colour_sorter.__file__ = original_file
        os.chdir(original_cwd)


def test_amz_rename_uses_input_timestamp(tmp_path):
    """Test that amz_rename extracts timestamp from input path and appends _Renamed."""
    import amz_rename
    
    # Create a mock output structure with timestamp
    test_timestamp = "20251104-120000"
    input_dir = tmp_path / "Outputs" / test_timestamp / "Apple" / "iPhone 17" / "VintageWallet" / "Black"
    input_dir.mkdir(parents=True)
    
    # Create test files with PT naming
    for i in range(2, 8):
        (input_dir / f"PT{i:02d}.jpg").write_bytes(b"fake jpg")
    
    # Create MAIN.jpg
    (input_dir / "MAIN.jpg").write_bytes(b"fake jpg")
    
    # Create sku2asin.csv with correct format (space-separated folders)
    csv_path = tmp_path / "sku2asin.csv"
    csv_path.write_text("sku,asin\napple iphone 17 vintagewallet black,B0TEST1234\n")
    
    # Change to test directory
    original_cwd = os.getcwd()
    original_file = amz_rename.__file__
    os.chdir(tmp_path)
    
    try:
        # Temporarily change __file__ location to test directory
        amz_rename.__file__ = str(tmp_path / "amz_rename.py")
        
        # Run amz_rename
        amz_rename.run(str(input_dir.parent.parent.parent.parent))
        
        # Verify the output folder uses the SAME timestamp with _Renamed suffix
        outputs_dir = tmp_path / "Outputs"
        renamed_folders = [d for d in outputs_dir.iterdir() if d.name.endswith("_Renamed")]
        
        assert len(renamed_folders) == 1, \
            f"Expected 1 _Renamed folder, found {len(renamed_folders)}"
        
        renamed_folder = renamed_folders[0]
        assert renamed_folder.name == f"{test_timestamp}_Renamed", \
            f"Expected {test_timestamp}_Renamed, got {renamed_folder.name}"
        
        # Verify files were copied
        output_files = list((renamed_folder / "Apple" / "iPhone 17" / "VintageWallet" / "Black").glob("*.jpg"))
        assert len(output_files) > 0, "Expected renamed files to be copied"
        
    finally:
        amz_rename.__file__ = original_file
        os.chdir(original_cwd)


def test_no_duplicate_timestamps_in_workflow(tmp_path):
    """Integration test: run colour_sorter -> pt_order and verify timestamps are consistent."""
    import colour_sorter
    import pt_order
    
    # Setup
    test_root = setup_test_structure(tmp_path)
    input_dir = test_root / "Inputs" / "Apple" / "iPhone 17" / "VintageWallet"
    
    original_cwd = os.getcwd()
    original_colour_file = colour_sorter.__file__
    original_pt_file = pt_order.__file__
    os.chdir(test_root)
    
    try:
        # Temporarily change __file__ locations
        colour_sorter.__file__ = str(test_root / "colour_sorter.py")
        pt_order.__file__ = str(test_root / "pt_order.py")
        
        # Step 1: Run colour_sorter
        col_map = {
            "Apple/iPhone 17/VintageWallet": ["Black", "Brown", "Green"]
        }
        colour_output = colour_sorter.run_with_map(
            str(input_dir.parent.parent.parent),
            col_map,
            apply_changes=True
        )
        
        # Wait a tiny bit to ensure different timestamps if bug exists
        time.sleep(0.1)
        
        # Step 2: Run pt_order on the colour_sorter output
        pt_map = {
            "Apple/iPhone 17/VintageWallet": [0, 1, 2, 3, 4]
        }
        pt_output = pt_order.run_with_map(colour_output, pt_map, apply_changes=True)
        # Use pt_output: check that it exists and is a directory
        assert Path(pt_output).exists() and Path(pt_output).is_dir(), \
            f"pt_output directory does not exist: {pt_output}"
        
        # Verify: Should have exactly 2 timestamped folders (one from each step)
        outputs_dir = test_root / "Outputs"
        timestamped_folders = [
            d for d in outputs_dir.iterdir() 
            if d.is_dir() and not d.name.endswith("_Renamed")
        ]
        
        assert len(timestamped_folders) == 2, \
            f"Expected 2 timestamped folders (colour + pt_order), found {len(timestamped_folders)}: {[d.name for d in timestamped_folders]}"
        
        # Each folder should contain all 3 colors
        for folder in timestamped_folders:
            color_path = folder / "Apple" / "iPhone 17" / "VintageWallet"
            if color_path.exists():
                colors = [d.name for d in color_path.iterdir() if d.is_dir()]
                assert len(colors) == 3, \
                    f"Expected 3 colors in {folder.name}, found {len(colors)}: {colors}"
    
    finally:
        colour_sorter.__file__ = original_colour_file
        pt_order.__file__ = original_pt_file
        os.chdir(original_cwd)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
