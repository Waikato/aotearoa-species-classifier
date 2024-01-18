import os

import pandas as pd

from tqdm import tqdm

def format_row(row):
  if row['taxonRank'] in ['SUBSPECIES', 'VARIETY', 'FORM']:
    return (row['species'], row['taxonRank'])
  return (row[row['taxonRank'].lower()], row['taxonRank'])

# handle research-grade classes
info = pd.read_csv('NZ-Species.csv', delimiter = '\t')
classes = {}
for class_name in sorted(os.listdir('res_grade')):
  row = info[info['verbatimScientificName'] == class_name].iloc[0]
  classes[class_name] = format_row(row)
new_classes = {}
# sanitise classes with standardising hybrid names
for k, v in classes.items():
  # delete classes at super-species taxon levels
  if v[1] in ['GENUS', 'FAMILY', 'ORDER', 'CLASS']:
    if ' ' in k:
      new_classes[k] = k.replace(' x ', ' × ')
    else:
      new_classes[k] = None
  elif v[1] == 'SPECIES':
    if k.endswith('virus') or ' virus ' in k or ' ' not in k:
      new_classes[k] = None
    # convert sub-species classes into species classes
    elif k.split(' ')[0 : 2] == v[0].split(' ') or v[0] in classes:
      new_classes[k] = v[0].replace(' x ', ' × ')
    elif len(k.split(' ')) == 3 and ' '.join(k.split(' ')[0 : 2]) in classes:
      new_classes[k] = ' '.join(k.split(' ')[0 : 2]).replace(' x ', ' × ')
    else:
      new_classes[k] = k.replace(' x ', ' × ')
  else:
    new_classes[k] = (' '.join(k.split(' ')[0 : 2]).replace(' x ', ' × '), v[0].replace(' x ', ' × ')) if str(v[0]) != 'nan' else k.replace(' x ', ' × ')
# handle additional captive/cultivated classes
info = pd.read_csv('captive_cultivated.csv', delimiter = ',')
for class_name in sorted(os.listdir('cap_cul')):
  if class_name not in new_classes:
    species_name = info.loc[info['scientific_name'] == class_name, 'taxon_species_name'].iat[0]
    new_classes[class_name] = species_name.replace(' x ', ' × ') if str(species_name) != 'nan' else class_name
# collect classes to be deleted, renamed, or merged
delete_classes = []
rename_classes = {}
for k, v in new_classes.items():
  if type(v) is tuple:
    continue
  else:
    if v == None:
      delete_classes.append(k)
    elif v in rename_classes:
      rename_classes[v].append(k)
    else:
      rename_classes[v] = [k]
for k, v in new_classes.items():
  if type(v) is tuple:
    if k == 'Penion cuvierianus jeakingsi':
      rename_classes['Penion ormesi'] = [k]
    elif v[0] in rename_classes:
      rename_classes[v[0]].append(k)
    elif v[1] in rename_classes:
      rename_classes[v[1]].append(k)
    else:
      rename_classes[v[0]] = [k]
# format and print sanitation instructions
for delete_class in sorted(delete_classes):
  print(f'D,{delete_class}')
keep_lines = []
rename_lines = []
merge_classes = []
flag_keep_lines = []
flag_rename_lines = []
flag_merge_classes = []
for k, v in rename_classes.items():
  if len(v) == 1:
    if v[0] == k:
      if len(k.split(' ')) == 2 and (k not in classes or classes[k][1] not in ['GENUS', 'FAMILY', 'ORDER', 'CLASS']):
        keep_lines.append(f'K,{k}')
      else:
        flag_keep_lines.append(f'FLAG K,{k}')
    elif v[0].startswith(k) and len(k.split(' ')) == 2:
      rename_lines.append(f'R,{k},{v[0]}')
    else:
      flag_rename_lines.append(f'FLAG R,{k},{v[0]}')
  elif all([vi.startswith(k) for vi in v]):
    merge_classes.append(k)
  else:
    flag_merge_classes.append(k)
for keep_line in sorted(keep_lines):
  print(keep_line)
for rename_line in sorted(rename_lines):
  print(rename_line)
for merge_class in sorted(merge_classes):
  print(f'M,{merge_class}', end='')
  for sub_class in sorted(rename_classes[merge_class]):
    print(f',{sub_class}', end='')
  print()
for keep_line in sorted(flag_keep_lines):
  print(keep_line)
for rename_line in sorted(flag_rename_lines):
  print(rename_line)
for merge_class in sorted(flag_merge_classes):
  print(f'FLAG M,{merge_class}', end='')
  for sub_class in sorted(rename_classes[merge_class]):
    print(f',{sub_class}', end='')
  print()
