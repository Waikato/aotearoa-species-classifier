import sys
import math
import wandb
from tqdm import tqdm
from os.path import join
from pathlib import Path

import numpy as np
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


def train_epoch(model, criterion, train_loader, optimizer, loss_scaler, clip_grad, clip_mode, mixup_fn, device):
    model.train()
    mean_loss, mean_acc = 0, 0
    for i, data in enumerate(tqdm(train_loader, smoothing=50/len(train_loader))):
        samples, targets = data
        samples = samples.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

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

        torch.cuda.synchronize()

        targets = targets.argmax(dim=1)  # Convert from one-hot to class indices
        acc = accuracy(outputs, targets)
        mean_loss = running_average(loss_value, mean_loss, i)
        mean_acc = running_average(acc[0], mean_acc, i)

    # Convert metrics to tensors for distributed reduction
    mean_loss_tensor = torch.tensor(mean_loss, dtype=torch.float32, device=device)
    mean_acc_tensor = torch.tensor(mean_acc, dtype=torch.float32, device=device)

    # Reduce across all processes (sum)
    dist.all_reduce(mean_loss_tensor, op=dist.ReduceOp.SUM)
    dist.all_reduce(mean_acc_tensor, op=dist.ReduceOp.SUM)

    # Divide by world size (number of processes) to get mean
    world_size = dist.get_world_size()
    mean_loss_tensor /= world_size
    mean_acc_tensor /= world_size

    return {'loss': mean_loss, 'accuracy': mean_acc}


def evaluate(model, test_loader, device):
    model.eval()
    mean_loss, mean_acc = 0, 0
    criterion = torch.nn.CrossEntropyLoss()

    with torch.no_grad():
        for i, data in enumerate(test_loader):
            images, targets = data
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            output = model(images)
            loss = criterion(output, targets)
            loss = loss.item()
            acc = accuracy(output, targets)

            mean_loss = running_average(loss, mean_loss, i)
            mean_acc = running_average(acc[0], mean_acc, i)

    # Convert metrics to tensors for distributed reduction
    mean_loss_tensor = torch.tensor(mean_loss, dtype=torch.float32, device=device)
    mean_acc_tensor = torch.tensor(mean_acc, dtype=torch.float32, device=device)

    # Reduce across all processes (sum)
    dist.all_reduce(mean_loss_tensor, op=dist.ReduceOp.SUM)
    dist.all_reduce(mean_acc_tensor, op=dist.ReduceOp.SUM)

    # Divide by world size (number of processes) to get mean
    world_size = dist.get_world_size()
    mean_loss_tensor /= world_size
    mean_acc_tensor /= world_size

    return {'loss': mean_loss, 'accuracy': mean_acc}


def train(model, train_loader, test_loader, optimizer, criterion, epochs, loss_scaler, lr_scheduler, mixup_fn, device, args):

    for epoch in range(epochs):
        if args.distributed:
            train_loader.sampler.set_epoch(epoch)

        print(f"Epoch {epoch+1}")

        train_stats = train_epoch(
            model, criterion, train_loader, optimizer, loss_scaler, args.clip_grad, args.clip_mode, mixup_fn, device
        )
        eval_stats = evaluate(model, test_loader, device)

        lr_scheduler.step(epoch)

        if is_main_process():  # only do this stuff in the main process
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
                    'optimiser': optimizer.state_dict(),
                    'lr_scheduler': lr_scheduler.state_dict(),
                    'epoch': epoch,
                    'scaler': loss_scaler.state_dict(),
                    'args': vars(args)
                }
                Path('checkpoints').mkdir(parents=True, exist_ok=True)
                if args.checkpoint_name is not None:
                    torch.save(model_dict, join('checkpoints', f"{args.checkpoint_name}_{args.start_epoch}-{args.start_epoch + epochs}.pth"))
                else:
                    torch.save(model_dict, join('checkpoints', f"{wandb.run.name}_{args.start_epoch}-{args.start_epoch + epochs}.pth"))


