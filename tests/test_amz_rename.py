import os
from amz_rename import process_root

# Create a minimal sku2asin.csv in the script directory

# Use repo root as script_dir
repo_dir = os.path.dirname(os.path.dirname(__file__))
csv_path = os.path.join(repo_dir, "sku2asin.csv")
with open(csv_path, "w", encoding="utf-8") as f:
    f.write("sku,asin\n")
    f.write("Google Pixel 9a VintageWallet Brown,B0F3JG39SM\n")

# Set the input folder to Inputs in repo root
input_root = os.path.join(repo_dir, "Inputs")

if __name__ == "__main__":
    process_root(input_root)
    print("amz_rename test completed.")
