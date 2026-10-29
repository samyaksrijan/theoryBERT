"""Known product regressions, scored against independent formal fixtures."""

import argparse
import json
from pathlib import Path


def check(dfa_path=None, grammar_path=None):
    import torch
    torch.set_num_threads(2)
    checks = []
    if dfa_path:
        from theorybert.models.predictor import load_predictor
        from theorybert.data.generators import benchmark_examples, pattern_dfa
        from theorybert.formal.dfa import equivalent
        predictor = load_predictor(dfa_path)
        fixtures = [(e["description"], e["dfa"], False) for e in benchmark_examples()]
        fixtures.append(("Binary strings that end with 0101", pattern_dfa("0101", "ends"), True))
        for description, reference, require_first in fixtures:
            candidates = list(predictor.predict(description, 5))
            first = equivalent(candidates[0], reference)[0]
            any_correct = any(equivalent(c, reference)[0] for c in candidates)
            checks.append({"mode": "dfa", "description": description, "first_correct": first, "within_five": any_correct, "passed": first if require_first else any_correct})
        del predictor
    if grammar_path:
        from theorybert.models.grammar import GrammarPredictor, grammar_identity
        from theorybert.formal.cfg import EXAMPLES
        from theorybert.formal.compiler import ARITHMETIC_GRAMMAR
        predictor = GrammarPredictor(grammar_path)
        fixtures = [
            ("Build a context-free grammar for strings of the form a^n b^n for n >= 0.", EXAMPLES["Balanced a / b"][0]),
            ("Arithmetic expressions with identifiers, plus and multiplication, using standard precedence.", EXAMPLES["Arithmetic"][0]),
            ("Ambiguous expressions with id and addition and no operator associativity.", EXAMPLES["Ambiguous expression"][0]),
            ("Arithmetic expressions with identifiers and numbers, plus, minus, multiplication, division, parentheses, and unary signs; use standard precedence and left associativity.", ARITHMETIC_GRAMMAR),
        ]
        for description, reference in fixtures:
            try:
                predicted = predictor.predict(description)
                passed = grammar_identity(predicted) == grammar_identity(reference)
                checks.append({"mode": "cfg", "description": description, "passed": passed, "grammar": predicted})
            except ValueError as exc:
                checks.append({"mode": "cfg", "description": description, "passed": False, "error": str(exc)})
    return {"passed": all(c["passed"] for c in checks), "checks": checks, "scope": "Known product fixtures; not held-out generalization evidence."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dfa")
    parser.add_argument("--grammar")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = check(args.dfa, args.grammar)
    Path(args.output).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
