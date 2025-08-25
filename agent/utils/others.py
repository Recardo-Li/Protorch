import torch
import numpy as np
import random
import os
import signal
import psutil


def setup_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    random.seed(seed)
    # torch.backends.cudnn.deterministic = True


def random_seed():
    torch.seed()
    torch.cuda.seed()
    np.random.seed()
    random.seed()
    # torch.backends.cudnn.deterministic = False


def kill_process(pid):
    """
    Iteratively kill all child processes derived from the given pid, including the pid itself.
    Args:
        pid: Process ID
    """
    current_pid = pid
    child_processes = []
    for process in psutil.process_iter(['pid', 'ppid']):
        if process.info['ppid'] == current_pid:
            child_processes.append(process.info['pid'])

    for child_pid in child_processes:
        kill_process(child_pid)
    
    try:
        os.kill(pid, signal.SIGKILL)
    except Exception as e:
        print(f"Failed to kill {pid}: {e}")
    