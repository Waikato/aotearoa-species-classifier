"""
This script tests the viability of using the iNat API directly for retrieving iNat keys, instead of wikidata
"""

import pandas as pd
import requests
from retrying import retry
from tqdm import tqdm

# Paths
INPUT_CSV = "data/20250506_GBIF_species/20250506_GBIF_species.csv"
MATCHES_CSV = "data/matched_gbif_inat_ids.csv"
MISMATCHES_CSV = "data/mismatched_gbif_inat_ids.csv"

# SPARQL endpoint
SPARQL_URL = "https://query.wikidata.org/sparql"

# iNaturalist API base
INAT_API_BASE = "https://api.inaturalist.org/v1/taxa"

@retry(stop_max_attempt_number=10, wait_fixed=2000)
def get_inat_id_from_wikidata(gbif_id):
    sparql_query = f"""
    SELECT ?iNat_Taxon_ID WHERE {{
        ?item wdt:P846 "{gbif_id}".
        OPTIONAL {{ ?item wdt:P3151 ?iNat_Taxon_ID. }}
    }}
    """
    params = {
        "format": "json",
        "query": sparql_query
    }
    response = requests.get(SPARQL_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    bindings = data.get("results", {}).get("bindings", [])
    if bindings:
        result = bindings[0].get("iNat_Taxon_ID", {}).get("value")
        return int(result) if result else None
    return None

@retry(stop_max_attempt_number=10, wait_fixed=2000)
def get_inat_id_from_api(scientific_name):
    query = {"q": scientific_name, "order": "desc", "order_by": "observations_count"}
    response = requests.get(INAT_API_BASE, params=query, timeout=10)
    response.raise_for_status()
    results = response.json().get("results", [])
    if results:
        return results[0].get("id")
    return None

def main():
    df = pd.read_csv(INPUT_CSV, sep='\t')
    match_records = []
    mismatch_records = []
    mismatch_count = 0

    for _, row in tqdm(df.iterrows(), total=len(df)):
        gbif_id = row['taxonKey']
        sci_name = row['scientificName']

        wikidata_id = None
        inat_api_id = None

        try:
            wikidata_id = get_inat_id_from_wikidata(gbif_id)
        except Exception as e:
            pass  # Optional: log or handle errors

        try:
            inat_api_id = get_inat_id_from_api(sci_name)
        except Exception as e:
            pass  # Optional: log or handle errors

        if wikidata_id is not None and inat_api_id is not None:
            if wikidata_id == inat_api_id:
                match_records.append((gbif_id, wikidata_id))
            else:
                mismatch_count += 1
                mismatch_records.append((gbif_id, wikidata_id, inat_api_id))

    # Save results
    match_df = pd.DataFrame(match_records, columns=["GBIF_ID", "iNat_ID"])
    mismatch_df = pd.DataFrame(mismatch_records, columns=["GBIF_ID", "Wikidata_iNat_ID", "iNat_API_ID"])

    match_df.to_csv(MATCHES_CSV, index=False)
    mismatch_df.to_csv(MISMATCHES_CSV, index=False)

    print(f"Total mismatches: {mismatch_count}")

if __name__ == "__main__":
    main()
