import sys
import math
import wandb
from tqdm import tqdm
from os.path import join
from pathlib import Path

import torch
import torchvision.transforms as transforms
import torchvision.datasets as datasets
from torch.utils.data import DataLoader
from timm.models import create_model
from timm.loss import LabelSmoothingCrossEntropy, SoftTargetCrossEntropy
from timm.utils import NativeScaler, accuracy
from timm.optim import create_optimizer
from timm.scheduler import create_scheduler
from timm.data import Mixup

from helpers.utils import running_average, get_world_size, DictToObject
from dataset_loaders.dataset_loaders import prepare_cifar10, prepare_local_dataset

# Define device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# Set random seed for reproducibility
torch.manual_seed(42)


def prepare_data(src_path, batch_size, num_classes=None, train_prop=0.8):
    #train_loader, test_loader = prepare_cifar10(batch_size)
    train_loader, test_loader, train_dataset, test_dataset = prepare_local_dataset(src_path, batch_size, num_classes=num_classes, train_prop=train_prop, drop_last=True)

    return train_loader, test_loader, train_dataset, test_dataset


def train_epoch(model, criterion, train_loader, optimizer, loss_scaler, clip_grad, clip_mode, mixup_fn):
    model.train()
    mean_loss, mean_acc = 0, 0
    for i, data in enumerate(tqdm(train_loader)):
        samples, targets = data
        samples = samples.to(device)
        targets = targets.to(device)

        if mixup_fn is not None:
            samples, targets = mixup_fn(samples, targets)

        #print(samples.shape)
        outputs = model(samples)
        loss = criterion(outputs, targets)  # note original code had distillation loss which we aren't using

        loss_value = loss.item()

        if not math.isfinite(loss_value):
            print(f"Loss is {loss_value}, stopping training")
            sys.exit(1)

        optimizer.zero_grad()

        # this attribute is added by timm on one optimizer (adahessian)
        is_second_order = hasattr(
            optimizer, 'is_second_order') and optimizer.is_second_order
        loss_scaler(loss, optimizer, clip_grad=clip_grad, clip_mode=clip_mode,
                    parameters=model.parameters(), create_graph=is_second_order)
        targets = targets.argmax(dim=1)  # Convert from one-hot to class indices
        acc = accuracy(outputs, targets)
        mean_loss = running_average(loss_value, mean_loss, i)
        mean_acc = running_average(acc[0], mean_acc, i)
    current_lr = optimizer.param_groups[0]['lr']
    return {'loss': mean_loss, 'accuracy': mean_acc, "lr": current_lr}


def evaluate(model, test_loader):
    model.eval()
    mean_loss, mean_acc = 0, 0
    criterion = torch.nn.CrossEntropyLoss()

    with torch.no_grad():
        for i, data in enumerate(test_loader):
            images, targets = data
            images = images.to(device)
            targets = targets.to(device)

            output = model(images)
            loss = criterion(output, targets)
            loss = loss.item()
            acc = accuracy(output, targets)

            mean_loss = running_average(loss, mean_loss, i)
            mean_acc = running_average(acc[0], mean_acc, i)
    return {'loss': mean_loss, 'accuracy': mean_acc}


def train(model, train_loader, test_loader, optimizer, criterion, epochs, loss_scaler, lr_scheduler, mixup_fn, args):

    for epoch in range(epochs):
        print(f"Epoch {epoch+1}")

        train_stats = train_epoch(
            model, criterion, train_loader, optimizer, loss_scaler, args.clip_grad, args.clip_mode, mixup_fn
        )
        eval_stats = evaluate(model, test_loader)

        lr_scheduler.step(epoch)

        log_stats = {
            'epoch': epoch,
            'train': train_stats,
            'test': eval_stats
        }
        wandb.log(log_stats)
        print(f"Results:\n"
              f"Train Loss: {log_stats['train']['loss']:.4f}, Train Accuracy: {log_stats['train']['accuracy']}\n"
              f"Test Loss:  {log_stats['test']['loss']:.4f}, Test Accuracy:  {log_stats['test']['accuracy']}\n---")
        if args.save_checkpoints:
            model_dict = {
                'state_dict': model.state_dict(),
                'args': vars(args)
            }
            Path('checkpoints').mkdir(parents=True, exist_ok=True)
            if args.checkpoint_name is not None:
                torch.save(model_dict, join('checkpoints', f"{args.checkpoint_name}.pth"))
            else:
                torch.save(model_dict, join('checkpoints', f"{wandb.run.name}.pth"))


