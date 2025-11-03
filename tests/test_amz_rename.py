import os
from amz_rename import process_root

# Use repo root as script_dir
repo_dir = os.path.dirname(os.path.dirname(__file__))
input_root = os.path.join(repo_dir, "Inputs")


def test_amz_rename_smoke():
    """Smoke test that amz_rename.process_root is callable.
    
    Note: Full rename requires sku2asin.csv and test fixtures in Inputs/.
    This test only verifies the function exists and is callable.
    """
    assert callable(process_root)


if __name__ == "__main__":
    # Only create test CSV when running directly (not during pytest collection)
    csv_path = os.path.join(repo_dir, "sku2asin.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("sku,asin\n")
        f.write("Google Pixel 9a VintageWallet Brown,B0F3JG39SM\n")
    
    process_root(input_root)
    print("amz_rename test completed.")
