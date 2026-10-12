"""Kaggle script kernel: clone the repository and run training/finetune.py. No logic lives here (doc 10 §2).

Pushed with `uvx kaggle kernels push -p training/kaggle`, which uploads this file: changing ORDER
needs no push to GitHub. A change to finetune.py does, because the kernel clones it from there.

Everything runs under /tmp. /kaggle/working holds 20 GB and becomes the kernel's output, and one
export alone writes the merged model, a 16-bit GGUF and the quantised one. Only what is worth
downloading is copied there: pilot.json, the adapter and the quantised GGUF of each run.
"""

import subprocess

BRANCH = "feat/week3-d15-data"
RUNS = {  # {data}: where Kaggle mounted the dataset named first
    "pilot": ("aeropatch-train", "--data {data} --max-steps 50 --gguf q4_k_m"),
    "probe": ("aeropatch-train-4096", "--data {data} --max-steps 6 --longest 50 --max-seq-length 4096"),
    "control": ("aeropatch-train", "--data {data} --max-steps 0 --gguf q4_k_m"),
}
ORDER = ["pilot", "probe", "control"]  # the first has to pass; a later one may fail and the rest still run


def sh(command: str, check: bool = True) -> int:
    print("$", command, flush=True)
    return subprocess.run(command, shell=True, check=check, cwd="/tmp").returncode


def mounted(dataset: str) -> str:
    """The folder under /kaggle/input that holds a dataset's train.jsonl; its place has changed between images."""
    found = subprocess.run(f"find /kaggle/input -path '*/{dataset}/*' -name train.jsonl", shell=True, check=False,
                           capture_output=True, text=True).stdout.split()
    if not found:
        sh("find /kaggle/input -maxdepth 5 | head -40", check=False)
        raise SystemExit(f"dataset {dataset} is not mounted")
    return found[0].rsplit("/", 1)[0]


data = {name: mounted(dataset) for name, (dataset, _) in RUNS.items() if name in ORDER}
print(data, flush=True)
gpu = sh("nvidia-smi --query-gpu=name,memory.total --format=csv", check=False) == 0
net = sh("git ls-remote https://github.com/mdsvr/AeroPatch.git HEAD", check=False) == 0
if not (gpu and net):  # Kaggle gives both only to an account with a verified phone number
    raise SystemExit(f"GPU: {gpu}, internet: {net}. The run needs both.")
sh(f"git clone --depth 1 --branch {BRANCH} https://github.com/mdsvr/AeroPatch.git")
sh("git -C AeroPatch log --oneline -1")
sh("pip install -q -r AeroPatch/training/requirements.txt")
sh("pip freeze > /kaggle/working/requirements-frozen.txt")
# torch version, GPU, bf16 as torch sees it (emulation counts), bf16 as Unsloth sees it
sh('python -c "import torch; from unsloth import is_bfloat16_supported as u; '
   'print(torch.__version__, torch.cuda.get_device_name(0), torch.cuda.is_bf16_supported(), u())"', check=False)
for name in ORDER:
    out = f"/kaggle/working/{name}"
    # One GPU: the kernel asks for "GPU T4 x2" (kernel-metadata.json), and the numbers are for one T4.
    code = sh(f"CUDA_VISIBLE_DEVICES=0 python AeroPatch/training/finetune.py --out /tmp/runs/{name} "
              + RUNS[name][1].format(data=data[name]),
              check=False)
    sh(f"mkdir -p {out}; cp /tmp/runs/{name}/pilot.json {out}/; cp -r /tmp/runs/{name}/adapter {out}/; "
       f"find /tmp/runs -name '*.gguf' -size -6G -exec mv {{}} {out}/ ';'; rm -rf /tmp/runs/{name}; "
       f"echo {name} exit {code} >> /kaggle/working/status.txt", check=False)
    if code and name == ORDER[0]:
        raise SystemExit(code)
