import os
import pickle
import random
import shutil

from tqdm import tqdm

random.seed(0)
classes = os.listdir('dataset')
# split into training and test sets
os.makedirs('dataset/train')
os.makedirs('dataset/test')
# record the number of training observations in each class
instance_count = {}
for class_i in tqdm(classes):
  image_files = os.listdir(f'dataset/{class_i}')
  # log problematic empty class
  if not image_files:
    print(f'empty class {class_i}')
    continue
  instances = {}
  # count observations
  for image_file in image_files:
    instance_id = image_file.split('.')[0].split('_')[-1]
    if instance_id in instances:
      instances[instance_id].append(image_file)
    else:
      instances[instance_id] = [image_file]
  num = len(instances)
  instance_ids = list(instances.keys())
  # move all instances into the training set before splitting into the test set
  shutil.move(f'dataset/{class_i}', f'dataset/train/{class_i}')
  os.makedirs(f'dataset/test/{class_i}')
  instance_count_i = len(instance_ids)
  # if there is only one observation, keep it in the training set
  if num > 1:
    # randomly split 10% of the observations into the test set
    random.shuffle(instance_ids)
    for instance_id in instance_ids[::10]:
      for image_file in instances[instance_id]:
        os.rename(f'dataset/train/{class_i}/{image_file}', f'dataset/test/{class_i}/{image_file}')
      instance_count_i -= 1
  instance_count[class_i] = instance_count_i
# save training observation count for validation later on
pickle.dump(instance_count, open('instance_count.pkl', 'wb'))
