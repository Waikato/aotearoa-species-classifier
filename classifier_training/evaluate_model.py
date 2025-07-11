import json
import os.path

from huggingface_hub import accept_access_request
from tqdm import tqdm
from os.path import join
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
import torch
import torchvision.transforms as transforms
import torchvision.datasets as datasets
from torchvision.models.efficientnet import efficientnet_v2_s
import torch.distributed as dist
from torch.utils.data import DataLoader, DistributedSampler, SequentialSampler
from torch.nn.parallel import DistributedDataParallel
from timm.models import create_model
from timm.loss import LabelSmoothingCrossEntropy, SoftTargetCrossEntropy
from timm.utils import NativeScaler, accuracy
from timm.optim import create_optimizer
from timm.scheduler import create_scheduler
from timm.data import Mixup

from helpers.utils import running_average, get_world_size, get_rank, init_distributed_mode, setup_distributed, DictToObject, is_main_process
from dataset_loaders.dataset_loaders import prepare_cifar10, prepare_local_dataset

torch.manual_seed(0)
torch.cuda.manual_seed(0)

model_names = [
    "efficientformerv2_s1",  # efficientformer model
    "efficientnet_v2_s",  # original efficientnet v2 s
    "tf_efficientnetv2_s.in21k",  # efficientnet v2 s trained on imagenet21k
    "efficientvit_m4.r224_in1k",  # efficientvit seems to be even  smaller than efficientformer?
]
input_sizes = {
    "efficientformerv2_s1": 224,
    "efficientnet_v2_s": 300,
    "tf_efficientnetv2_s.in21k": 300,
    "efficientvit_m4.r224_in1k": 224,
}


def prepare_data(src_path, batch_size, num_classes=None, train_prop=0.8, input_size=224):
    #train_loader, test_loader = prepare_cifar10(batch_size)
    train_loader, test_loader, train_dataset, test_dataset = prepare_local_dataset(src_path, batch_size, num_classes=num_classes, train_prop=train_prop, drop_last=True, input_size=input_size)

    return train_loader, test_loader, train_dataset, test_dataset


def get_class_accuracies(model, dataloader, num_classes, device):
    model.eval()
    mean_acc = 0

    class_accuracies = {i: {'results': []} for i in range(num_classes)}

    with torch.no_grad():
        for i, data in enumerate(tqdm(dataloader, smoothing=50/len(dataloader))):
            images, targets = data
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            output = model(images)
            assert len(output.shape) == 2, f"Expected 2D output predictions batch but got shape {output.shape}"
            pred_classes = torch.argmax(output, dim=1)
            acc = accuracy(output, targets)

            for j in range(len(targets)):
                cat = int(targets[j].item())
                correct = int(targets[j].item() == pred_classes[j].item())
                class_accuracies[cat]['results'].append(correct)


            mean_acc = running_average(acc[0], mean_acc, i)

    for cat in class_accuracies.keys():
        if len(class_accuracies[cat]['results']) > 0:
            acc = sum(class_accuracies[cat]['results']) / len(class_accuracies[cat]['results'])
        else:
            acc = None
        class_accuracies[cat]['accuracy'] = acc

    return {'accuracy': mean_acc.item(), 'class_accuracies': class_accuracies}


def plot_histograms(accuracy_data, bins='auto', density=False, save_fig=False, unique_name=None):
    accuracies = [accuracy_data[cat]['accuracy'] for cat in accuracy_data.keys() if accuracy_data[cat]['accuracy'] is not None]
    print(f"found {sum([1 if acc is None else 0 for acc in accuracies])} None values in accuracy data")

    plt.figure(figsize=(10, 6))
    plt.hist(accuracies, bins=bins, density=density)
    plt.xlabel("Class Accuracy")
    plt.ylabel(f"{'Proportion' if density else 'Count'}")
    plt.title("Histogram of Class Accuracies")
    if save_fig:
        if not os.path.exists("figures"): os.mkdir("figures")
        plt.savefig(Path("figures") / Path(f"{unique_name + '_' if unique_name is not None else ''}class_accuracies_histogram.png"))
    plt.show()


