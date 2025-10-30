import os
import requests
from dotenv import load_dotenv

# === STEP 1: Your credentials ===
load_dotenv()
DATASET_ID = os.getenv("DATASET_ID")
API_ID = os.getenv("API_ID")
API_KEY = os.getenv("API_KEY")

# === STEP 2: Get OAuth token ===
auth_url = "https://api.domo.com/oauth/token"
data = {
    "grant_type": "client_credentials",
    "scope": "data"
}
auth_response = requests.post(auth_url, data=data, auth=(API_ID, API_KEY))
access_token = auth_response.json()["access_token"]

# === STEP 3: Fetch dataset ===
headers = {"Authorization": f"bearer {access_token}"}
data_url = f"https://api.domo.com/v1/datasets/{DATASET_ID}/data?includeHeader=true"
response = requests.get(data_url, headers=headers)

if response.status_code != 200:
    raise Exception(f"Failed to fetch dataset: {response.status_code} - {response.text}")

# === Step 4: Save as CSV file ===
output_file = "sku2asin.csv"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(response.text)

print(f"✅ Dataset saved as: {output_file}")
