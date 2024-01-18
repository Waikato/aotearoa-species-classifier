Code in this directory downloads and preprocesses data for the species classifier and trains and validates classifier models.

Please install the dependencies listed in the environment.yml file.

Download these data files into this directory:

https://drive.google.com/file/d/1L74V_Fqsvj1ku7drcHpBkS2imYLytsZD/view?usp=sharing

https://drive.google.com/file/d/1TXnETXa2do8jMDITqOf4FIBGZME0p1xc/view?usp=sharing

https://drive.google.com/file/d/1eSdpfSNjnh42FFLo3Y4cxZ3025N-YK7a/view?usp=sharing

Download research-grade and captive/cultivated data:

```
python download_res_grade.py
```

```
python download_cap_cul.py
```

Produce sanitation instructions (optional):

```
python sanitise_instructions.py > sanitise_instructions.txt
```

Fine-clean sanitise_instructions.txt, e.g., handle flagged classes, and rename it to refined_instructions.txt. We have included this refined_instructions.txt produced by us.

Perform sanitation:

```
python perform_sanitise_instructions.py
```

Split data into training and test sets:

```
python split.py
```

Fine-tune an ImageNet21K-pretrained EfficientNetV2 model using the data:

```
python fine_tune.py <model_size> <training_split> <load_checkpoint> <ddp_port>
```

<model_size>: choose among "s", "m", and "l"

<training_split>: choose between "train" and "full"

<load_checkpoint>: option to resume training in case of interruption, enter index of checkpoint to resume, or "None" if first starting training

<ddp_port>: port for parallel training

Example:

```
python fine_tune.py s train None 8888
```

Number of GPUs and batch size per GPU can be modified in fine_tune.py

Validate fine-tuned models:

```
python validate.py <model_size> <checkpoint_directory> <beginning_checkpoint> <end_checkpoint>
```

<model_size>: choose among "s", "m", and "l"

<checkpoint_directory> & <beginning_checkpoint> & <end_checkpoint>: self explanatory

Example:

```
python validate.py s s_train 0 500
```

Merge data back into the full set for training a model for deployment with all data:

```
python split.py
```

Use validation results to aid hyperparameter tuning for training on all data.
