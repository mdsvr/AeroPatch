"""Kaggle script kernel: clone the repository and run training/finetune.py. No logic lives here (doc 10 §2).

Pushed with `uvx kaggle kernels push -p training/kaggle`, which uploads this file: changing ORDER
needs no push to GitHub. A change to finetune.py does, because the kernel clones it from there.

Everything runs under /tmp. /kaggle/working holds 20 GB and becomes the kernel's output, and one
export alone writes the merged model, a 16-bit GGUF and the quantised one. Only what is worth
downloading is copied there: pilot.json, the adapter and the quantised GGUF of each run.
"""

import subprocess

BRANCH = "feat/week3-d15-data"
RUNS = {
    "pilot": "--data /kaggle/input/aeropatch-train --max-steps 50 --gguf q4_k_m",
    "probe": "--data /kaggle/input/aeropatch-train-4096 --max-steps 6 --longest 50 --max-seq-length 4096",
    "control": "--data /kaggle/input/aeropatch-train --max-steps 0 --gguf q4_k_m",
}
ORDER = ["pilot"]  # the first has to pass; a later one may fail and the rest still run


def sh(command: str, check: bool = True) -> int:
    print("$", command, flush=True)
    return subprocess.run(command, shell=True, check=check, cwd="/tmp").returncode


sh("nvidia-smi --query-gpu=name,memory.total --format=csv")
sh(f"git clone --depth 1 --branch {BRANCH} https://github.com/mdsvr/AeroPatch.git")
sh("git -C AeroPatch log --oneline -1")
sh("pip install -q -r AeroPatch/training/requirements.txt")
sh("pip freeze > /kaggle/working/requirements-frozen.txt")
for name in ORDER:
    out = f"/kaggle/working/{name}"
    # One GPU: the kernel asks for "GPU T4 x2" (kernel-metadata.json), and the numbers are for one T4.
    code = sh(f"CUDA_VISIBLE_DEVICES=0 python AeroPatch/training/finetune.py --out /tmp/runs/{name} {RUNS[name]}",
              check=False)
    sh(f"mkdir -p {out}; cp /tmp/runs/{name}/pilot.json {out}/; cp -r /tmp/runs/{name}/adapter {out}/; "
       f"find /tmp/runs -name '*.gguf' -size -6G -exec mv {{}} {out}/ ';'; rm -rf /tmp/runs/{name}; "
       f"echo {name} exit {code} >> /kaggle/working/status.txt", check=False)
    if code and name == ORDER[0]:
        raise SystemExit(code)
