import os
import sys
import math
import time
import timm
import torch

import numpy as np
import torch.nn as nn
import torch.cuda.amp as amp
import torch.distributed as dist
import torch.multiprocessing as mp
import torchvision.datasets as datasets
import torchvision.transforms as transforms

from torch.optim import RMSprop
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.tensorboard import SummaryWriter
from pathlib import Path

# number of GPUs
WORLD_SIZE = 4
# batch size per GPU for each model size
BATCH_SIZES = {'s': 256, 'm': 96, 'l': 48}
MODEL_SIZE = sys.argv[1]
BATCH_SIZE = BATCH_SIZES[MODEL_SIZE]
# the first number for the number of epochs for training the classifier
# the last number for unfreezing the entire model and fine-tuning it
# can add more numbers between the two
# each number in the middle unfreezes one block
# from the classifier's side to the input side
EPOCHS = [5, 495]
# specify the split for training
SPLIT = sys.argv[2]
# specify a checkpoint to load if resuming fine-tuning
LOAD_CHECKPOINT = None if sys.argv[3] == 'None' else int(sys.argv[3])
# specify a port to use for distributed data parallelism
PORT = sys.argv[4]
# directory for saving checkpoints and tensorboard logs
checkpoints_dir = Path(f'{MODEL_SIZE}_{SPLIT}')
checkpoints_dir.mkdir(exist_ok = True)

