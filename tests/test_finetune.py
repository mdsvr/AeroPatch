"""training/finetune.py: what is learned from an example. The training itself runs on Kaggle."""

import importlib.util

import pytest

from aeropatch.config import ROOT

spec = importlib.util.spec_from_file_location("finetune", ROOT / "training" / "finetune.py")
finetune = importlib.util.module_from_spec(spec)
spec.loader.exec_module(finetune)


class Tokenizer:
    """One token per character; 0 ends a turn."""
    eos_token, eos_token_id = "<end>", 0

    def apply_chat_template(self, messages, add_generation_prompt, enable_thinking, tokenize):
        assert add_generation_prompt and not enable_thinking and not tokenize  # as the local server renders it
        return "".join(f"[{m['role']}]{m['content']}" for m in messages) + "[assistant]"

    def __call__(self, text, add_special_tokens):
        assert not add_special_tokens
        return {"input_ids": [ord(c) for c in text]}

    def decode(self, ids, **_):
        return "".join(self.eos_token if i == 0 else chr(i) for i in ids)


REPAIR = {"id": "S-1#1", "target": "RATIONALE: bind it.\nthe fix",
          "messages": [{"role": "system", "content": "rules"}, {"role": "user", "content": "finding"},
                       {"role": "assistant", "content": "the failed edit"}, {"role": "user", "content": "POC_FAIL"}]}


def test_only_the_target_is_learned_and_never_the_students_failed_edit():
    row = finetune.encode(Tokenizer(), REPAIR)
    prompt = "[system]rules[user]finding[assistant]the failed edit[user]POC_FAIL[assistant]"
    assert row["labels"][:len(prompt)] == [-100] * len(prompt) and -100 not in row["labels"][len(prompt):]
    assert Tokenizer().decode(row["input_ids"]) == prompt + REPAIR["target"] + "<end>"
    assert Tokenizer().decode(row["labels"][len(prompt):]) == REPAIR["target"] + "<end>"
    assert len(row["input_ids"]) == len(row["labels"]) == len(row["attention_mask"])


def test_an_example_over_the_length_is_dropped_whole_and_a_different_prompt_stops_the_run():
    tokens = len(finetune.encode(Tokenizer(), REPAIR)["input_ids"])
    rows, report = finetune.prepare(Tokenizer(), [REPAIR, {**REPAIR, "target": REPAIR["target"] + "!"}], tokens)
    assert len(rows) == 1 and report["dropped_for_length"] == 1 and report["longest_example"] == tokens
    prompt_tokens = tokens - len(REPAIR["target"]) - 1
    _, report = finetune.prepare(Tokenizer(), [{**REPAIR, "prompt_tokens": prompt_tokens}], tokens)
    assert report["prompts_checked_against_ollama"] == 1
    with pytest.raises(SystemExit, match="chat templates differ"):  # Ollama counted another prompt
        finetune.prepare(Tokenizer(), [{**REPAIR, "prompt_tokens": prompt_tokens + 2}], tokens)
