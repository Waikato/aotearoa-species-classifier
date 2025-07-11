import os
import numpy as np
import torch
import torch.distributed as dist
import random


def conv_output_size(width, kernel, padding=0, stride=1):
    #print(np.asarray(((width - kernel + 2*padding)/stride) + 1).astype(int))
    return np.asarray(((width - kernel + 2*padding)/stride) + 1).astype(int)

def running_average(val, mean, count):
    """
    Based on Welford's method:
    M_1 = x_1
    M_k = M_{k-1} + (x_k - M_{k-1}) / (k)
    :param val:
    :param mean:
    :param count:
    :return:
    """
    return mean + (val - mean) / (count + 1)


def get_model_params(model):
    pp = 0
    for p in list(model.parameters()):
        nn = 1
        for s in list(p.size()):
            nn = nn * s
        pp += nn
    return pp


def print_model_params(model):
    print("Number of parameters:")
    pp = 0
    for p in list(model.parameters()):
        nn = 1
        for s in list(p.size()):
            nn = nn * s
        pp += nn
    print(pp)


def print_model_architecture(model):
    # Iterate over the model's parameters and print the information
    total_params = 0
    for name, param in model.named_parameters():
        if param.requires_grad:
            print(f"Layer: {name}, Parameters: {param.numel()}")
            total_params += param.numel()
    #for name, module in model.named_children():
    #    print(f"module: {module}")
    for child in model.children():
        print(child)

    print(f"Total Trainable Parameters: {total_params}")


def set_seed(seed: int) -> None:
    """
    Sets the seeds at a certain value.
    :param seed: the value to be set
    """
    print("Setting seeds ...... \n")
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def setup_for_distributed(is_master):
    """
    This function disables printing when not in master process
    """
    import builtins as __builtin__
    builtin_print = __builtin__.print

    def print(*args, **kwargs):
        force = kwargs.pop('force', False)
        if is_master or force:
            builtin_print(*args, **kwargs)

    __builtin__.print = print


def is_dist_avail_and_initialized():
    if not dist.is_available():
        return False
    if not dist.is_initialized():
        return False
    return True


def get_world_size():  # this is for distributed stuff, might come in handy one day
    if not is_dist_avail_and_initialized():
        return 1
    return dist.get_world_size()


def get_rank():
    if not is_dist_avail_and_initialized():
        return 0
    return dist.get_rank()


def is_main_process():
    return get_rank() == 0


def init_distributed_mode(args):
    print(os.environ)
    print("world size: ", torch.cuda.device_count())
    if 'RANK' in os.environ and 'WORLD_SIZE' in os.environ:
        args.rank = int(os.environ["RANK"])
        args.world_size = int(os.environ['WORLD_SIZE'])
        args.gpu = int(os.environ['LOCAL_RANK'])
    elif 'SLURM_PROCID' in os.environ:
        args.rank = int(os.environ['SLURM_PROCID'])
        args.gpu = args.rank % torch.cuda.device_count()
    else:
        print('Not using distributed mode')
        args.distributed = False
        return

    args.distributed = True

    torch.cuda.set_device(args.gpu)
    args.dist_backend = 'nccl'
    print('| distributed init (rank {}): {}'.format(
        args.rank, args.dist_url), flush=True)
    torch.distributed.init_process_group(backend=args.dist_backend, init_method=args.dist_url,
                                         world_size=args.world_size, rank=args.rank)
    torch.distributed.barrier()
    setup_for_distributed(args.rank == 0)


def setup_distributed(args, rank, world_size):
    """
    Note I ended up not using this, it might be needed if you don't use torchrun for whatever reason
    :param args:
    :param rank:
    :param world_size:
    :return:
    """
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'  # can be any free port

    dist.init_process_group(backend='nccl', rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)

    args.rank=rank
    args.world_size = world_size
    args.gpu = rank
    torch.distributed.barrier()
    setup_for_distributed(args.rank == 0)


class DictToObject:  # handy for holding lots of hyperparameters
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            setattr(self, key, value)

