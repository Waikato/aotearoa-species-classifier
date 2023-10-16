import json
from os import sep
from tqdm import tqdm
import wikipediaapi
import requests
from utils.wikidata_requests import retrieve_gbif_vernacular_names, retrieve_inat_response
from time import sleep

#
# paths
#

srcpath_wikidata = "data/00_species_14991_wikidata.json"
srcpath_coredata = "data/01_species_14991_coredata.json"
srcpath_namesdata = "data/02_species_14991_namesdata.json"
srcpath_mpidata = "data/03_species_14991_mpidata.json"
tgtpath_metadata = "data/04_species_14991_metadata.json"


def normalize_name(name):
    # Normalize the name by converting to lowercase and removing spaces and hyphens
    return name.strip().lower().replace(" ", "").replace("-", "")


def remove_duplicates(names):
    normalized_names_set = set()
    unique_names = []

    for name in names:
        normalized_name = normalize_name(name)
        if normalized_name not in normalized_names_set:
            normalized_names_set.add(normalized_name)
            unique_names.append(name)

    return unique_names


def capitalize_parts(names):
    capitalized_names = []

    for name in names:
        capitalized_names.append(' '.join([part.capitalize() for part in name.split()]))

    return capitalized_names


def remove_references(summary):
    # Find the position of the "References" heading
    references_index = summary.find("== References ==")

    # If the heading is found, remove everything after it
    if references_index != -1:
        cleaned_summary = summary[:references_index]
    else:
        cleaned_summary = summary

    return cleaned_summary.strip()  # Remove leading/trailing whitespace


def retrieve_wikipedia_summaries(page_name):
    mri_page_name = page_name
    eng_response = eng_wiki.page(page_name)
    sleep(0.25)
    try:
        eng_summary = ""
        mri_summary = ""
        if eng_response.exists():
            eng_summary = eng_response.summary
            lang_links = eng_response.langlinks
            # if link exists to mri page, update mri name to search
            if 'mi' in lang_links.keys():
                mri_page_name = lang_links['mi']
        # get mri name
        mri_response = mri_wiki.page(mri_page_name)
        sleep(0.25)
        if mri_response.exists():
            mri_summary = mri_response.summary
        return eng_summary, mri_summary
    except Exception as e:
        print(f"error handling name '{page_name}': {e}")
        return "", ""



if __name__ == "__main__":
    """
    combine inat and wikidata. 
    Target metadata structure:
    - species key
        - scientific_name
        - preferred_common_name
        - eng
            - common names
            - wikipedia_summary
            - wikipedia_link
        - mri
            - common names
            - wikipedia_summary
            - wikipedia_link
        - unwanted
        - notifiable
        - kingdom
    """
    #
    # load data
    #
    with open(srcpath_wikidata, "r") as file:
        wikidata = json.load(file)
    with open(srcpath_coredata, "r") as file:
        coredata = json.load(file)
    with open(srcpath_namesdata, "r") as file:
        namesdata = json.load(file)
    with open(srcpath_mpidata, "r") as file:
        mpidata = json.load(file)

    #
    # prepare wikipedia api
    #
    eng_wiki = wikipediaapi.Wikipedia('en')
    mri_wiki = wikipediaapi.Wikipedia('mi')

    metadata = {}
    urls_updated = 0  # keep track of the number of times a wikipedia url had to be updated
    for key in tqdm(coredata.keys()):
        metadata[key] = {
            "scientific_name": coredata[key]['scientific_name'],
            "preferred_common_name": namesdata[key]['preferred_common_name'],
            "eng": {
                "common_names": [],
                "wikipedia_summary": wikidata[key]['eng']['summary'] if wikidata[key]['eng'] and 'summary' in wikidata[key]['eng'] else "",  # note that if the namesdata url doesn't match the wikidata url, this should be updated
                "wikipedia_link": namesdata[key]['eng']['wikipedia_url'],
            },
            "mri": {
                "common_names": [],
                "wikipedia_summary": wikidata[key]['mri']['summary'] if wikidata[key]['mri'] and 'summary' in wikidata[key]['mri'] else "",
                "wikipedia_link": namesdata[key]['mri']['wikipedia_url'],
            },
            "unwanted": mpidata[key]['unwanted'],
            "notifiable": mpidata[key]['notifiable'],
            "kingdom": coredata[key]['kingdom']
        }

        #
        # collect names lists and merge them
        #
        gbif_eng_names = [name_dict['vernacularName'] for name_dict in namesdata[key]['gbif_names']
                          if name_dict['language'] == 'eng']

        if metadata[key]['preferred_common_name']:
            gbif_eng_names = [metadata[key]['preferred_common_name']] + gbif_eng_names
        gbif_mri_names = [name_dict['vernacularName'] for name_dict in namesdata[key]['gbif_names']
                          if name_dict['language'] == 'mri']
        eng_names = remove_duplicates(gbif_eng_names)
        mri_names = remove_duplicates(gbif_mri_names)

        #
        # capitalize names
        #
        # capitalize preferred common name
        common_name = metadata[key]['preferred_common_name']
        metadata[key]['preferred_common_name'] = ' '.join([part.capitalize() for part in common_name.split()])

        # capitalize common names
        eng_names = capitalize_parts(eng_names)
        mri_names = capitalize_parts(mri_names)
        metadata[key]['eng']['common_names'] = eng_names
        metadata[key]['mri']['common_names'] = mri_names

        # fill in missing common names where possible
        if not metadata[key]['preferred_common_name'] and metadata[key]['eng']['common_names']:
            metadata[key]['preferred_common_name'] = metadata[key]['eng']['common_names'][0]

        #
        # process wikipedia summaries
        #
        # update wikipedia summary if urls don't match
        if wikidata[key]['eng'] and 'canonicalurl' in wikidata[key]['eng']:
            if metadata[key]['eng']['wikipedia_link'] != wikidata[key]['eng']['canonicalurl']:
                page_name = metadata[key]['eng']['wikipedia_link'].split(sep)[-1]
                eng_summary, mri_summary = retrieve_wikipedia_summaries(page_name)
                metadata[key]['eng']['wikipedia_summary'] = eng_summary
                metadata[key]['mri']['wikipedia_summary'] = mri_summary
                urls_updated += 1

        # clean up summaries
        metadata[key]['eng']['wikipedia_summary'] = remove_references(metadata[key]['eng']['wikipedia_summary'])
        metadata[key]['mri']['wikipedia_summary'] = remove_references(metadata[key]['mri']['wikipedia_summary'])

    # save the results
    print(
        f"saving dict with {len(metadata.keys())} entries to {tgtpath_metadata}... {urls_updated} Wikipedia urls "
        f"and summaries updated.")
    with open(tgtpath_metadata, 'w') as json_file:
        json.dump(metadata, json_file)
    print("done!")

