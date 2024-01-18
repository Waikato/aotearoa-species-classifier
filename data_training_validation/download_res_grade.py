import os
import sys
import magic
import socket
import urllib.request

import pandas as pd

from PIL import Image
from tqdm import tqdm
from torchvision.datasets.folder import IMG_EXTENSIONS

# decrease wait time for each download
socket.setdefaulttimeout(15)

# IDs and URLs
multimedia = pd.read_csv('multimedia.txt', delimiter = '\t')
# IDs and labels
dataset = pd.read_csv('NZ-Species.csv', delimiter = '\t')
# iterate through instances to download
for i, row in tqdm(multimedia.iterrows()):
    species_dir = 'res_grade/' +  dataset.loc[dataset['gbifID'] == row['gbifID'], 'verbatimScientificName'].iat[0]
    filename = species_dir + '/' + str(i) + '_' + str(row['gbifID']) + '.' + str(row['format']).split('/')[-1]
    # skip files in incompatible formats
    if not (str(row['identifier']).lower().endswith(('.',) + IMG_EXTENSIONS) or filename.lower().endswith(('.',) + IMG_EXTENSIONS)):
        print('\nSkipped', str(i), row['gbifID'], row['identifier'], flush=True)
        continue
    try:
        if not os.path.exists(species_dir):
            os.makedirs(species_dir)
        if os.path.exists(filename):
            continue
        urllib.request.urlretrieve(row['identifier'], filename)
        try:
            # download file and save in RGB mode
            im = Image.open(filename).convert('RGB')
            if filename.lower().endswith(IMG_EXTENSIONS):
                im.save(filename)
            else:
                # determine format for files missing this information
                os.remove(filename)
                pil_extension = '.' + im.format.lower()
                if pil_extension in IMG_EXTENSIONS:
                    im.save(filename.split('.')[0] + pil_extension)
                else:
                    print('\nRemoved incompatible', str(i), row['gbifID'], row['identifier'], flush=True)
        # remove corrupted files
        except:
            print('\nRemoved unreadable', str(i), row['gbifID'], row['identifier'], flush=True)
            os.remove(filename)
    # report failed downloads
    except:
        print('\nFailed to acquire', str(i), row['gbifID'], row['identifier'], flush=True)