def main(lr, batch_size, epochs, args, mixup=0.8, smoothing=0.1):
    args = DictToObject(args)
    init_distributed_mode(args)
    device = torch.device(args.device)

    # fix seed
    seed = args.seed + get_rank()
    torch.manual_seed(seed)
    np.random.seed(seed)

    #
    # data preparation
    #

    print("preparing data...")
    _, _, train_dataset, test_dataset = prepare_data(
        '../../../Datasets/inaturalist/20250611_medium_inaturalist_data',
        #'../../../Datasets/Species_Data/2024_species_train_224',
        #'../../../Datasets/stink-bugs/data_224',
        args.batch_size,
        train_prop=args.train_prop,
        input_size=input_sizes[args.model_name]
    )

    if args.num_classes is None:
        args.num_classes = train_dataset.num_classes  # set number of classes if not specified

    print(f"done! {args.num_classes} classes.")


    if is_main_process():
        wandb.init(
            project="efficientformer_experiments",
            config=vars(args),
            mode=args.wandb_mode,
            group='002-species'
        )

    num_tasks = get_world_size()
    global_rank = get_rank()

    #
    # prepare dataloaders
    #

    sampler_train = DistributedSampler(train_dataset, num_replicas=num_tasks, rank=global_rank, shuffle=True)
    if args.dist_eval:
        if len(test_dataset) % num_tasks != 0:
            print('Warning: Enabling distributed evaluation with an eval dataset not divisible by process number. '
                  'This will slightly alter validation results as extra duplicate entries are added to achieve '
                  'equal num of samples per-process.')
            sampler_test = DistributedSampler(test_dataset, num_replicas=num_tasks, rank=global_rank, shuffle=False)
        else:
            sampler_test = SequentialSampler(test_dataset)

    train_loader = DataLoader(train_dataset, sampler=sampler_train, batch_size=args.batch_size,
                              num_workers=args.num_workers, pin_memory=args.pin_mem, drop_last=True)
    test_loader = DataLoader(test_dataset, sampler=sampler_test, batch_size=args.batch_size,
                              num_workers=args.num_workers, pin_memory=args.pin_mem, drop_last=True)

    #
    # prepare mixup
    #

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

    print("creating model...")
    model = create_model(
        model_name=f'{args.model_name}',
        num_classes=args.num_classes,
        pretrained=True
    )

    checkpoint = None
    if args.resume is not None:
        checkpoint = torch.load(args.resume, map_location='cpu')
        model.load_state_dict(checkpoint['model'])

    model.to(device)

    if args.distributed:  # note that distributed and args.gpu should be set by init_distributed_mode
        model = DistributedDataParallel(model, device_ids=[args.gpu], find_unused_parameters=False)
        #model_without_ddp = model.module

    n_parameters = sum(p.numel()
                       for p in model.parameters() if p.requires_grad)
    #print(f"model configs: {model.default_cfg}")  # dist doesn't like this >:(
    print('number of params:', n_parameters)

    linear_scaled_lr = lr * batch_size * get_world_size() / 1024.
    args.lr = linear_scaled_lr

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
    # load previous states if applicable
    #

    if checkpoint is not None:
        if 'optimizer' in checkpoint:
            optimizer.load_state_dict(checkpoint['optimizer'])
        if 'lr_scheduler' in checkpoint:
            lr_scheduler.load_state_dict(checkpoint['lr_scheduler'])
        if 'epoch' in checkpoint:
            args.start_epoch = checkpoint['epoch'] + 1
        if 'scaler' in checkpoint:
            loss_scaler.load_state_dict(checkpoint['loss_scaler'])

    #
    # training
    #

    train(model, train_loader, test_loader, optimizer, criterion, epochs, loss_scaler, lr_scheduler, mixup_fn, device, args)

    wandb.finish()
    torch.distributed.destroy_process_group()


if __name__ == "__main__":
    mode='disabled'
    epochs = 1#100
    batch_size = 64#384
    lr = 1e-3
    model_name = 'efficientvit_m4.r224_in1k'  #'efficientformerv2_s1'
    args = {
        'epochs': epochs,  # general params
        'batch_size': batch_size,
        'num_classes': None,
        'smoothing': 0.1,
        'train_prop': 0.9,
        'wandb_mode': mode,
        'model_name': model_name,
        'save_checkpoints': True,
        'checkpoint_name': None,
        'seed': 0,
        'num_workers': 1,
        'pin_mem': True,
        'device': 'cuda',
        'resume': None,
        'start_epoch': 0,
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
        'warmup_epochs': max(min(epochs-1, 30), 0),#5,  # mustn't be greater than the number of epochs or everything will explode
        'cooldown_epochs': 10,
        'patience_epochs': 10,
        'decay_rate': 0.1,
        'mixup': 0.8,  # mixup parameters
        'cutmix': 1.0,
        'cutmix_minmax': None,
        'mixup_prob': 1.0,
        'mixup_switch_prob': 0.5,
        'mixup_mode': 'batch',
        'rank': None,  # distributed training parameters
        'world_size': None,
        'gpu': None,
        'distributed': None,
        'dist_backend': None,
        'dist_url': None,
        'dist_eval': True,
    }
    main(
        lr=lr,
        batch_size=batch_size,
        epochs=epochs,
        args=args,
        mixup=args['mixup'],
        smoothing=args['smoothing']
    )