def main(lr, batch_size, epochs, args, mixup=0.8, smoothing=0.1):
    args = DictToObject(args)

    #
    # data preparation
    #

    print("preparing data...")
    #train_loader, test_loader, train_dataset, test_dataset = prepare_data('../../../Datasets/stink-bugs/data_224', args.batch_size)
    #train_loader, test_loader, train_dataset, test_dataset = prepare_data('../../../../hw168/2023B/NZ-Species-Training/dataset/train', args['batch_size'])
    #train_loader, test_loader, train_dataset, test_dataset = prepare_data('data/demo_data', args['batch_size'])
    train_loader, test_loader, train_dataset, test_dataset = prepare_data('../../../Datasets/Species_Data/2024_species_train_224', args.batch_size)

    if args.num_classes is None:
        args.num_classes = train_dataset.num_classes  # set number of classes if not specified

    print(f"done! {args.num_classes} classes.")


    wandb.init(
        project="efficientformer_experiments",
        config=vars(args),
        mode=args.wandb_mode,
        group='002-species'
    )

    mixup_fn = None
    mixup_active = mixup > 0 or args.cutmix > 0.0 or args.cutmix_minmax is not None
    if mixup_active:
        mixup_fn = Mixup(
            mixup_alpha=mixup, cutmix_alpha=args.cutmix, cutmix_minmax=args.cutmix_minmax,
            prob=args.mixup_prob, switch_prob=args.mixup_switch_prob, mode=args.mixup_mode,
            label_smoothing=args.smoothing, num_classes=args.num_classes
        )

    #
    # create model
    #

    model =create_model(
        'efficientformerv2_s1',
        num_classes=args.num_classes,
        pretrained=True
    )  # perhaps it really is that simple
    model.to(device)
    n_parameters = sum(p.numel()
                       for p in model.parameters() if p.requires_grad)
    print(model.default_cfg)
    print('number of params:', n_parameters)

    linear_scaled_lr = lr * batch_size * get_world_size() / 1024.
    lr = linear_scaled_lr

    optimizer = create_optimizer(args, model)  # the demo uses model_without_ddp, but I believe this is only relevant for parallel training
    loss_scaler = NativeScaler()

    lr_scheduler, _ = create_scheduler(args, optimizer)

    criterion = LabelSmoothingCrossEntropy()

    if mixup > 0:
        criterion = SoftTargetCrossEntropy()
    elif smoothing:
        criterion = LabelSmoothingCrossEntropy(smoothing=smoothing)
    else:
        criterion = torch.nn.CrossEntropyLoss()

    #
    # training
    #

    train(model, train_loader, test_loader, optimizer, criterion, epochs, loss_scaler, lr_scheduler, mixup_fn, args)

    wandb.finish()


if __name__ == "__main__":
    mode='disabled'
    epochs = 100
    batch_size = 384
    lr = 1e-3
    args = {
        'epochs': epochs,  # general params
        'batch_size': batch_size,
        'num_classes': None,
        'smoothing': 0.1,
        'wandb_mode': mode,
        'save_checkpoints': True,
        'checkpoint_name': 'test',
        'opt': 'adamw',  # optimizer params
        'opt_eps': 1e-8,
        'opt_betas': None,
        'clip_grad': 0.01,
        'clip_mode': 'agc',
        'momentum': 0.9,
        'weight_decay': 0.025,
        'sched': 'cosine',  # schedule parameters
        'lr': lr,
        'lr_noise': None,
        'lr_noise_pct': 0.67,
        'lr_noise_std': 1.0,
        'warmup_lr': 1e-5,
        'min_lr': 1e-5,
        'decay_epochs': 30,
        'warmup_epochs': 5,
        'cooldown_epochs': 10,
        'patience_epochs': 10,
        'decay_rate': 0.1,
        'mixup': 0.8,  # mixup parameters
        'cutmix': 1.0,
        'cutmix_minmax': None,
        'mixup_prob': 1.0,
        'mixup_switch_prob': 0.5,
        'mixup_mode': 'batch'
    }
    main(
        lr=lr,
        batch_size=batch_size,
        epochs=epochs,
        args=args,
        mixup=args['mixup'],
        smoothing=args['smoothing']
    )

