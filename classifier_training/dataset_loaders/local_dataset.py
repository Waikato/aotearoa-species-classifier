import os
from os import listdir
from os.path import sep, join, exists, splitext, split, abspath
import json
import hashlib

from PIL import Image
import numpy as np
from numpy.random import multivariate_normal
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader


VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}


def get_cache_name(path):
    # Normalize the path (handle different OS formats)
    dataset_name = split(path)[-1]
    norm_path = abspath(path)
    # Create a hash
    path_hash = hashlib.sha256(norm_path.encode()).hexdigest()[:16]  # Shorten hash if needed
    return f"{dataset_name}_cache_{path_hash}.json"


class LocalDataset(Dataset):
    def __init__(self, data_src: str, num_classes=None, train=True, train_prop=0.8, transform=None, cache_loc=None, recreate_cache=False):
        super().__init__()

        self.data_src = data_src
        self.dataset_name = split(data_src)[-1]
        self.cache_name = get_cache_name(data_src)
        self.class_names = [dir for dir in next(os.walk(data_src))[1]]  # collects top-level directories only (i.e., ignores files)
        self.transform = transform
        if cache_loc is None:
            self.cache_file = join('data', self.cache_name)
        else:
            self.cache_file = join(cache_loc, self.cache_name)

        self.num_classes = num_classes
        if not num_classes:
            self.num_classes = len(self.class_names)

        self.id2name = {i: name for i, name in enumerate(self.class_names)}
        self.name2id = {name: i for i, name in enumerate(self.class_names)}

        if exists(self.cache_file) and not recreate_cache:
            with open(self.cache_file, 'r') as f:
                self.im_paths = {int(k): v for k, v in json.load(f).items()}
        else:
            self.im_paths = {
                self.name2id[name]: [
                    join(data_src, name, im_name)
                    for im_name in listdir(join(data_src, name))
                    if splitext(im_name.lower())[-1] in VALID_IMAGE_EXTENSIONS
                ]
                for name in self.class_names
            }
            with open(self.cache_file, 'w') as f:
                json.dump(self.im_paths, f)

        self.all_samples = []
        for class_id, paths in self.im_paths.items():
            cutoff_index = int(len(paths) * train_prop)
            selected_paths = paths[:cutoff_index] if train else paths[cutoff_index:]
            self.all_samples += [(class_id, im_path) for im_path in selected_paths]
        np.random.shuffle(self.all_samples)

    def __len__(self):
        return len(self.all_samples)

    def __getitem__(self, item):
        data_pair = self.all_samples[item]
        image = Image.open(data_pair[1]).convert('RGB')

        if self.transform:
            image = self.transform(image)

        return image, data_pair[0]

