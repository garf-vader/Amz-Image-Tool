import os
from pathlib import Path
from colour_sorter import run_with_map as colour_run_with_map
from pt_order import run_with_map as pt_run_with_map
from amz_rename import process_root




import time
script_dir = os.path.dirname(__file__)
input_root = os.path.join(script_dir, "Inputs")
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

# Step 3: Create sku2asin.csv for amz_rename
csv_path = os.path.join(script_dir, "sku2asin.csv")
with open(csv_path, "w", encoding="utf-8") as f:
    f.write("sku,asin\n")
    f.write("Google Pixel 9a VintageWallet Brown,B0F3JG39SM\n")

# Step 4: Run amz_rename on pt_order output
print("Running amz_rename...")
amz_output = process_root(str(pt_output))
if isinstance(amz_output, str):
    amz_output_path = Path(amz_output)
else:
    amz_output_path = amz_output
assert amz_output_path.exists() and amz_output_path.is_dir(), f"No output from amz_rename! Got: {amz_output_path}"
print(f"amz_rename output folder: {amz_output_path}")
print("Integration test completed.")
