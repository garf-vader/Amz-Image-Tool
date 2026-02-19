import os

import requests
from dotenv import load_dotenv


def fetch_sku2asin_csv(output_file: str = "sku2asin.csv") -> str:
    """Fetch sku2asin CSV from Domo and return the written output path."""
    load_dotenv()
    dataset_id = os.getenv("DATASET_ID")
    api_id = os.getenv("API_ID")
    api_key = os.getenv("API_KEY")

    missing = [name for name, value in {
        "DATASET_ID": dataset_id,
        "API_ID": api_id,
        "API_KEY": api_key,
    }.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    auth_url = "https://api.domo.com/oauth/token"
    token_response = requests.post(
        auth_url,
        data={"grant_type": "client_credentials", "scope": "data"},
        auth=(api_id, api_key),
    )
    token_response.raise_for_status()
    access_token = token_response.json()["access_token"]

    headers = {"Authorization": f"bearer {access_token}"}
    data_url = f"https://api.domo.com/v1/datasets/{dataset_id}/data?includeHeader=true"
    response = requests.get(data_url, headers=headers)
    response.raise_for_status()

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(response.text)

    return output_file


if __name__ == "__main__":
    output = fetch_sku2asin_csv()
    print(f"Dataset saved as: {output}")
