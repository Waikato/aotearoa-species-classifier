import json
from tqdm import tqdm
import pandas as pd

#
# paths
#

srcpath_pestdata = "data/00_mpi_pest_register.csv"
srcpath_coredata = "data/01_species_14991_coredata.json"
tgtpath_mpidata = "data/03_species_14991_mpidata.json"


# Function to aggregate strings
def aggregate_strings(group):
    if len(group) == 1:
        return group.iloc[0]
    else:
        unique_values = sorted(group.unique())
        return ",".join(unique_values)


if __name__ == "__main__":
    """
    merge MPI pest data (unwanted, notifiable)
    target mpidata structure:
    - species key
        - unwanted
        - notifiable
    """
    #
    # load data
    #
    with open(srcpath_coredata, "r") as file:
        coredata = json.load(file)
    pest_df = pd.read_csv(srcpath_pestdata, delimiter=',')

    # drop common names
    pest_df = pest_df.drop("Common name(s)", axis=1)

    # drop "Virus" rows
    pest_df = pest_df[pest_df["Organism type"] != "Virus"]

    # keep unique rows only
    pest_df = pest_df.drop_duplicates()

    # drop rows where both unwanted and notifiable are "No"
    pest_df = pest_df[(pest_df["Unwanted"] != "No") | (pest_df["Notifiable"] != "No")]

    # Convert entries in the 'Pest name' and 'Scientific name(s)' columns to lowercase
    pest_df["Pest name"] = pest_df["Pest name"].str.lower()
    pest_df["Scientific name(s)"] = pest_df["Scientific name(s)"].str.lower()

    # fill nan values
    pest_df["Unwanted"] = pest_df["Unwanted"].fillna("")
    pest_df["Notifiable"] = pest_df["Notifiable"].fillna("")
    print(pest_df["Unwanted"].unique())
    print(pest_df["Notifiable"].unique())

    num_matches = 0
    mpidata = {}
    for key in tqdm(coredata.keys()):
        mpidata[key] = {}
        scientific_name = coredata[key]['scientific_name']
        pest_matches = pest_df[(pest_df["Pest name"] == scientific_name.lower()) | (
            pest_df["Scientific name(s)"].str.contains(scientific_name.lower(), na=False))]
        pest_matches = pest_matches.loc[:, ["Organism type", "Unwanted", "Notifiable"]]

        # Aggregate unwanted and notifiable columns into alphabetically ordered comma-separated strings
        pest_matches = pest_matches.groupby(["Organism type"]).agg(
            {"Unwanted": aggregate_strings, "Notifiable": aggregate_strings})

        if scientific_name == "Apis mellifera":  # check for common honey bee
            print(pest_matches)
        mpidata[key]['unwanted'] = ""
        mpidata[key]['notifiable'] = ""
        if not pest_matches.empty:
            first_row = pest_matches.iloc[0]
            mpidata[key]['unwanted'] = first_row["Unwanted"]
            mpidata[key]['notifiable'] = first_row["Notifiable"]
            num_matches += 1

    # save the results
    print(
        f"saving dict with {len(mpidata.keys())} entries to {tgtpath_mpidata}... {num_matches} species matched.")
    with open(tgtpath_mpidata, 'w') as json_file:
        json.dump(mpidata, json_file)
    print("done!")

