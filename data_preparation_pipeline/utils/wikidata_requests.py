import requests
from requests.exceptions import RequestException
from retrying import retry
from time import sleep

# URL for the SPARQL endpoint
url = "https://query.wikidata.org/sparql"
gbif_vernacular_url = "https://api.gbif.org/v1/species/"
inat_response_url = "https://api.inaturalist.org/v1/taxa?taxon_id="


@retry(
    stop_max_attempt_number=10,
    wait_fixed=2000,
    retry_on_exception=lambda ex: isinstance(ex, RequestException),
)
def retrieve_inat_taxon_id_response(gbif_id: str):
    # SPARQL query you want to send
    sparql_query = "SELECT ?iNat_Taxon_ID ?ITIS_TSN WHERE {?item wdt:P846 \"" + str(
        gbif_id) + "\".OPTIONAL { ?item wdt:P3151 ?iNat_Taxon_ID. }OPTIONAL { ?item wdt:P815 ?ITIS_TSN. }}"

    # Parameters for the GET request
    params = {
        "format": "json",  # Response format
        "query": sparql_query  # Your SPARQL query
    }

    # Sending the GET request
    try:
        response = requests.get(url, params=params)
    except:
        raise RequestException()

    # Checking the status code of the response
    if response.status_code == 200:
        # Parsing JSON response
        data = response.json()
        # Process the data as needed
        # print(data)
        return data
    else:
        if response.status_code == 429:
            raise RequestException("Too Many Requests")
        elif response.status_code != 200:
            raise RequestException(f"HTTP Error {response.status_code}")


@retry(
    stop_max_attempt_number=10,
    wait_fixed=2000,
    retry_on_exception=lambda ex: isinstance(ex, RequestException),
)
def retrieve_gbif_vernacular_names(gbif_id: str):
    # SPARQL query you want to send
    query = f"{gbif_vernacular_url}{str(gbif_id)}/vernacularNames"

    # Parameters for the GET request
    params = {
        "format": "json",  # Response format
    }

    # Sending the GET request
    try:
        response = requests.get(query, params=params)
    except:
        raise RequestException()

    # Checking the status code of the response
    if response.status_code == 200:
        # Parsing JSON response
        data = response.json()
        return data
    else:
        if response.status_code == 429:
            raise RequestException("Too Many Requests")
        elif response.status_code != 200:
            raise RequestException(f"HTTP Error {response.status_code}")


@retry(
    stop_max_attempt_number=10,
    wait_fixed=2000,
    retry_on_exception=lambda ex: isinstance(ex, RequestException),
)
def retrieve_inat_response(inat_id: str):
    # SPARQL query you want to send
    query = f"{inat_response_url}{str(inat_id)}&order=desc&order_by=observations_count"

    # Parameters for the GET request
    params = {
        "format": "json",  # Response format
    }

    # Sending the GET request
    connection_error = False
    try:
        response = requests.get(query, params=params)
    except:
        raise RequestException()

    # Checking the status code of the response
    if response.status_code == 200:
        # Parsing JSON response
        data = response.json()
        return data
    else:
        if response.status_code == 429:
            raise RequestException("Too Many Requests")
        elif response.status_code != 200:
            raise RequestException(f"HTTP Error {response.status_code}")
