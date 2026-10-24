"""Actual measurements only; gate correctness using ground truth is not model accuracy."""

import argparse
import csv
import json
import time
from pathlib import Path
from theorybert.contracts import DFA
from theorybert.formal.dfa import canonicalise, equivalent, validate
from theorybert.pipeline import run_candidates
from theorybert.baselines.predictors import RuleBased, Learned
from theorybert.models.theorybert import load_checkpoint


def fertility(tokenizer, texts):
    # Denominator: whitespace-delimited units, not linguistic words; punctuation remains attached.
    units = sum(len(t.split()) for t in texts)
    return (
        sum(len(tokenizer.encode(t, add_special_tokens=False)) for t in texts) / units
        if units
        else None
    )


def evaluate(predictor, records, budget=5, tokenizer=None, render_videos=False):
    rows = []
    for record in records:
        reference = DFA.from_dict(record["ground_truth_dfa"])
        start = time.perf_counter()
        prediction_error = None
        try:
            candidates = list(predictor.predict(record["description"], budget))
            supported = True
        except ValueError as exc:
            candidates = []
            supported = False
            prediction_error = str(exc)
        prediction_latency = time.perf_counter() - start
        start = time.perf_counter()
        result = run_candidates(
            candidates, reference, record["example_id"], predictor.source, budget
        )
        verification_latency = time.perf_counter() - start
        first = candidates[0] if candidates else None
        valid = bool(first and not validate(first))
        comparable = valid and set(first.alphabet) == set(reference.alphabet)
        raw_eq = equivalent(first, reference)[0] if comparable else False
        # Canonical structure is reachable BFS with alphabet order, WITHOUT minimisation.
        structural = (
            canonicalise(first, False).to_dict()
            == canonicalise(reference, False).to_dict()
            if valid
            else False
        )
        canonical_exact = (
            canonicalise(first).to_dict() == canonicalise(reference).to_dict()
            if valid
            else False
        )
        rendering_latency = None
        if render_videos and result.verified:
            from theorybert.rendering.renderer import render

            _, rendering_latency, _ = render(result.verified, [])
        released = bool(result.verified)
        rows.append(
            {
                "example_id": record["example_id"],
                "language_id": record["language_id"],
                "category": record["metadata"]["category"],
                "notation": record["metadata"].get("notation", "unknown"),
                "source": predictor.source,
                "prediction_error": prediction_error,
                "verification_status": result.reports[-1].status.value,
                "verification_message": result.reports[-1].message,
                "supported": int(supported),
                "raw_equivalence": int(raw_eq),
                "first_candidate_accuracy": int(raw_eq),
                "success_within_budget": int(released),
                "structural_validity": int(valid),
                "canonical_exact_match": int(canonical_exact),
                "transition_table_exact_match": int(structural),
                "released": int(released),
                "released_correct": int(
                    released and equivalent(result.verified.checked(), reference)[0]
                ),
                "incorrect_released": int(
                    released and not equivalent(result.verified.checked(), reference)[0]
                ),
                "attempts": len(result.reports),
                "prediction_seconds": prediction_latency,
                "verification_seconds": verification_latency,
                "rendering_seconds": rendering_latency,
                "fertility": fertility(tokenizer, [record["description"]])
                if tokenizer
                else None,
                "input_truncated": int(
                    len(tokenizer.encode(record["description"]))
                    > predictor.config.get("max_length", 96)
                )
                if tokenizer
                else None,
            }
        )
    return rows


def write_results(rows, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No evaluation rows found.")
    with (output / "results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = {}
    for category in sorted({r["category"] for r in rows}):
        subset = [r for r in rows if r["category"] == category]
        metrics = {}
        for k in (
            "supported",
            "raw_equivalence",
            "first_candidate_accuracy",
            "success_within_budget",
            "structural_validity",
            "canonical_exact_match",
            "transition_table_exact_match",
            "released",
            "prediction_seconds",
            "verification_seconds",
            "rendering_seconds",
            "fertility",
        ):
            vals = [r[k] for r in subset if r[k] is not None]
            metrics[k] = sum(vals) / len(vals) if vals else None
        released = sum(r["released"] for r in subset)
        metrics.update(
            examples=len(subset),
            unique_languages=len({r["language_id"] for r in subset}),
            correctness_among_released=sum(r["released_correct"] for r in subset)
            / released
            if released
            else None,
            incorrect_candidates_released=sum(r["incorrect_released"] for r in subset),
        )
        summary[category] = metrics
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    strata = {}
    for notation in ("plain", "mixed", "notation-heavy"):
        subset = [r for r in rows if r["notation"] == notation]
        values = [r["fertility"] for r in subset if r["fertility"] is not None]
        strata[notation] = {
            "examples": len(subset),
            "mean_per_example_fertility": sum(values) / len(values) if values else None,
            "status": "measured" if values else "not measured",
        }
    (output / "fertility.json").write_text(json.dumps(strata, indent=2))
    lines = [
        "# Evaluation (measured)",
        "",
        "Gate and evaluator use the same independent ground truth. Released correctness is a checker property.",
        "",
        "Prediction source: " + "; ".join(sorted({r["source"] for r in rows})) + ".",
        "",
        "| Category | Examples | Raw equivalence | Within budget | Support coverage | Release coverage | Released correctness |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for c, m in summary.items():
        correctness = m["correctness_among_released"]
        correctness_label = (
            f"{correctness:.3f}" if correctness is not None else "not measured"
        )
        lines.append(
            f"| {c} | {m['examples']} | {m['raw_equivalence']:.3f} | {m['success_within_budget']:.3f} | {m['supported']:.3f} | {m['released']:.3f} | {correctness_label} |"
        )
    (output / "report.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", default="data/examples/sample.jsonl")
    p.add_argument("--checkpoint")
    p.add_argument("--output", default="artifacts/evaluation")
    p.add_argument("--budget", type=int, default=5)
    p.add_argument("--split", default="test")
    p.add_argument("--render", action="store_true")
    a = p.parse_args()
    tokenizer = None
    if a.checkpoint:
        model, tokenizer, config = load_checkpoint(a.checkpoint)
        predictor = Learned(model, tokenizer, config)
    else:
        predictor = RuleBased()
    records = [
        json.loads(l) for l in Path(a.dataset).read_text().splitlines() if l.strip()
    ]
    records = [r for r in records if r["split"] == a.split]
    rows = evaluate(predictor, records, a.budget, tokenizer, a.render)
    write_results(rows, a.output)
    metadata = {
        "checkpoint": a.checkpoint,
        "source": predictor.source,
        "trainable_parameters": sum(
            p.numel() for p in predictor.model.parameters() if p.requires_grad
        )
        if hasattr(predictor, "model")
        else 0,
        "peak_memory_bytes": None,
        "peak_memory_note": "not measured for evaluation; CUDA training peaks are in training summary.json",
        "training_seconds": None,
        "transition_alignment": "reachable BFS canonical graph, fixed alphabet order; complete state/transition table including accepting roles; no minimisation",
        "gate_reference": "same ground truth as evaluator; released correctness is a checker property",
        "aggregation": "per example; unsupported predictions count as incorrect",
    }
    if a.checkpoint:
        summary_path = Path(a.checkpoint).parent / "summary.json"
        if summary_path.exists():
            metadata.update(
                {
                    k: v
                    for k, v in json.loads(summary_path.read_text()).items()
                    if k
                    in ("training_seconds", "peak_memory_bytes", "status", "device")
                }
            )
    Path(a.output, "metadata.json").write_text(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
