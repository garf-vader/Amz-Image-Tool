import os
from amz_rename import process_root

# Create a minimal sku2asin.csv in the script directory
script_dir = os.path.dirname(__file__)
csv_path = os.path.join(script_dir, "sku2asin.csv")
with open(csv_path, "w", encoding="utf-8") as f:
    f.write("sku,asin\n")
    f.write("Google Pixel 9a VintageWallet Brown,B0F3JG39SM\n")

# Set the input folder to Inputs
input_root = os.path.join(script_dir, "Inputs")

if __name__ == "__main__":
    process_root(input_root)
    print("amz_rename test completed.")
