"""LoRA fine-tuning of the local model on the examples of prepare_dataset.py (doc 10).

Runs on a 16 GB GPU (a Kaggle or Colab T4), not on the laptop:

    python training/finetune.py --data <dir> --out <dir> --max-steps 50 --gguf q4_k_m   # the pilot
    python training/finetune.py --data <dir> --out <dir> --max-steps 6 --longest 50 --max-seq-length 4096   # memory probe
    python training/finetune.py --data <dir> --out <dir>                                # the full run
    python training/finetune.py --data <dir> --out <dir> --max-steps 0 --gguf q4_k_m    # untuned control: export only

<dir> holds train.jsonl and val.jsonl. An example is {"messages": [...], "target": ...}. The
prompt is `messages` under the model's chat template with the generation prompt and thinking
off, which is what the local server sends (equal token counts on 25 prompts, 2026-10-12). The
target and the end-of-turn token follow, and only they carry a label: an assistant message
inside `messages` is a failed edit of the student and must not be learned. That is why the loss
is masked by position here, and not with Unsloth's train_on_responses_only.

Everything measured goes to <out>/pilot.json: loss, peak VRAM, seconds per step, examples
dropped for length, and the outputs for a few validation prompts with the verdict of the loop's
own parser.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))  # the repository is cloned, not installed

from aeropatch.agent import edits

BASE = "Qwen/Qwen3.5-4B"
SEED = 3407


def encode(tokenizer, example: dict) -> dict:
    """Token ids and labels of one example. Labels are -100 over the whole prompt."""
    prompt = tokenizer.apply_chat_template(example["messages"], add_generation_prompt=True, enable_thinking=False,
                                           tokenize=False)
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    target_ids = tokenizer(example["target"], add_special_tokens=False)["input_ids"] + [tokenizer.eos_token_id]
    return {"input_ids": prompt_ids + target_ids, "attention_mask": [1] * len(prompt_ids + target_ids),
            "labels": [-100] * len(prompt_ids) + target_ids}


def prepare(tokenizer, examples: list[dict], max_seq_length: int) -> tuple[list[dict], dict]:
    """Encoded examples that fit the sequence length, and what was checked on the way.

    Stops the run when a target would not be learned as written, or when the prompt is not the
    one the local server builds (Ollama's token count is stored with the examples it was sent).
    """
    rows, report = [], {"examples": len(examples), "dropped_for_length": 0, "prompts_checked_against_ollama": 0}
    for n, example in enumerate(examples):
        row = encode(tokenizer, example)
        learned = [i for i in row["labels"] if i != -100]
        if n < 3 and tokenizer.decode(learned, clean_up_tokenization_spaces=False) != example["target"] + tokenizer.eos_token:
            raise SystemExit(f"{example['id']}: the labelled tokens do not decode to the target")
        sent = example.get("prompt_tokens")
        if sent:
            report["prompts_checked_against_ollama"] += 1
            if len(row["input_ids"]) - len(learned) != sent:
                raise SystemExit(f"{example['id']}: {len(row['input_ids']) - len(learned)} prompt tokens here, "
                                 f"{sent} counted by Ollama: the two chat templates differ")
        if len(row["input_ids"]) > max_seq_length:  # never truncated: a cut example loses the end of its target
            report["dropped_for_length"] += 1
        else:
            rows.append(row)
    report["longest"] = max((len(r["input_ids"]) for r in rows), default=0)
    return rows, report


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--data", type=Path, required=True, help="directory with train.jsonl and val.jsonl")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-seq-length", type=int, default=2048)
    p.add_argument("--max-steps", type=int, default=-1, help="50 for the pilot, 0 to export the untuned base")
    p.add_argument("--epochs", type=float, default=2)
    p.add_argument("--rank", type=int, default=16, help="LoRA r, and alpha with it (doc 10 §3)")
    p.add_argument("--longest", type=int, default=0, help="train on the N longest examples only: the memory probe")
    p.add_argument("--gguf", help="merge and export at this quantisation, such as q4_k_m")
    args = p.parse_args()

    # Imported here: the laptop has no GPU libraries, and the tests need encode() only.
    import torch
    from unsloth import FastLanguageModel, is_bfloat16_supported  # isort: skip - before transformers, as Unsloth asks
    from transformers import AutoTokenizer, DataCollatorForSeq2Seq, Trainer, TrainingArguments  # isort: skip

    model, processor = FastLanguageModel.from_pretrained(
        model_name=BASE, max_seq_length=args.max_seq_length, load_in_4bit=False, load_in_16bit=True,
        full_finetuning=False)  # LoRA on the 16-bit base: Unsloth advises against QLoRA for Qwen3.5 (doc 10 §1)
    # Tokens are built and read with the plain tokenizer, the one the template check was made
    # with. The model also takes images, so what Unsloth returns may be a processor; it is kept
    # for saving, because the export may want its files.
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    train, report = prepare(tokenizer, _jsonl(args.data / "train.jsonl"), args.max_seq_length)
    val_examples = _jsonl(args.data / "val.jsonl")
    val, _ = prepare(tokenizer, val_examples, args.max_seq_length)
    if args.longest:
        train = sorted(train, key=lambda r: -len(r["input_ids"]))[:args.longest]
    report.update(vars(args) | {"data": str(args.data), "out": str(args.out), "base": BASE, "trained_on": len(train)})
    args.out.mkdir(parents=True, exist_ok=True)

    if args.max_steps != 0:
        model = FastLanguageModel.get_peft_model(
            model, r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none", random_state=SEED,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            use_gradient_checkpointing="unsloth", max_seq_length=args.max_seq_length)
        bf16 = is_bfloat16_supported()  # False on a T4 (doc 10 §3); torch's own check counts emulation and says True
        # ponytail: transformers' Trainer, not TRL's SFTTrainer: the examples arrive tokenised and
        # masked, so nothing of TRL's text handling (templates, packing) is wanted.
        trainer = Trainer(
            model=model, train_dataset=train, eval_dataset=val,
            data_collator=DataCollatorForSeq2Seq(tokenizer, padding=True, label_pad_token_id=-100),
            args=TrainingArguments(
                output_dir=str(args.out / "checkpoints"), per_device_train_batch_size=1, per_device_eval_batch_size=1,
                gradient_accumulation_steps=8, learning_rate=2e-4, lr_scheduler_type="linear", warmup_ratio=0.05,
                num_train_epochs=args.epochs, max_steps=args.max_steps, optim="adamw_8bit", seed=SEED,
                fp16=not bf16, bf16=bf16, logging_steps=5, eval_strategy="steps", eval_steps=25,
                save_strategy="epoch", report_to="none"))
        torch.cuda.reset_peak_memory_stats()
        start = time.monotonic()
        result = trainer.train()
        report.update({"train_seconds": round(time.monotonic() - start), "steps": result.global_step,
                       "seconds_per_step": round((time.monotonic() - start) / max(1, result.global_step), 1),
                       "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                       "log": trainer.state.log_history})
        model.save_pretrained(str(args.out / "adapter"))
        processor.save_pretrained(str(args.out / "adapter"))

    # A few validation prompts through the trained model, judged by the parser the loop uses (doc 10 §4).
    FastLanguageModel.for_inference(model)
    report["samples"] = []
    for example in [e for e in val_examples if len(e["messages"]) == 2][:5]:
        prompt = tokenizer.apply_chat_template(example["messages"], add_generation_prompt=True, enable_thinking=False,
                                               return_tensors="pt", return_dict=True).to(model.device)
        out = model.generate(**prompt, max_new_tokens=512, do_sample=False)
        text = tokenizer.decode(out[0][prompt["input_ids"].shape[1]:], skip_special_tokens=True)
        path = re.search(r"^Files you may edit: (\S+)$", example["messages"][1]["content"], re.MULTILINE)[1]
        report["samples"].append({"id": example["id"], "parses": not edits.parse(text, {path: ""}).parse_error,
                                  "output": text})
    (args.out / "pilot.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("log", "samples")}, indent=2, default=str))
    print("validation outputs that parse:", sum(s["parses"] for s in report["samples"]), "of", len(report["samples"]))

    if args.gguf:  # merged with the adapter when one was trained; the bare base when --max-steps 0
        model.save_pretrained_gguf(str(args.out / "gguf"), processor, quantization_method=args.gguf)


if __name__ == "__main__":
    main()
