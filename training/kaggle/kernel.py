"""Kaggle script kernel: clone the repository and run training/finetune.py. No logic lives here (doc 10 §2).

Pushed with `uvx kaggle kernels push -p training/kaggle`, which uploads this file: changing RUN
needs no push to GitHub. A change to finetune.py does, because the kernel clones it from there.
"""

import subprocess

BRANCH = "feat/week3-d15-data"
RUNS = {
    "pilot": "--data /kaggle/input/aeropatch-train --max-steps 50 --gguf q4_k_m",
    "probe": "--data /kaggle/input/aeropatch-train-4096 --max-steps 6 --longest 50 --max-seq-length 4096",
    "control": "--data /kaggle/input/aeropatch-train --max-steps 0 --gguf q4_k_m",
}
RUN = RUNS["pilot"]


def sh(command: str) -> None:
    print("$", command, flush=True)
    subprocess.run(command, shell=True, check=True)


sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh(f"git clone --depth 1 --branch {BRANCH} https://github.com/mdsvr/AeroPatch.git")
sh("pip install -q -r AeroPatch/training/requirements.txt")
sh("pip freeze > /kaggle/working/requirements-frozen.txt")
# One GPU: the kernel asks for "GPU T4 x2" (kernel-metadata.json), and the numbers are for one T4.
sh(f"CUDA_VISIBLE_DEVICES=0 python AeroPatch/training/finetune.py --out /kaggle/working/run {RUN}")
