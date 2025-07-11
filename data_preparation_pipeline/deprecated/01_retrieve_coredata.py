import json
from time import sleep
from os import listdir
from os.path import split, join
from collections import Counter
from utils.csv_tools import load_csv_file, save_as_csv
from utils.wikidata_requests import (retrieve_inat_taxon_id_response, retrieve_gbif_vernacular_names,
                                     retrieve_inat_response)
import pandas as pd
from tqdm import tqdm

#
# paths
#

srcpath = "data/collected_id.json"
srcpath_speciesdata = "../data/NZ-Species.csv"
tgtpath = "data/01_species_14991_coredata.json"


#
# helper functions
#


def search_inat_for_kingdom(ancestors: list):
    for ancestor in ancestors:
        response = retrieve_inat_response(ancestor)
        sleep(0.5)
        if response['results'][0]['rank'] == 'kingdom':
            return response['results'][0]['name']
    return None


#
# subsection functions
#


def get_inat_keys(coredata):
    no_inat_key_found = []
    for key in tqdm(coredata.keys()):
        if 'gbif' not in coredata[key]:
            coredata[key]['gbif'] = None
        if 'inat' not in coredata[key]:
            coredata[key]['inat'] = None
        gbif_key = coredata[key]['gbif']
        # if the inat key isn't present, attempt to retrieve it
        key_found = False
        if not coredata[key]['inat'] and gbif_key:
            # try to retrieve the inat key from wikidata
            try:
                wikidata_response = retrieve_inat_taxon_id_response(gbif_key)
            except:
                wikidata_response = None
            sleep(0.5)

            if wikidata_response and wikidata_response['results']['bindings'] and \
                    wikidata_response['results']['bindings'][0]:
                try:
                    coredata[key]['inat'] = wikidata_response['results']['bindings'][0]['iNat_Taxon_ID']['value']

                    key_found = True
                except:
                    print(wikidata_response['results']['bindings'][0])
        if not key_found:
            no_inat_key_found.append(coredata[key]["scientific_name"])

    print(f"inat keys retrieved... couldn't find {len(no_inat_key_found)} inat keys...")
    with open("data/01_no_inat_key.json", 'w') as json_file:
        json.dump(no_inat_key_found, json_file)
    return coredata


def get_gbif_and_inat_data(coredata):
    no_response_found = []
    for key in tqdm(coredata.keys()):
        gbif_key = coredata[key]['gbif']
        inat_key = coredata[key]['inat']
        # retrieve GBIF and iNat data
        key_found = False
        if 'gbif_vernacular_response' not in coredata[key] or not coredata[key]['gbif_vernacular_response']:
            coredata[key]['gbif_vernacular_response'] = []
            if gbif_key:
                try:
                    wikidata_response = retrieve_gbif_vernacular_names(gbif_key)
                except:
                    wikidata_response = None
                sleep(0.5)
                if wikidata_response is not None and wikidata_response['results']:
                    coredata[key]['gbif_vernacular_response'].extend(wikidata_response['results'])
                    key_found = True

        if 'inat_results' not in coredata[key] or not coredata[key]['inat_results']:
            coredata[key]['inat_results'] = []
            if inat_key:
                try:
                    coredata[key]['inat_results'] = retrieve_inat_response(inat_key)
                except:
                    coredata[key]['inat_results'] = None
                sleep(0.5)
                if coredata[key]['inat_results']:
                    key_found = True

        if not key_found:
            no_response_found.append(coredata[key]["scientific_name"])

    print(f"gbif and inat responses retrieved... couldn't find {len(no_response_found)} responses...")
    with open("data/01_no_response.json", 'w') as json_file:
        json.dump(no_response_found, json_file)
    return coredata


def get_kingdom(coredata, speciesdata):
    for key in tqdm(coredata.keys()):
        gbif_key = coredata[key]['gbif']
        inat_key = coredata[key]['inat']
        # retrieve kingdom from either GBIF or iNat data
        # first, attempt to retrieve it from GBIF data
        if 'kingdom' not in coredata[key] or not coredata[key]["kingdom"]:
            coredata[key]["kingdom"] = None
            gbif_kingdom = False
            matches = speciesdata[speciesdata['taxonKey'] == gbif_key]
            if not matches.empty:
                kingdom = matches.iloc[0]['kingdom']
                coredata[key]["kingdom"] = kingdom
                gbif_kingdom = True

            # if GBIF couldn't provide a match, attempt to get the kingdom from the iNat API instead
            if not gbif_kingdom and inat_key:
                # operate on coredata[key]['inat_results']...
                # looking for results['results'][0]['ancestor_ids'][1]
                inat_results = coredata[key]['inat_results']
                try:
                    ancestors = inat_results['results'][0]['ancestor_ids']
                    proposed_ancestor = ancestors[1]

                    # check if the ancestor in question is indeed the kingdom
                    proposed_response = retrieve_inat_response(proposed_ancestor)
                    sleep(0.5)
                    if proposed_response['results'][0]['rank'] == 'kingdom':
                        coredata[key]['kingdom'] = proposed_response['results'][0]['name']
                    else:
                        coredata[key]['kingdom'] = search_inat_for_kingdom(ancestors)
                except:
                    print(f"Couldn't process inat results for {coredata[key]['scientific_name']}; got {inat_results}")
    return coredata


#
# main function
#


