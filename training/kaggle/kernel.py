"""Kaggle script kernel: clone the repository and run training/finetune.py. No logic lives here (doc 10 §2).

Pushed with `uvx kaggle kernels push -p training/kaggle`. RUN is the one line that changes between
the pilot, the memory probe, the full run and the untuned control; finetune.py's docstring lists them.
The kernel reads the code from GitHub, so a change has to be pushed there before it runs here.
"""

import subprocess

BRANCH = "feat/week3-d15-data"
RUN = "--max-steps 50 --gguf q4_k_m"  # the pilot


def sh(command: str) -> None:
    print("$", command, flush=True)
    subprocess.run(command, shell=True, check=True)


sh(f"git clone --depth 1 --branch {BRANCH} https://github.com/mdsvr/AeroPatch.git")
sh("pip install -q -r AeroPatch/training/requirements.txt")
sh("pip freeze > /kaggle/working/requirements-frozen.txt")
sh(f"python AeroPatch/training/finetune.py --data /kaggle/input/aeropatch-train --out /kaggle/working/run {RUN}")
