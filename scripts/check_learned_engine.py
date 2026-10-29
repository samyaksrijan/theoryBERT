"""Audit the actual local model: full BERT executes and rules cannot substitute."""

import json
import torch
from safetensors import safe_open

from theorybert.baselines.predictors import RuleBased
from theorybert.contracts import DFA
from theorybert.data.generators import benchmark_examples, pattern_dfa
from theorybert.formal.dfa import equivalent
from theorybert.web import solve_dfa, learned_checkpoint, ROOT, solve_cfg


def main():
    active = json.loads((ROOT / "artifacts/active-model.json").read_text())
    path = ROOT / active["checkpoint"]
    predictor = learned_checkpoint(str(path), (path / "weights.pt").stat().st_mtime_ns, (path / "config.json").stat().st_mtime_ns)
    calls = []
    handle = predictor.model.backbone.register_forward_hook(lambda *args: calls.append(True))
    original_rule = RuleBased.predict
    def forbidden(*args, **kwargs):
        raise AssertionError("A learned-mode request invoked the rule baseline")
    RuleBased.predict = forbidden
    findings = []
    try:
        for example in benchmark_examples():
            result, _ = solve_dfa({"source": "learned", "description": example["description"], "input": example["test"], "example_id": example["id"], "checkpoint": str(path), "budget": 5}, lambda _: None)
            findings.append({"name": example["name"], "source": result["source"], "status": result["status"], "verified": result["verified"], "attempts": len(result["reports"])})
        result, private = solve_dfa({"source": "learned", "description": "Please recognize binary strings ending with 10.", "input": "110", "checkpoint": str(path)}, lambda _: None)
        assert result["graph"] and result["trace"] and not result["verified"]
        assert not result["renderable"] and private["evidence"] is None
        # Ground truth is used only for this audit, never passed to inference.
        custom_correct = equivalent(DFA.from_dict(result["dfa"]), pattern_dfa("10"))[0]
        assert custom_correct
        findings.append({"name": "Custom English preview", "status": result["status"], "accepted": result["trace"]["accepted"], "independent_audit_equivalence": custom_correct, "dfa": result["dfa"]})
        assert len(calls) == 4
    finally:
        RuleBased.predict = original_rule
        handle.remove()
    cfg, _ = solve_cfg({"grammar": "S -> 'x' S 'y' |", "input": "x x y y"}, lambda _: None)
    assert cfg["verified"] and cfg["layouts"][0]
    state = torch.load(path / "weights.pt", map_location="cpu", weights_only=True, mmap=True)["model"]
    with safe_open(ROOT / "artifacts/pretrained/bert-base-uncased/model.safetensors", framework="pt") as original:
        upper = "encoder.layer.11.attention.self.query.weight"
        lower = "encoder.layer.0.attention.self.query.weight"
        upper_delta = float((state["backbone." + upper] - original.get_tensor("bert." + upper)).abs().mean())
        lower_unchanged = torch.equal(state["backbone." + lower], original.get_tensor("bert." + lower))
    assert upper_delta > 0 and lower_unchanged
    report = {"full_bert_forward_calls": len(calls), "rule_fallback_disabled_during_audit": True, "pretrained_upper_bert_mean_weight_change": upper_delta, "original_lower_bert_layer_unchanged": lower_unchanged, "findings": findings, "custom_cfg_verified": cfg["verified"]}
    target = ROOT / "artifacts/learned-engine-audit.json"
    target.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
