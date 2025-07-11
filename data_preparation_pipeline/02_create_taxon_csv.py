"""
Create a CSV file from the main inat json file containing for each species: taxon rank, taxon parents, and number of observations.
"""
import json
from tqdm import tqdm
from pathlib import Path
import pandas as pd


def create_species_data_csv(data_src):
    with open(str(data_src), 'r') as f:
        data = json.load(f)
    # dataframe stats
    print("\n---\nData json stats:")
    print(len(data))
    print(data.keys())
    print(len(data['results']))
    print(data['results'][0].keys())
    print(data['results'][0]['taxon'].keys())

    # collect dataframe
    inat_ids, names, cnames, ranks, counts, obs_counts, parent_ids = [], [], [], [], [], [], []
    for i in tqdm(range(len(data['results']))):
        inat_ids.append(data['results'][i]['taxon']['id'])
        names.append(data['results'][i]['taxon']['name'])
        ranks.append(data['results'][i]['taxon']['rank'])
        counts.append(data['results'][i]['count'])
        obs_counts.append(data['results'][i]['taxon']['observations_count'])
        parent_ids.append(data['results'][i]['taxon']['parent_id'])
        if 'preferred_common_name' in data['results'][i]['taxon'].keys():
            cnames.append(data['results'][i]['taxon']['preferred_common_name'])
        else:
            cnames.append(None)

    df = pd.DataFrame({
        'id': inat_ids,
        'name': names,
        'preferred_common_name': cnames,
        'taxon': ranks,
        'count': counts,
        'obs_count': obs_counts,
        'parent_id': parent_ids
    })
    print("\n---\nTaxon counts")
    print(len(df))
    print(df['taxon'].value_counts())

    print("\n---\nCounts vs observation counts")
    print(df['count'].describe())
    print(df['obs_count'].describe())

    print("\n---\nAre any hybrids children of included species?")
    parent_ids_of_hybrids = df.loc[df['taxon'] == 'hybrid']['parent_id'].tolist()
    print(len(parent_ids_of_hybrids))
    print(parent_ids_of_hybrids[:5])
    print(df['id'].head())
    parents_mask = df['id'].isin(parent_ids_of_hybrids)
    print(f"Number of hybrid parent IDs that are also saved as species: {parents_mask.sum()}")

    print("\n---\nChecking for cats and sheep...")
    # checking for cats <- yes!
    print(df['name'].str.contains('.*Felis.*').sum())
    print(df[df['name'].str.contains('.*Felis.*')])
    print(df['name'].str.contains('.*catus.*').sum())
    print(df[df['name'].str.contains('.*catus.*')])
    # how about sheep <- yes!
    print(df['name'].str.contains('.*Ovis.*').sum())
    print(df[df['name'].str.contains('.*Ovis.*')])
    print(df['name'].str.contains('.*aries.*').sum())
    print(df[df['name'].str.contains('.*aries.*')])

    # how many common names?
    print("\n---\nHow many entries have common names?")
    print(df['preferred_common_name'].nunique())

    # is the photo ID the same as the species ID?
    print("\n---\nAre photo IDs different from iNat IDs?")
    test_inat_id = data['results'][0]['taxon']['id']
    test_im_id = data['results'][0]['taxon']['default_photo']['id']
    print(test_inat_id, test_im_id)
    print(f"{'yeah' if test_inat_id != test_im_id else 'nah'}")

    df.to_csv('data/02_taxon_collected_data.csv')


if __name__=="__main__":
    json_src = Path("data/inaturalist_api_all_nz_species.json")
    create_species_data_csv(json_src)