import argparse
import csv
import json
import math
import random
import time
from pathlib import Path
import numpy as np
import torch
from theorybert.contracts import DFA
from theorybert.formal.dfa import canonicalise, equivalent
from theorybert.models.theorybert import (
    build,
    targets,
    structured_loss,
    save_checkpoint,
    load_checkpoint,
)
from theorybert.models.decoding import decode_candidates


def device_for(request="auto"):
    if request == "auto":
        return (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )
    if request == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA is unavailable.")
    if request == "mps" and not torch.backends.mps.is_available():
        raise ValueError("Apple MPS is unavailable.")
    return request


def validation(model, tokenizer, records, config, device):
    model.eval()
    losses = []
    success = 0
    with torch.no_grad():
        for r in records:
            encoded = tokenizer(
                r["description"],
                return_tensors="pt",
                truncation=True,
                max_length=config["max_length"],
            )
            encoded = {
                k: v.to(device)
                for k, v in encoded.items()
                if k in ("input_ids", "attention_mask")
            }
            d = canonicalise(DFA.from_dict(r["ground_truth_dfa"]))
            out = model(**encoded)
            loss, _ = structured_loss(
                out,
                targets([d], config["max_states"], device),
                config.get("loss_weights"),
            )
            losses.append(float(loss))
            pred = next(decode_candidates(out, 1))
            success += equivalent(pred, d)[0]
    return sum(losses) / max(1, len(losses)), success / max(1, len(records))


