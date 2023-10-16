import json
import wikipediaapi
from time import sleep

from tqdm import tqdm

#
# load species data
#

src = "data/collected_id.json"
tgt = "data/00_species_14991_wikidata.json"

# Load the JSON file
with open(src, "r") as file:
    species_data = json.load(file)

# Access the loaded dictionary
print(len(species_data.keys()))  # Or perform any operations with the dictionary

species_names = list(species_data.keys())

print(len(species_names))
print(species_names[:5])

species_data = {str(i): key for i, key in enumerate(species_data.keys())}

#
# Create dictionary to fill information into
#

class_metadata = {key: {"scientific_name": value, "eng": {}, "mri": {}} for key, value in species_data.items()}
print(class_metadata["0"])
"""for key in species_data.keys():
    scientific_name = species_data[key]
    class_metadata[key] = {
        "eng": {},
        "mri": {}
    }"""

#
# helper functions
#

def collect_wiki_dict(wiki_page: wikipediaapi.WikipediaPage):
    langlinks = list(wiki_page.langlinks.keys())#{key: value.canonicalurl for key, value in wiki_page.langlinks.items()}
    links = list(wiki_page.links.keys())#{key: value.canonicalurl for key, value in wiki_page.links.items()}
    categories = list(wiki_page.categories.keys())#{key: value.canonicalurl for key, value in wiki_page.categories.items()}
    wiki_dict = {
        "pageid": wiki_page.pageid,
        "title": wiki_page.title,
        "summary": wiki_page.summary,
        "text": wiki_page.text,
        "langlinks": langlinks,#wiki_page.langlinks,
        "links": links,#wiki_page.links,
        "categories": categories,#wiki_page.categories,
        "displaytitle": wiki_page.displaytitle,
        "canonicalurl": wiki_page.canonicalurl,
        "ns": wiki_page.ns,
        "contentmodel": wiki_page.contentmodel,
        "pagelanguage": wiki_page.pagelanguage,
        "pagelanguagehtmlcode": wiki_page.pagelanguagehtmlcode,
        "pagelanguagedir": wiki_page.pagelanguagedir,
        "touched": wiki_page.touched,
        "lastrevid": wiki_page.lastrevid,
        "length": wiki_page.length,
        "protection": wiki_page.protection,
        "restrictiontypes": wiki_page.restrictiontypes,
        "watchers": wiki_page.watchers,
        "notificationtimestamp": wiki_page.notificationtimestamp,
        "talkid": wiki_page.talkid,
        "fullurl": wiki_page.fullurl,
        "editurl": wiki_page.editurl,
        "readable": wiki_page.readable,
        "preload": wiki_page.preload
    }
    return wiki_dict

#
# check how many wikipedia pages can be found
#

eng_wiki = wikipediaapi.Wikipedia('en')
mri_wiki = wikipediaapi.Wikipedia('mi')

num_eng_hits, num_mri_hits = 0, 0

print("beginning wiki search...\n")
for key, scientific_name in tqdm(species_data.items(), total=len(species_data)):
    eng_found = False
    mri_found = False

    eng_test = eng_wiki.page(scientific_name)
    mri_test = mri_wiki.page(scientific_name)
    try:
        if eng_test.exists():
            num_eng_hits += 1
            class_metadata[key]['eng'] = collect_wiki_dict(eng_test)
            eng_found = True
        if mri_test.exists():
            num_mri_hits += 1
            class_metadata[key]['mri'] = collect_wiki_dict(mri_test)
            mri_found = True
    except Exception as e:
        print(f"error handling name '{scientific_name}': {e}")
        continue
    sleep(0.1)
    #if key == "2":
    #    print(class_metadata["0"])
print()
print(f"Done! Found {num_eng_hits} English pages, {num_mri_hits} Maori pages...")

# save json
# Save the list of articles as a JSON file
with open(tgt, 'w') as json_file:
    json.dump(class_metadata, json_file)

print("Articles saved as", tgt)
