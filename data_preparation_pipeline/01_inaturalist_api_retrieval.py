import os
import json
import time
import requests
from tqdm import tqdm
from retrying import retry

# Constants
INAT_URL = "https://api.inaturalist.org/v1/observations/species_counts"
PARAMS = {
    "photos": "true",
    "sounds": "false",
    "taxon_is_active": "true",
    "place_id": 6803,  # New Zealand
    "hrank": "species",
    "quality_grade": "research",
    "include_ancestors": "false",
    "per_page": 500
}

# Retry logic for failed requests (exponential backoff up to 3 attempts)
@retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000, wait_exponential_max=10000)
def fetch_page(page_num):
    params = PARAMS.copy()
    params["page"] = page_num
    response = requests.get(INAT_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch page {page_num}: Status {response.status_code}")
    return response.json()

def retrieve_all_species(target_path, filename=None):
    # Initial request to get total_results
    print("Fetching first page to get total results...")
    first_page = fetch_page(1)
    total_results = first_page["total_results"]
    per_page = PARAMS["per_page"]
    total_pages = (total_results + per_page - 1) // per_page

    print(f"Total results: {total_results}, Pages to fetch: {total_pages}")

    all_results = first_page["results"]
    failed_pages = []

    # Fetch remaining pages with 1-second delay to respect API rate limits
    for page_num in tqdm(range(2, total_pages + 1), desc="Fetching pages"):
        time.sleep(1)  # 1 request per second to stay below 60/minute
        try:
            data = fetch_page(page_num)
            all_results.extend(data["results"])
        except Exception as e:
            print(f"⚠️  Failed to retrieve page {page_num}: {e}")
            failed_pages.append(page_num)

    output_data = {
        "total_results": total_results,
        "per_page": per_page,
        "pages_retrieved": total_pages - len(failed_pages),
        "results": all_results,
        "failed_pages": failed_pages,
    }

    # Create output directory if it doesn't exist
    os.makedirs(target_path, exist_ok=True)

    # Construct file path
    if filename is None:
        filename = "inaturalist_api_all_nz_species.json"
    file_path = os.path.join(target_path, filename)

    # Save to file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Data saved to {file_path}")
    if failed_pages:
        print(f"⚠️  Some pages failed to fetch: {failed_pages}")

if __name__ == "__main__":
    # Example usage
    target_path = "data"
    filename = None  # or set to "custom_name.json"
    retrieve_all_species(target_path, filename)