def train(config, smoke=False, resume=None):
    seed = config.get("seed", 42)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(config.get("cpu_threads", 2))
    output = Path(config["output"])
    output.mkdir(parents=True, exist_ok=True)
    device = device_for(config.get("device", "auto"))
    records = [
        json.loads(l)
        for l in Path(config["dataset"]).read_text().splitlines()
        if l.strip()
    ]
    train_rows = [r for r in records if r["split"] == "train"]
    val_rows = [r for r in records if r["split"] == "validation"]
    if not train_rows or not val_rows:
        raise ValueError("Dataset needs nonempty train and validation splits.")
    if smoke:
        # Tiny random BERT intentionally tests mechanics, not research accuracy.
        config = {
            **config,
            "training_status": "smoke-trained; tiny random backbone",
            "backbone": "tiny-random-bert",
            "device": "cpu",
            "max_length": 48,
            "epochs": 1,
            "batch_size": 2,
        }
        device = "cpu"
        train_rows = train_rows[:6]
        val_rows = val_rows[:2]
        train_rows[0] = {
            **train_rows[0],
            "description": train_rows[0]["description"] + " Σ δ q0",
        }
    else:
        config = {
            **config,
            "training_status": "trained; research performance requires held-out evaluation",
        }
    if resume:
        model, tokenizer, old = load_checkpoint(resume, device)
        audit = old["embedding_audit"]
        for k in ("variant", "max_states", "backbone", "initialisation"):
            if old.get(k) != config.get(k):
                raise ValueError(f"Resume config mismatch: {k}")
    else:
        model, tokenizer, audit = build(config, tiny=smoke)
        model.to(device)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.get("learning_rate", 3e-4),
        weight_decay=0.01,
    )
    start_epoch = 0
    if resume:
        state = torch.load(
            Path(resume) / "weights.pt", map_location=device, weights_only=True
        )
        if state["optimizer"]:
            optimizer.load_state_dict(state["optimizer"])
        start_epoch = state["epoch"] + 1
    frozen = {
        n: p.detach().cpu().clone()
        for n, p in model.named_parameters()
        if not p.requires_grad
    }
    watched = (
        {
            n: p.detach().cpu().clone()
            for n, p in model.named_parameters()
            if p.requires_grad
        }
        if smoke
        else {}
    )
    # Predefined vocabulary is audited against training text only.
    training_text = " ".join(r["description"] for r in train_rows)
    for row in audit:
        row["training_surface_occurrences"] = training_text.count(row["token"])
        row["training_token_id_occurrences"] = sum(
            tokenizer.encode(r["description"], add_special_tokens=False).count(
                tokenizer.convert_tokens_to_ids(row["token"])
            )
            for r in train_rows
        )
    batch_size = config.get("batch_size", 2)
    accum = config.get("gradient_accumulation", 4)
    best = (-1.0, float("-inf"))
    if resume and (output / "training.csv").exists():
        with (output / "training.csv").open() as previous:
            scores = [
                (float(r["validation_equivalence"]), -float(r["validation_loss"]))
                for r in csv.DictReader(previous)
            ]
            if scores:
                best = max(scores)
    start = time.perf_counter()
    logs = []
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for epoch in range(start_epoch, config.get("epochs", 3)):
        random.shuffle(train_rows)
        model.train()
        optimizer.zero_grad()
        parts = []
        batches = math.ceil(len(train_rows) / batch_size)
        for i in range(batches):
            rows = train_rows[i * batch_size : (i + 1) * batch_size]
            encoded = tokenizer(
                [r["description"] for r in rows],
                padding=True,
                truncation=True,
                max_length=config["max_length"],
                return_tensors="pt",
            )
            encoded = {
                k: v.to(device)
                for k, v in encoded.items()
                if k in ("input_ids", "attention_mask")
            }
            ds = [canonicalise(DFA.from_dict(r["ground_truth_dfa"])) for r in rows]
            out = model(**encoded)
            loss, components = structured_loss(
                out,
                targets(ds, config["max_states"], device),
                config.get("loss_weights"),
            )
            if not torch.isfinite(loss):
                raise RuntimeError(
                    "Non-finite loss; inspect initialisation norms and learning rate."
                )
            # Scale the final partial accumulation group by its actual size.
            group_size = min(accum, batches - (i // accum) * accum)
            (loss / group_size).backward()
            if (i + 1) % accum == 0 or i + 1 == batches:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad], 1.0
                )
                optimizer.step()
                optimizer.zero_grad()
            parts.append({k: float(v.detach()) for k, v in components.items()})
        val_loss, accuracy = validation(model, tokenizer, val_rows, config, device)
        log = {
            "epoch": epoch,
            **{k: sum(x[k] for x in parts) / len(parts) for k in parts[0]},
            "validation_loss": val_loss,
            "validation_equivalence": accuracy,
            "elapsed_seconds": time.perf_counter() - start,
        }
        logs.append(log)
        print(json.dumps(log), flush=True)
        score = (accuracy, -val_loss)
        if score > best:
            best = score
            save_checkpoint(
                output / "best", model, tokenizer, config, audit, optimizer, epoch
            )
        save_checkpoint(
            output / "last", model, tokenizer, config, audit, optimizer, epoch
        )
    for n, p in model.named_parameters():
        if n in frozen and not torch.equal(frozen[n], p.detach().cpu()):
            raise AssertionError("Frozen parameter changed: " + n)
    if smoke:
        changed = [
            n
            for n, p in model.named_parameters()
            if n in watched and not torch.equal(watched[n], p.detach().cpu())
        ]
        for category in (
            "extra.weight",
            "extension.",
            "count_head.",
            "accept_head.",
            "transition_head.",
        ):
            if not any(category in n for n in changed):
                raise AssertionError("No update for " + category)
        model.eval()
        encoded = tokenizer("binary Σ δ q0", return_tensors="pt")
        encoded = {
            k: v for k, v in encoded.items() if k in ("input_ids", "attention_mask")
        }
        restored, _, _ = load_checkpoint(output / "last", "cpu")
        with torch.no_grad():
            before = model(**encoded)
            after = restored(**encoded)
        assert all(torch.equal(before[k], after[k]) for k in before), (
            "Checkpoint changed predictions"
        )
    mode = "a" if resume else "w"
    with (output / "training.csv").open(mode, newline="") as f:
        if logs:
            w = csv.DictWriter(f, fieldnames=list(logs[0]))
            if not resume:
                w.writeheader()
            w.writerows(logs)
    if audit:
        final_embeddings = model.backbone.get_input_embeddings().extra.weight.detach()
        for i, row in enumerate(audit):
            row["final_norm"] = float(final_embeddings[i].norm())
    summary = {
        "status": config["training_status"],
        "device": device,
        "frozen_weights_unchanged": True,
        "trainable_parameters": sum(
            p.numel() for p in model.parameters() if p.requires_grad
        ),
        "training_seconds": time.perf_counter() - start,
        "peak_memory_bytes": torch.cuda.max_memory_allocated()
        if device == "cuda"
        else None,
        "embedding_audit": audit,
        "smoke_update_and_reload_checks": smoke,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return output / "best"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/theorybert.json")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--resume")
    a = p.parse_args()
    config = json.loads(Path(a.config).read_text())
    if a.smoke:
        config["output"] = "artifacts/smoke"
    train(config, a.smoke, a.resume)


if __name__ == "__main__":
    main()
