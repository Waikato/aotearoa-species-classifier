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

srcpath_coredata = "data/01_species_14991_coredata.json"
srcpath_wikidata = "data/00_species_14991_wikidata.json"
tgtpath = "data/02_species_14991_namesdata.json"


#
# main function
#


if __name__ == "__main__":
    # Load the JSON file
    with open(srcpath_coredata, "r") as file:
        coredata = json.load(file)
    with open(srcpath_wikidata, "r") as file:
        wikidata = json.load(file)

    # prepare namesdata in desired format
    namesdata = {}
    num_wikipedia_links = 0
    num_common_names = 0
    for key in tqdm(coredata.keys()):
        gbif_names = coredata[key]['gbif_vernacular_response']
        gbif_names = [{'vernacularName': namedict['vernacularName'], 'language': namedict['language']} for namedict in gbif_names if namedict['language'] in ['eng', 'mri']]
        wikipedia_url = wikidata[key]['eng']['canonicalurl'] if wikidata[key]['eng'] else ''
        mri_wikipedia_url = wikidata[key]['mri']['canonicalurl'] if wikidata[key]['mri'] else ''
        preferred_common_name = ''
        if coredata[key]['inat_results'] and coredata[key]['inat_results']['results']:
            if ('wikipedia_url' in coredata[key]['inat_results']['results'][0] and
                    coredata[key]['inat_results']['results'][0]['wikipedia_url']):
                wikipedia_url = coredata[key]['inat_results']['results'][0]['wikipedia_url']
                num_wikipedia_links += 1

            if ('preferred_common_name' in coredata[key]['inat_results']['results'][0] and
                    coredata[key]['inat_results']['results'][0]['preferred_common_name']):
                preferred_common_name = coredata[key]['inat_results']['results'][0]['preferred_common_name']
                num_common_names += 1

        namesdata[key] = {
            'scientific_name': coredata[key]['scientific_name'],
            'gbif_names': gbif_names,
            'eng': {
                'wikipedia_url': wikipedia_url,
            },
            'mri': {
                'wikipedia_url': mri_wikipedia_url,
            },
            'preferred_common_name': preferred_common_name
        }

    # save the results
    print(
        f"saving dict with {len(namesdata.keys())} entries to {tgtpath}... found {num_wikipedia_links} wikipedia links and {num_common_names} inaturalist common names.")
    with open(tgtpath, 'w') as json_file:
        json.dump(namesdata, json_file)
    print("done!")

