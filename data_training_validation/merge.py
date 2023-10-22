import os

from tqdm import tqdm

classes = os.listdir('dataset/test')
# merge each test class back into the training set
for class_i in tqdm(sorted(classes)):
  image_files = sorted(os.listdir(f'dataset/test/{class_i}'))
  for image_file in image_files:
    os.rename(f'dataset/test/{class_i}/{image_file}', f'dataset/train/{class_i}/{image_file}')
  os.rmdir(f'dataset/test/{class_i}')
os.rmdir(f'dataset/test')
# rename the training set into the full set
os.rename('dataset/train', 'dataset/full')