if __name__ == "__main__":
    # Load the JSON file
    with open(srcpath, "r") as file:
        species_dict = json.load(file)
    # Load species GBIF data
    dtype_dict = {col: 'str' for col in pd.read_csv(srcpath_speciesdata, nrows=1).columns}
    speciesdata = pd.read_csv(srcpath_speciesdata, delimiter='	', dtype=dtype_dict)
    speciesdata = speciesdata.astype({'taxonKey': str})
    print(speciesdata.columns)
    speciesdata = speciesdata.loc[:, ["taxonKey", "kingdom"]].drop_duplicates()
    print(speciesdata.columns)

    #
    # get data
    #
    create_coredata = True
    retrieve_inat = True
    retrieve_responses = True
    retrieve_kingdoms = True

    # create coredata
    if create_coredata:
        # prepare coredata in desired format
        coredata = {str(i): {"scientific_name": key} for i, key in enumerate(species_dict.keys())}
        for key in coredata.keys():
            scientific_name = coredata[key]["scientific_name"]
            keys_dict = species_dict[scientific_name][0]
            if keys_dict:
                coredata[key].update(species_dict[scientific_name][0])
            else:
                try:
                    coredata[key].update(species_dict[scientific_name][1][0][0])
                except:
                    pass

        print(coredata["0"])

        with open(tgtpath, 'w', encoding='utf-8') as json_file:
            json.dump(coredata, json_file)

    # get inat keys
    if retrieve_inat:
        with open(tgtpath, "r") as file:
            coredata = json.load(file)
        coredata = get_inat_keys(coredata)
        print(f"saving dict with {len(coredata.keys())} entries to {tgtpath}...")
        with open(tgtpath, 'w', encoding='utf-8') as json_file:
            json.dump(coredata, json_file)

    # get gbif and inat responses
    if retrieve_responses:
        with open(tgtpath, "r") as file:
            coredata = json.load(file)
        coredata = get_gbif_and_inat_data(coredata)
        print(f"saving dict with {len(coredata.keys())} entries to {tgtpath}...")
        with open(tgtpath, 'w', encoding='utf-8') as json_file:
            json.dump(coredata, json_file)

    # collect kingdoms
    if retrieve_kingdoms:
        with open(tgtpath, "r") as file:
            coredata = json.load(file)
        coredata = get_kingdom(coredata, speciesdata)
        print(f"saving dict with {len(coredata.keys())} entries to {tgtpath}...")
        with open(tgtpath, 'w', encoding='utf-8') as json_file:
            json.dump(coredata, json_file)

    """no_inat_key_found = []
    no_response_found = []
    for key in tqdm(coredata.keys()):
        if 'gbif' not in coredata[key]:
            coredata[key]['gbif'] = None
        if 'inat' not in coredata[key]:
            coredata[key]['inat'] = None
        gbif_key = coredata[key]['gbif']
        # if the inat key isn't present, attempt to retrieve it
        key_found = False
        if not coredata[key]['inat'] and gbif_key:
            wikidata_response = retrieve_inat_taxon_id_response(gbif_key)
            sleep(0.5)
            if wikidata_response is not None and wikidata_response['results']['bindings'] and \
                    wikidata_response['results']['bindings'][0]:
                try:
                    coredata[key]['inat'] = wikidata_response['results']['bindings'][0]['iNat_Taxon_ID']['value']

                    key_found = True
                except:
                    print(wikidata_response['results']['bindings'][0])
        if not key_found:
            no_inat_key_found.append(coredata[key]["scientific_name"])
        inat_key = coredata[key]['inat']

        # retrieve GBIF and iNat data
        key_found = False
        coredata[key]['gbif_vernacular_response'] = []
        if gbif_key:
            wikidata_response = retrieve_gbif_vernacular_names(gbif_key)
            sleep(0.5)
            if wikidata_response is not None and wikidata_response['results']:
                coredata[key]['gbif_vernacular_response'].extend(wikidata_response['results'])
                key_found = True

        coredata[key]['inat_results'] = []
        if inat_key:
            coredata[key]['inat_results'] = retrieve_inat_response(inat_key)
            sleep(0.5)
            if coredata[key]['inat_results']:
                key_found = True

        if not key_found:
            no_response_found.append(coredata[key]["scientific_name"])

        # retrieve kingdom from either GBIF or iNat data
        # first, attempt to retrieve it from GBIF data
        coredata[key]["kingdom"] = None
        gbif_kingdom = False
        matches = speciesdata[speciesdata['taxonKey'] == gbif_key]
        if not matches.empty:
            kingdom = matches.iloc[0]['kingdom']
            coredata[key]["kingdom"] = kingdom
            gbif_kingdom = True

        # if GBIF couldn't provide a match, attempt to get the kingdom from the iNat API instead
        if not gbif_kingdom and inat_key:
            # operate on coredata[key]['inat_results']...
            # looking for results['results'][0]['ancestor_ids'][1]
            inat_results = coredata[key]['inat_results']
            try:
                ancestors = inat_results['results'][0]['ancestor_ids']
                proposed_ancestor = ancestors[1]

                # check if the ancestor in question is indeed the kingdom
                proposed_response = retrieve_inat_response(proposed_ancestor)
                sleep(0.5)
                if proposed_response['results'][0]['rank'] == 'kingdom':
                    coredata[key]['kingdom'] = proposed_response['results'][0]['name']
                else:
                    coredata[key]['kingdom'] = search_inat_for_kingdom(ancestors)
            except:
                print(f"Couldn't process inat results for {coredata[key]['scientific_name']}; got {inat_results}")
        # if key == "100":
        #    break  # for testing!

    # save the results
    print(
        f"saving dict with {len(coredata.keys())} entries to {tgtpath}... couldn't find {len(no_inat_key_found)} inat keys... couldn't find {len(no_response_found)} responses.")
    with open(tgtpath, 'w', encoding='utf-8') as json_file:
        json.dump(coredata, json_file)
    with open("data/01_no_inat_key.json", 'w') as json_file:
        json.dump(no_inat_key_found, json_file)
    with open("data/01_no_response.json", 'w') as json_file:
        json.dump(no_response_found, json_file)"""
    print("done!")
