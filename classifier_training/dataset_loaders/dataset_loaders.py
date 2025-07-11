import torch
import torchvision.transforms as transforms
import torchvision.datasets as datasets
from torch.utils.data import DataLoader
from PIL import Image

from dataset_loaders.local_dataset import LocalDataset


class ConditionalResize:
    def __init__(self, min_size=128):
        self.min_size = min_size

    def __call__(self, image):
        width, height = image.size
        if min(width, height) < self.min_size:
            scale_factor = self.min_size / min(width, height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            return image.resize(new_size, Image.BILINEAR)
        return image


def prepare_cifar10(batch_size=128, transform=None):
    if transform is None:
        transform = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            transforms.RandomCrop(32, padding=4),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))
        ])

    # Load CIFAR-10 dataset
    train_dataset = datasets.CIFAR10(root="./data", train=True, transform=transform, download=True)
    test_dataset = datasets.CIFAR10(root="./data", train=False, transform=transform, download=True)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True, num_workers=0)

    return train_loader, test_loader


def prepare_local_dataset(src_path, batch_size=128, num_classes=None, train_prop=0.8, transform=None, drop_last=False, input_size=224):
    if transform is None:
        transform = transforms.Compose([
            transforms.RandomHorizontalFlip(),
            ConditionalResize(min_size=input_size),
            transforms.RandomCrop(input_size, padding=4),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.247, 0.243, 0.261))
        ])

    train_dataset = LocalDataset(src_path, num_classes=num_classes, train=True, train_prop=train_prop, transform=transform, recreate_cache=False)
    test_dataset = LocalDataset(src_path, num_classes=num_classes, train=False, train_prop=train_prop, transform=transform, recreate_cache=False)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=drop_last)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True, num_workers=0, drop_last=drop_last)

    return train_loader, test_loader, train_dataset, test_dataset

