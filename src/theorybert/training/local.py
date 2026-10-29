"""Fine-tune actual upper BERT blocks with a cache of immutable lower blocks.

The cache contains neural activations, never labels or constructed predictions.
Inference runs the entire BERT and learned DFA heads without this cache.
"""

import argparse
import csv
import hashlib
import json
import math
import random
import time
from pathlib import Path

import numpy as np
import torch

from theorybert.contracts import DFA
from theorybert.formal.dfa import canonicalise, equivalent
from theorybert.models.theorybert import build, load_checkpoint, save_checkpoint, targets, structured_loss
from theorybert.training.resources import ResourceGuard
from theorybert.training.train import device_for


def fingerprint(parameters):
    digest = hashlib.sha256()
    for name, parameter in parameters:
        digest.update(name.encode())
        digest.update(parameter.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def first_dfa(out, index):
    n = int(out["count"][index].argmax()) + 1
    states = [f"q{i}" for i in range(n)]
    transitions = out["transition"][index, :n, :, :n].argmax(-1).cpu().tolist()
    accepts = (out["accept"][index, :n] >= 0).cpu().tolist()
    return DFA(states, list("01"), {s: {a: states[transitions[i][int(a)]] for a in "01"} for i, s in enumerate(states)}, "q0", [s for s, active in zip(states, accepts) if active])


def run(config, resume=None, initialize=None):
    seed = config.get("seed", 42)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(2)
    device = device_for(config.get("device", "auto"))
    if device == "mps":
        torch.mps.set_per_process_memory_fraction(.5)
    output = Path(config["output"])
    output.mkdir(parents=True, exist_ok=True)
    guard = ResourceGuard(output, config.get("min_disk_gb", 3), config.get("max_swap_growth_gb", 1.5))
    records = [json.loads(line) for line in Path(config["dataset"]).read_text().splitlines() if line.strip()]
    train_ids = [i for i, r in enumerate(records) if r["split"] == "train"]
    val_ids = [i for i, r in enumerate(records) if r["split"] == "validation"]
    if not train_ids or not val_ids:
        raise ValueError("Nonempty train and validation splits required")
    if not config.get("fine_tune_layers"):
        raise ValueError("This trainer must fine-tune pretrained BERT layers")
    config = {**config, "training_status": "pretrained BERT fine-tuned; held-out metrics available separately", "dataset_sha256": hashlib.sha256(Path(config["dataset"]).read_bytes()).hexdigest(), "training_method": "frozen lower BERT activation cache; upper pretrained BERT blocks and direct structured DFA heads trained with supervision"}
    started = time.perf_counter()
    if resume or initialize:
        model, tokenizer, previous = load_checkpoint(resume or initialize)
        keys = ("dataset_sha256", "fine_tune_layers", "max_states", "max_length", "variant") if resume else ("fine_tune_layers", "max_states", "variant")
        for key in keys:
            if previous.get(key) != config.get(key):
                raise ValueError(f"Resume mismatch: {key}")
        audit = previous["embedding_audit"]
        if initialize:
            config["initial_checkpoint"] = str(initialize)
    else:
        model, tokenizer, audit = build(config)
    for row in audit:
        row["trainable"] = False
        row["note"] = "New embeddings fixed to initial values for immutable lower-layer caching"
    original_frozen = fingerprint((n, p) for n, p in model.named_parameters() if not p.requires_grad)
    original_bert = fingerprint((n, p) for n, p in model.named_parameters() if n.startswith("backbone.") and p.requires_grad)
    encoded = tokenizer([r["description"] for r in records], padding=True, truncation=True, max_length=config["max_length"], return_tensors="pt")
    token_lengths = [len(tokenizer.encode(r["description"])) for r in records]
    config["truncated_examples"] = sum(n > config["max_length"] for n in token_lengths)
    if config["truncated_examples"]:
        raise ValueError("Dataset would be truncated; increase max_length before training")
    mask = encoded["attention_mask"]
    cache = output / "lower-bert-cache.pt"
    cache_meta = {"dataset": config["dataset_sha256"], "length": mask.shape[1], "frozen": original_frozen, "depth": config["fine_tune_layers"]}
    meta_path = cache.with_suffix(".json")
    if cache.exists() and meta_path.exists() and json.loads(meta_path.read_text()) == cache_meta:
        hidden = torch.load(cache, map_location="cpu", weights_only=True, mmap=True)
        print(json.dumps({"phase": "cache_reused", "shape": list(hidden.shape)}), flush=True)
    else:
        model.to(device).eval()
        hidden = torch.empty((len(records), mask.shape[1], model.backbone.config.hidden_size), dtype=torch.float16)
        cache_batch = config.get("cache_batch_size", 4)
        with torch.no_grad():
            for start in range(0, len(records), cache_batch):
                stop = min(start + cache_batch, len(records))
                value = model.encode_lower(encoded["input_ids"][start:stop].to(device), mask[start:stop].to(device))
                hidden[start:stop] = value.cpu().half()
                if start % (cache_batch * 20) == 0:
                    print(json.dumps({"phase": "encoding_frozen_bert", "done": stop, "total": len(records), "resources": guard.check("encoding")}), flush=True)
        torch.save(hidden, cache)
        meta_path.write_text(json.dumps(cache_meta))
        print(json.dumps({"phase": "cache_complete", "seconds": time.perf_counter() - started, "size_mb": cache.stat().st_size / 2**20}), flush=True)
        # Do not keep an anonymous RAM copy of a newly written cache while
        # allocating optimizer state. Reload it as a file-backed mapping just
        # like a resumed run, so the OS can reclaim inactive pages.
        del hidden
        hidden = torch.load(cache, map_location="cpu", weights_only=True, mmap=True)
    # Only the layers that need a backward pass occupy the GPU during training.
    model.to("cpu")
    for layer in model.backbone.encoder.layer[-config["fine_tune_layers"]:]:
        layer.to(device)
    for module in (model.extension, model.norm, model.dropout, model.count_head, model.accept_head, model.transition_head):
        module.to(device)
    if device == "mps":
        torch.mps.empty_cache()
    all_targets = [canonicalise(DFA.from_dict(r["ground_truth_dfa"])) for r in records]
    bert_parameters, head_parameters = [], []
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            (bert_parameters if name.startswith("backbone.") else head_parameters).append(parameter)
    optimizer = torch.optim.AdamW([
        {"params": bert_parameters, "lr": config.get("bert_learning_rate", 3e-5)},
        {"params": head_parameters, "lr": config.get("learning_rate", 3e-4)},
    ], weight_decay=.01)
    initial_epoch = 0
    if resume:
        state = torch.load(Path(resume) / "weights.pt", map_location="cpu", weights_only=True, mmap=True)
        initial_epoch = state["epoch"] + 1
        if state.get("optimizer"):
            optimizer.load_state_dict(state["optimizer"])
        del state
    batch = config.get("batch_size", 8)
    accumulation = config.get("gradient_accumulation", 1)
    best, stale = (-1, -math.inf), 0
    history = output / "training.csv"
    if resume and history.exists():
        with history.open() as f:
            best = max((float(r["validation_equivalence"]), -float(r["validation_loss"])) for r in csv.DictReader(f))
    def forward(ids):
        return model.forward_cached(hidden[ids].float().to(device), mask[ids].to(device))
    for epoch in range(initial_epoch, config.get("epochs", 30)):
        epoch_start = time.perf_counter()
        random.shuffle(train_ids)
        model.train()
        total, seen = 0, 0
        optimizer.zero_grad(set_to_none=True)
        batches = math.ceil(len(train_ids) / batch)
        for step in range(batches):
            ids = train_ids[step * batch:(step + 1) * batch]
            out = forward(ids)
            loss, _ = structured_loss(out, targets([all_targets[i] for i in ids], config["max_states"], device), config.get("loss_weights"))
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite loss")
            group = min(accumulation, batches - step // accumulation * accumulation)
            (loss / group).backward()
            if (step + 1) % accumulation == 0 or step + 1 == batches:
                torch.nn.utils.clip_grad_norm_(bert_parameters + head_parameters, 1)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            total += float(loss.detach()) * len(ids)
            seen += len(ids)
            if step % 40 == 0:
                guard.check(f"epoch-{epoch}-step-{step}")
        model.eval()
        val_loss, success = 0, 0
        with torch.no_grad():
            for start in range(0, len(val_ids), batch):
                ids = val_ids[start:start + batch]
                out = forward(ids)
                loss, _ = structured_loss(out, targets([all_targets[i] for i in ids], config["max_states"], device))
                val_loss += float(loss) * len(ids)
                for j, index in enumerate(ids):
                    success += equivalent(first_dfa(out, j), all_targets[index])[0]
        log = {"epoch": epoch, "train_loss": total / seen, "validation_loss": val_loss / len(val_ids), "validation_equivalence": success / len(val_ids), "epoch_seconds": time.perf_counter() - epoch_start, "elapsed_seconds": time.perf_counter() - started}
        exists = history.exists()
        with history.open("a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(log))
            if not exists:
                writer.writeheader()
            writer.writerow(log)
        print(json.dumps({**log, "resources": guard.check("checkpoint", reserve_gb=1.2)}), flush=True)
        score = (log["validation_equivalence"], -log["validation_loss"])
        if score > best:
            best, stale = score, 0
            save_checkpoint(output / "best", model, tokenizer, config, audit, None, epoch)
        else:
            stale += 1
        if (epoch + 1) % config.get("checkpoint_every", 5) == 0 or epoch + 1 == config["epochs"]:
            save_checkpoint(output / "last", model, tokenizer, config, audit, optimizer, epoch)
        if stale >= config.get("patience", 12):
            break
    final_frozen = fingerprint((n, p) for n, p in model.named_parameters() if not p.requires_grad)
    final_bert = fingerprint((n, p) for n, p in model.named_parameters() if n.startswith("backbone.") and p.requires_grad)
    if original_frozen != final_frozen:
        raise AssertionError("Frozen BERT layers changed")
    if original_bert == final_bert:
        raise AssertionError("Pretrained BERT layers did not update")
    summary = {"status": config["training_status"], "device": device, "training_seconds": time.perf_counter() - started, "fine_tuned_bert_layers": config["fine_tune_layers"], "pretrained_bert_weights_changed": original_bert != final_bert, "frozen_weights_unchanged": original_frozen == final_frozen, "bert_before_sha256": original_bert, "bert_after_sha256": final_bert, "best_validation_equivalence": best[0], "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad), "dataset_sha256": config["dataset_sha256"], "truncated_examples": config["truncated_examples"], "scope": "binary DFA prediction; grammar parsing remains a formal algorithm", "resources": guard.check("complete")}
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    return output / "best"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/local-bert.json")
    parser.add_argument("--resume")
    parser.add_argument("--initialize", help="Warm-start a new data stage with fresh optimizer state")
    args = parser.parse_args()
    if args.resume and args.initialize:
        parser.error("Use either --resume or --initialize")
    run(json.loads(Path(args.config).read_text()), args.resume, args.initialize)