# a worker process managing one GPU
def train(rank):

    # set up distributed data parallelism
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = PORT
    dist.init_process_group(backend='nccl', init_method='env://', world_size=WORLD_SIZE, rank=rank)
    # this might improve performance
    torch.backends.cudnn.benchmark = True
    print('GPU', rank, 'initialised', flush=True)

    # load model pretrained on ImageNet21K data
    model = timm.create_model(f'tf_efficientnetv2_{MODEL_SIZE}_in21k', pretrained=(LOAD_CHECKPOINT is None), num_classes=14991).to(rank)
    torch.cuda.set_device(rank)
    model = torch.compile(nn.parallel.DistributedDataParallel(model, device_ids=[rank], find_unused_parameters=(LOAD_CHECKPOINT < sum(EPOCHS[:-1]) if LOAD_CHECKPOINT is not None else True)))
    criterion = nn.CrossEntropyLoss().to(rank)
    print('GPU', rank, 'model created', flush=True)

    # set up data pipeline
    normalize = transforms.Normalize(mean=[0.5, 0.5, 0.5],
                                     std=[0.5, 0.5, 0.5])
    train_dataset = datasets.ImageFolder(
        f'dataset/{SPLIT}',
        transforms.Compose([
            transforms.RandomResizedCrop(300 if MODEL_SIZE == 's' else 384),
            transforms.RandomHorizontalFlip(),
            transforms.AutoAugment(),
            transforms.ToTensor(),
            normalize,
        ]))
    train_sampler = torch.utils.data.distributed.DistributedSampler(train_dataset, num_replicas=WORLD_SIZE, rank=rank)
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=16, sampler=train_sampler, pin_memory=True)
    print('GPU', rank, 'loader ready', flush=True)

    # start with a frozen model
    steps_per_epoch = len(train_loader)
    current_epoch = 0
    model.requires_grad_(False)

    # iterate through fine-tuning stages
    for stage_i, epochs_i in enumerate(EPOCHS):

        # first stage: train the classifier
        if stage_i == 0:
            scaler = amp.GradScaler()
            print('GPU', rank, 'training started', flush=True)
            model.module.classifier.requires_grad_(True)
            if rank == 0:
                writer = SummaryWriter(str(checkpoints_dir / str(rank)))
                current_time = time.time()
        # last stage: fine-tuning entire model
        elif stage_i == len(EPOCHS) - 1:
            model.module.requires_grad_(True)
        # intermediate stages: unfreeze one convolutional block
        else:
            # unfreeze layers connecting the final block and the classifier
            if stage_i == 1:
                model.module.bn2.requires_grad_(True)
                model.module.conv_head.requires_grad_(True)
            # unfreeze the block
            model.module.blocks[-stage_i].requires_grad_(True)
        # skip stage if loading a later checkpoint
        if LOAD_CHECKPOINT is not None and current_epoch + epochs_i <= LOAD_CHECKPOINT:
            current_epoch += epochs_i
            continue
        # set up optimiser
        optimizer = RMSprop(params = filter(lambda p: p.requires_grad, model.parameters()), lr = 1e-6 * WORLD_SIZE * BATCH_SIZE / 16, alpha=0.9, eps=1e-08, weight_decay=1e-5, momentum=0.9)
        # load checkpoint
        if LOAD_CHECKPOINT is not None and current_epoch <= LOAD_CHECKPOINT:
            map_location = {'cuda:%d' % 0: 'cuda:%d' % rank}
            checkpoint = torch.load(f'{checkpoints_dir}/checkpoint_epoch{LOAD_CHECKPOINT}.pth', map_location = map_location)
            model.module.load_state_dict(checkpoint['model'])
            if current_epoch < LOAD_CHECKPOINT:
                optimizer.load_state_dict(checkpoint['optim'])
            del checkpoint
        # set up exponential learning rate decay
        current_epoch_static = current_epoch
        lr_manager = LambdaLR(optimizer, lambda step: (0.99 ** (float(max(current_epoch_static, LOAD_CHECKPOINT if LOAD_CHECKPOINT is not None else 0)) + float(step) / float(steps_per_epoch))))

        # save one checkpoint before fine-tuning for sanity checking
        if stage_i == 0 and rank == 0 and LOAD_CHECKPOINT is None:
            cp_path = checkpoints_dir / ("checkpoint_epoch0.pth")
            torch.save({
                'epoch': 0,
                'model': model.module.state_dict(),
                'optim': optimizer.state_dict()
            }, str(cp_path))
            print(f"Saved checkpoint to {str(cp_path)}")
        dist.barrier()

        # perform one fine-tuning epoch
        for epoch in range(current_epoch, current_epoch + epochs_i):

            # skip epoch if loading a later checkpoint
            if LOAD_CHECKPOINT is not None and epoch < LOAD_CHECKPOINT:
                current_epoch += 1
                continue
            model.train()
            train_sampler.set_epoch(epoch)
            # perform one mini-batch
            for step, data in enumerate(train_loader):
                inputs = data[0].cuda(rank, non_blocking=True)
                targets = data[1].cuda(rank, non_blocking=True)
                optimizer.zero_grad()
                # mixed-precision computation
                with amp.autocast():
                    outputs = model(inputs)
                    loss = criterion(outputs, targets)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                lr_manager.step()
                scaler.update()
                # print progress
                if rank == 0:
                    print(f"Epoch {epoch} Step {step} GPU {rank} Loss {loss.item():6.4f} Latency {time.time()-current_time:4.3f} LR {optimizer.param_groups[0]['lr']:1.8f}", flush=True)
                    current_time = time.time()
                    # log progress in tensorboard
                    if step % 100 == 99:
                        writer.add_scalar('train/loss', loss.item(), steps_per_epoch * epoch + step)
                        writer.add_scalar('train/lr', optimizer.param_groups[0]['lr'], steps_per_epoch * epoch + step)

            # save a checkpoint per five epochs
            if epoch % 5 == 4:
                if rank == 0:
                    cp_path = checkpoints_dir / ("checkpoint_epoch" + str(epoch + 1) + ".pth")
                    torch.save({
                        'epoch': epoch + 1,
                        'model': model.module.state_dict(),
                        'optim': optimizer.state_dict()
                    }, str(cp_path))
                    print(f"Saved checkpoint to {str(cp_path)}")
                dist.barrier()
            current_epoch = epoch + 1

# spawn worker threads
if __name__ == '__main__':
    os.environ['NCCL_BLOCKING_WAIT'] = '1'
    mp.spawn(train, nprocs = WORLD_SIZE)
