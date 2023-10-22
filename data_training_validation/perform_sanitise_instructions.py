import os

from PIL import Image
from tqdm import tqdm
from torchvision import transforms
from multiprocessing.pool import Pool

# resize data for training
t_512 = transforms.Resize(512)

# move one image for sanitation
def move_single(source, target):
  if os.path.exists(target):
    return
  try:
    im = Image.open(source)
    t_512(im).save(target, format='PNG', optimize=True)
  # log problematic images that cannot be opened or resized
  except:
    print(source, target, flush=True)
  return

# move images using multiprocessing
pool = Pool(processes=96)

# move one class for sanitation
def move(source, target):
  if not os.path.exists(f'dataset/{target}/'):
    os.mkdir(f'dataset/{target}/')
  # collect images to move into the sanitised class
  move_list = []
  # collect research-grade instances
  if os.path.exists(f'res_grade/{source}/'):
    move_list += [(f'res_grade/{source}/{filename}', f"dataset/{target}/{filename.split('.')[0]}.png") for filename in os.listdir(f'res_grade/{source}/')]
  # collect captive/cultivated instances
  if os.path.exists(f'cap_cul/{source}/'):
    move_list += [(f'cap_cul/{source}/{filename}', f"dataset/{target}/{filename.split('.')[0]}.png") for filename in os.listdir(f'cap_cul/{source}/')]
  # perform the move
  if move_list:
    pool.starmap(move_single, move_list)
  # log problematic empty classes
  else:
    print(source, target, flush=True)
  return

# read refined sanitation instructions
instructions = open('refined_instructions.txt', 'r').read().split('\n')
for i in tqdm(instructions):
  if ',' in i:
    parsed_i = i.split(',')
    # delete
    if parsed_i[0] == 'D':
      pass
    # keep
    elif parsed_i[0] == 'K':
      move(parsed_i[1], parsed_i[1])
    # rename
    elif parsed_i[0] == 'R':
      move(parsed_i[2], parsed_i[1])
    # merge
    elif parsed_i[0] == 'M':
      for p_i in parsed_i[2:]:
        move(p_i, parsed_i[1])
# clean up
pool.terminate()