def plot_accuracies_by_class_size(accuracy_data, bins='auto', density=False, save_fig=False, unique_name=None):
    test_set_sizes = np.asarray([len(accuracy_data[cat]['results']) for cat in accuracy_data.keys() if accuracy_data[cat]['accuracy'] is not None])
    accuracies = np.asarray([accuracy_data[cat]['accuracy'] for cat in accuracy_data.keys() if accuracy_data[cat]['accuracy'] is not None])

    plt.figure(figsize=(10, 6))
    plt.hist(test_set_sizes, bins=bins, density=density)
    plt.xlabel("Test Set Size")
    plt.ylabel(f"{'Proportion' if density else 'Count'}")
    plt.title("Histogram of Class Test Set Sizes")
    if save_fig:
        if not os.path.exists("figures"): os.mkdir("figures")
        plt.savefig(Path("figures") / Path(
            f"{unique_name + '_' if unique_name is not None else ''}class_test_set_sizes_histogram.png"))
    plt.show()

    # plot accuracy by test set size group
    if bins == 'auto':
        bins = 20
    steps = np.linspace(min(test_set_sizes), max(test_set_sizes), bins+1)
    steps[-1] += 1e-6

    bin_labels = []
    group_means = []
    group_stds = []
    for i in range(len(steps) - 1):
        in_bin = (steps[i] <= test_set_sizes) & (test_set_sizes < steps[i + 1])
        accs = accuracies[in_bin]
        if len(accs) == 0:
            group_means.append(np.nan)
            group_stds.append(0)
        else:
            group_means.append(np.mean(accs))
            group_stds.append(np.std(accs))

        # Create label like "10–20"
        bin_labels.append(f"{int(steps[i])}–{int(steps[i + 1])}")

    # Plot bar chart
    x = np.arange(len(bin_labels))
    plt.figure(figsize=(10, 6))
    plt.bar(x, group_means, yerr=group_stds, capsize=5, alpha=0.7, color='skyblue')
    plt.xticks(x, bin_labels, rotation=45, ha='right')
    plt.ylim(0, 1)
    plt.xlabel("Number of Test Set Samples (Grouped)")
    plt.ylabel("Mean Group Accuracy")
    plt.title("Mean Accuracy per Test Sample Count Group")
    plt.tight_layout()
    if save_fig:
        if not os.path.exists("figures"): os.mkdir("figures")
        plt.savefig(Path("figures") / Path(
            f"{unique_name + '_' if unique_name is not None else ''}class_test_accuracies_histogram.png"))
    plt.show()


def main(args, regenerate=False, plot_data=False):
    args = DictToObject(args)
    device = torch.device(args.device)
    json_tgt = f"results/{Path(args.checkpoint_path).stem}_test_stats.json"
    checkpoint_name = Path(args.checkpoint_path).stem

    if regenerate or not os.path.exists(json_tgt):  # only create the file if it doesn't already exist/is requested.
        #
        # data preparation
        #

        print("preparing data...")
        _, _, train_dataset, test_dataset = prepare_data(
            '../../../Datasets/inaturalist/20250611_medium_inaturalist_data',
            # '../../../Datasets/Species_Data/2024_species_train_224',
            # '../../../Datasets/stink-bugs/data_224',
            args.batch_size,
            train_prop=args.train_prop,
            input_size=input_sizes[args.model_name]
        )
        assert train_dataset.num_classes == test_dataset.num_classes, f"Warning! Expected test dataset to have {train_dataset.num_classes} classes, but is has {test_dataset.num_classes} classes."

        if args.num_classes is None:
            args.num_classes = test_dataset.num_classes  # set number of classes if not specified

        test_loader = DataLoader(test_dataset, batch_size=args.batch_size, num_workers=8, drop_last=True)

        print(f"done! {args.num_classes} classes.")

        #
        # load model
        #

        print("loading model...")
        model = create_model(
            model_name=f'{args.model_name}',
            num_classes=args.num_classes,
            pretrained=True
        )
        checkpoint = torch.load(args.checkpoint_path, map_location='cpu')
        # models trained by dataparallel have module prefix in state dict that needs to be removed
        new_state_dict = {}
        for k, v in checkpoint['state_dict'].items(): # Assuming 'state_dict' is the key holding the dict
            if k.startswith('module.'):
                new_state_dict[k[7:]] = v  # Remove 'module.' prefix
            else:
                new_state_dict[k] = v

        model.load_state_dict(new_state_dict)
        #model.load_state_dict(checkpoint['state_dict'])
        model.to(device)
        print("done!")

        #
        # get class accuracies...
        #

        class_accuracies = get_class_accuracies(model, test_loader, args.num_classes, device)
        if not os.path.exists("results"): os.mkdir("results")
        with open(f"results/{checkpoint_name}_test_stats.json", 'w') as f:
            json.dump(class_accuracies, f)

    if plot_data:
        #
        # analyse!
        #
        with open(f"results/{checkpoint_name}_test_stats.json", 'r') as f:
            class_accuracies = json.load(f)

        plot_histograms(class_accuracies['class_accuracies'], unique_name=checkpoint_name, save_fig=True)
        plot_accuracies_by_class_size(class_accuracies['class_accuracies'], unique_name=checkpoint_name, save_fig=True)



if __name__=="__main__":
    model_name = 'tf_efficientnetv2_s.in21k' #'efficientvit_m4.r224_in1k'  #'efficientformerv2_s1'
    checkpoint_path = 'checkpoints/20250703_efficientnetv2_0-136.pth' #'checkpoints/earthy-hill-23_0-150.pth' #'checkpoints/atomic-durian-20.pth' #'checkpoints/earthy-hill-23_0-150.pth'
    args = {
        'model_name': model_name,
        'checkpoint_path': checkpoint_path,
        'batch_size': 512,
        'device': 'cuda',
        'train_prop': 0.8,
        'num_classes': None
    }
    main(args, regenerate=False, plot_data=True)

