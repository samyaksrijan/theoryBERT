"""Run one heavy stage at a time; select on validation, then unseal test once."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from theorybert.training.resources import snapshot


def read(path):
    return json.loads(Path(path).read_text())


def fresh_accuracy(folder, mode, partition="validation"):
    rows = [r for r in map(json.loads, (Path(folder)/"results.jsonl").read_text().splitlines()) if r["mode"] == mode and r["partition"] == partition and r.get("within_scope", True)]
    return sum(r["correct"] for r in rows)/len(rows)


def finish(wait_pid):
    os.nice(8)
    os.environ.update(OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    def status(phase, **extra):
        report = {"phase": phase, "resources": snapshot(), **extra}
        Path("artifacts/challenge-work-status.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report), flush=True)
    status("waiting_for_DFA_training")
    while wait_pid is not None:
        try:
            os.kill(wait_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(5)
    if not Path("artifacts/bert-robust/summary.json").is_file():
        raise RuntimeError("Guarded DFA training did not complete; follow-up jobs were not started.")
    cleanup = []
    for name in ("lower-bert-cache.pt", "lower-bert-cache.json"):
        path = Path("artifacts/bert-robust")/name
        if path.exists():
            cleanup.append({"path": str(path), "bytes": path.stat().st_size})
            path.unlink()
    Path("artifacts/challenge-cache-cleanup.json").write_text(json.dumps(cleanup, indent=2))
    def stage(phase, arguments):
        status(phase)
        with Path("artifacts/"+phase+".log").open("w") as log:
            subprocess.run([sys.executable, *arguments], stdout=log, stderr=subprocess.STDOUT, check=True)
    candidate = "artifacts/bert-robust/best"
    old_dfa, old_grammar = "artifacts/bert-v3/best", "artifacts/bert-grammar"
    stage("challenge-original-validation", ["-m", "theorybert.evaluation.evaluate", "--checkpoint", candidate, "--dataset", "data/generated/english-dfa-v3.jsonl", "--split", "validation", "--output", "artifacts/bert-robust-original-validation"])
    stage("challenge-dfa-validation", ["-m", "theorybert.evaluation.challenge", "--checkpoint", candidate, "--grammar-checkpoint", old_grammar, "--output", "artifacts/challenge-dfa-candidate"])
    plan = read("artifacts/challenge-promotion-plan.json")
    original = read("artifacts/bert-robust-original-validation/summary.json")["semantic"]["raw_equivalence"]
    novel = fresh_accuracy("artifacts/challenge-dfa-candidate", "dfa")
    stage("challenge-dfa-presets", ["scripts/check_bert_presets.py", "--dfa", candidate, "--output", "artifacts/challenge-dfa-presets.json"])
    dfa_pass = original >= plan["original_dfa_validation_floor"] and novel >= plan["baseline_fresh_validation"]["dfa"]["accuracy"] + plan["fresh_dfa_validation_improvement_required"] and read("artifacts/challenge-dfa-presets.json")["passed"]
    selected_dfa = candidate if dfa_pass else old_dfa
    status("DFA_validation_selection", original_validation=original, challenge_validation=novel, selected=selected_dfa)
    stage("challenge-grammar-training", ["-m", "theorybert.models.grammar", "--encoder", selected_dfa, "--output", "artifacts/grammar-robust", "--extra-dataset", "data/generated/grammar-robust.jsonl", "--initialize", old_grammar, "--epochs", "100", "--patience", "15"])
    stage("challenge-pair-validation", ["-m", "theorybert.evaluation.challenge", "--checkpoint", selected_dfa, "--grammar-checkpoint", "artifacts/grammar-robust", "--output", "artifacts/challenge-pair-candidate"])
    grammar_val = fresh_accuracy("artifacts/challenge-pair-candidate", "cfg")
    compiler_val = fresh_accuracy("artifacts/challenge-pair-candidate", "compiler")
    grammar_summary = read("artifacts/grammar-robust/summary.json")
    stage("challenge-grammar-presets", ["scripts/check_bert_presets.py", "--grammar", "artifacts/grammar-robust", "--output", "artifacts/challenge-grammar-presets.json"])
    grammar_pass = grammar_val > plan["baseline_fresh_validation"]["cfg"]["accuracy"] and compiler_val >= plan["baseline_fresh_validation"]["compiler"]["accuracy"] and grammar_summary["best_validation_token_exact"] >= .90 and read("artifacts/challenge-grammar-presets.json")["passed"]
    selected_grammar = "artifacts/grammar-robust" if grammar_pass else old_grammar
    selection = {"selected_dfa": selected_dfa, "selected_grammar": selected_grammar, "dfa_promoted": dfa_pass, "grammar_promoted": grammar_pass, "original_dfa_validation": original, "fresh_dfa_validation": novel, "fresh_cfg_validation": grammar_val, "fresh_compiler_validation": compiler_val, "selection_used_test": False, "challenge_sha256": plan["test_sha256"]}
    Path("artifacts/challenge-selection.json").write_text(json.dumps(selection, indent=2))
    # Selection is frozen above. Only now inspect the sealed challenge test.
    stage("challenge-sealed-before", ["-m", "theorybert.evaluation.challenge", "--checkpoint", old_dfa, "--grammar-checkpoint", old_grammar, "--partitions", "test", "--output", "artifacts/challenge-test-before"])
    stage("challenge-sealed-after", ["-m", "theorybert.evaluation.challenge", "--checkpoint", selected_dfa, "--grammar-checkpoint", selected_grammar, "--partitions", "test", "--output", "artifacts/challenge-test-after"])
    evaluation = "artifacts/bert-robust-evaluation" if dfa_pass else "artifacts/bert-v3-evaluation"
    if dfa_pass:
        stage("challenge-original-test", ["-m", "theorybert.evaluation.evaluate", "--checkpoint", candidate, "--dataset", "data/generated/english-dfa-robust.jsonl", "--output", evaluation])
        stage("challenge-activate-dfa", ["scripts/activate_model.py", "--checkpoint", candidate, "--evaluation", evaluation])
    if grammar_pass:
        active = {"checkpoint": selected_grammar, "encoder_checkpoint": selected_dfa, "summary": selected_grammar+"/summary.json", "evaluation": "artifacts/challenge-test-after", "selection": "Validation-selected, then evaluated once on sealed fresh wording cases; no rule fallback"}
        path = Path("artifacts/active-grammar.json")
        temp = path.with_suffix(".json.partial")
        temp.write_text(json.dumps(active, indent=2))
        temp.replace(path)
    comparison = {"selection": selection, "before": read("artifacts/challenge-test-before/summary.json"), "after": read("artifacts/challenge-test-after/summary.json"), "original_test_after": read(evaluation+"/summary.json"), "scope": "Small frozen challenge set. Some targets are previously trained languages; wording and test cases are new. CFG membership checks are bounded, not a general equivalence proof."}
    Path("artifacts/challenge-comparison.json").write_text(json.dumps(comparison, indent=2))
    status("complete", selection=selection)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-pid", type=int)
    args = parser.parse_args()
    try:
        finish(args.wait_pid)
    except Exception as exc:
        Path("artifacts/challenge-work-error.json").write_text(json.dumps({"error": str(exc), "resources": snapshot()}, indent=2))
        raise
