import os
import sys
import socket
import urllib.request

import pandas as pd

from PIL import Image
from tqdm import tqdm
from torchvision.datasets.folder import IMG_EXTENSIONS

# decrease wait time for each download
socket.setdefaulttimeout(15)

# IDs and URLs
multimedia = pd.read_csv('captive_cultivated.csv', delimiter = ',')
# iterate through instances to download
for i, row in tqdm(multimedia.iterrows()):
    # download only files with one of the following licenses
    if row['license'] in ['CC-BY', 'CC-BY-NC', 'CC0']:
        species_dir = 'cap_cul/' + row['scientific_name']
        filename = species_dir + '/cap_cul_' + str(i) + '_' + str(row['id']) + '.' + str(row['image_url']).split('.')[-1]
        # skip files in incompatible formats
        if not filename.lower().endswith(('.',) + IMG_EXTENSIONS):
            print('\nSkipped', str(i), row['id'], row['image_url'], flush=True)
            continue
        try:
            if not os.path.exists(species_dir):
                os.makedirs(species_dir)
            if os.path.exists(filename):
                continue
            urllib.request.urlretrieve(row['image_url'].replace('small', 'original').replace('medium', 'original').replace('large', 'original'), filename)
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
                        print('\nRemoved incompatible', str(i), row['id'], row['image_url'], flush=True)
            # remove corrupted files
            except:
                print('\nRemoved unreadable', str(i), row['id'], row['image_url'], flush=True)
                os.remove(filename)
        # report failed downloads
        except:
            print('\nFailed to acquire', str(i), row['id'], row['image_url'], flush=True)
