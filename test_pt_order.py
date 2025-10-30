import os
from pt_order import run_with_map

# Define the input folder and mapping


# Root folder is Inputs
root_folder = os.path.join(os.path.dirname(__file__), "Inputs")
# Mapping key is relative path from Inputs
pt_map = {"Google/Pixel 9a/VintageWallet": [0, 5, 4, 2, 3, 1]}

if __name__ == "__main__":
    # Run pt_order with the mapping
    run_with_map(root_folder, pt_map, apply_changes=True, dry_run_log=False, allow_parallel=False)
    print("pt_order test completed.")
