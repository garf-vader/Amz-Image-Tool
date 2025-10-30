import os
from colour_sorter import run_with_map

# Set the input folder to Inputs
input_root = os.path.join(os.path.dirname(__file__), "Inputs")
# pt_map key is relative path from input_root
col_map = {"Google/Pixel 9a/VintageWallet": ["Brown"]}

if __name__ == "__main__":
    path = run_with_map(input_root, col_map, apply_changes=True)
    print("colour_sorter test completed.")
