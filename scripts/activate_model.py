"""Activate an evaluated pretrained model; never infer readiness from file names."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def activate(checkpoint, evaluation):
    checkpoint, evaluation = (ROOT / checkpoint).resolve(), (ROOT / evaluation).resolve()
    config = json.loads((checkpoint / "config.json").read_text())
    summary = json.loads((checkpoint.parent / "summary.json").read_text())
    measured = json.loads((evaluation / "summary.json").read_text())["semantic"]
    metadata = json.loads((evaluation / "metadata.json").read_text())
    if not (checkpoint / "weights.pt").is_file():
        raise ValueError("Missing weights")
    if not summary.get("pretrained_bert_weights_changed") or not summary.get("frozen_weights_unchanged"):
        raise ValueError("Fine-tuning audit did not pass")
    if "smoke" in config.get("training_status", "") or not config.get("fine_tune_layers"):
        raise ValueError("Expected a genuinely fine-tuned pretrained BERT checkpoint")
    if (ROOT / metadata["checkpoint"]).resolve() != checkpoint:
        raise ValueError("Evaluation belongs to a different checkpoint")
    if metadata.get("dataset_sha256") != config["dataset_sha256"] or metadata.get("split") != "test":
        raise ValueError("Expected held-out evaluation on the recorded dataset")
    if measured["raw_equivalence"] <= 0 or measured["examples"] < 1:
        raise ValueError("No measured correct learned predictions")
    active = {"checkpoint": str(checkpoint.relative_to(ROOT)), "evaluation": str(evaluation.relative_to(ROOT)), "training_summary": str((checkpoint.parent / "summary.json").relative_to(ROOT)), "pretrained_source": config["pretrained_source"], "pretrained_revision": config["pretrained_revision"], "dataset_sha256": config["dataset_sha256"], "first_candidate_equivalence": measured["raw_equivalence"], "success_within_budget": measured["success_within_budget"], "candidate_budget": metadata["candidate_budget"], "test_examples": measured["examples"], "scope": "Binary regular languages in the trained families, at most eight states; predictions require independent verification for a correctness claim.", "activated_at": datetime.now(timezone.utc).isoformat()}
    path = ROOT / "artifacts/active-model.json"
    if path.is_file():
        previous = json.loads(path.read_text())
        if previous.get("checkpoint") != active["checkpoint"]:
            active["previous_checkpoint"] = previous.get("checkpoint")
    temporary = path.with_suffix(".json.partial")
    temporary.write_text(json.dumps(active, indent=2))
    temporary.replace(path)
    print(json.dumps(active, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="artifacts/bert-engine/best")
    parser.add_argument("--evaluation", default="artifacts/bert-engine-evaluation")
    args = parser.parse_args()
    activate(args.checkpoint, args.evaluation)
