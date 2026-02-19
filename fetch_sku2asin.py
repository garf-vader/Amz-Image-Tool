import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


def _env_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / ".env"
    return Path(__file__).with_name(".env")


def fetch_sku2asin(output_file: str = "sku2asin.csv") -> str:
    load_dotenv(_env_path())

    dataset_id = os.getenv("DATASET_ID")
    api_id = os.getenv("API_ID")
    api_key = os.getenv("API_KEY")
    if not all((dataset_id, api_id, api_key)):
        raise RuntimeError("Missing credentials in .env file (DATASET_ID, API_ID, API_KEY)")

    auth = requests.post(
        "https://api.domo.com/oauth/token",
        data={"grant_type": "client_credentials", "scope": "data"},
        auth=(api_id, api_key),
        timeout=30,
    )
    auth.raise_for_status()
    token = auth.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token in auth response")

    data = requests.get(
        f"https://api.domo.com/v1/datasets/{dataset_id}/data?includeHeader=true",
        headers={"Authorization": f"bearer {token}"},
        timeout=60,
    )
    data.raise_for_status()

    Path(output_file).write_text(data.text, encoding="utf-8")
    return f"Dataset saved as: {output_file}"


if __name__ == "__main__":
    try:
        print(fetch_sku2asin())
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)
