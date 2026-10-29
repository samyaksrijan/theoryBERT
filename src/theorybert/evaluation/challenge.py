"""Resource-bounded, staged challenge evaluation; no rule-based predictions."""

import argparse
import ast
from collections import Counter
from decimal import Decimal
import hashlib
import itertools
import json
from pathlib import Path
import time

import torch
from nltk import CFG
from nltk.parse import EarleyChartParser

from theorybert.baselines.predictors import Learned
from theorybert.contracts import DFA
from theorybert.data.challenges import grammar_key
from theorybert.formal.cfg import grammar_spec, serialise_tree, check_tree
from theorybert.formal.compiler import lex_expression, compile_expression
from theorybert.formal.dfa import equivalent, canonicalise, validate, trace
from theorybert.models.theorybert import load_checkpoint
from theorybert.models.grammar import GrammarPredictor
from theorybert.rendering.layout import graph_layout, tree_layout
from theorybert.training.resources import ResourceGuard


def graph_correct(dfa):
    nodes, edges = graph_layout(dfa)
    expected = {(s, a, t) for s, row in dfa.transitions.items() for a, t in row.items()}
    actual = {(e["source"], a, e["target"]) for e in edges for a in e["symbols"]}
    return set(nodes) == set(dfa.states) and expected == actual


def recognizer(grammar, word):
    g = CFG.fromstring(grammar)
    if set(word) - {s for p in g.productions() for s in p.rhs() if isinstance(s, str)}:
        return False
    chart = EarleyChartParser(g).chart_parse(list(word))
    return any(edge.is_complete() for edge in chart.select(start=0, end=len(word), lhs=g.start()))


def reference_expression(source):
    def visit(n):
        if isinstance(n, ast.Name):
            return "identifier", n.id
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return "number", Decimal(str(n.value))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            return ("unary +" if isinstance(n.op, ast.UAdd) else "unary -", (visit(n.operand),))
        if isinstance(n, ast.BinOp) and type(n.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            return {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}[type(n.op)], (visit(n.left), visit(n.right))
        raise ValueError("Outside the supported arithmetic expression language")
    return visit(ast.parse(source, mode="eval").body)


def actual_expression(node):
    if node.terminal:
        try:
            return "number", Decimal(node.symbol)
        except Exception:
            return "identifier", node.symbol
    return node.symbol, tuple(actual_expression(c) for c in node.children)


def evaluate(dataset, output, checkpoint, grammar_checkpoint, partitions):
    torch.set_num_threads(2)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    guard = ResourceGuard(output, min_disk_gb=3, max_swap_growth_gb=.75)
    raw = Path(dataset).read_bytes()
    records = [r for r in map(json.loads, raw.decode().splitlines()) if r["partition"] in partitions]
    rows, grammar_predictions = [], {}
    model, tokenizer, config = load_checkpoint(checkpoint)
    learned = Learned(model, tokenizer, config)
    # The immutable encoder can be shared only when the grammar decoder was
    # trained against the exact same weight file; otherwise evaluate sequentially.
    grammar_config = json.loads((Path(grammar_checkpoint) / "config.json").read_text())
    same_encoder = Path(grammar_config["encoder_checkpoint"]).resolve() == Path(checkpoint).resolve()
    def progress(mode, done):
        print(json.dumps({"phase": mode, "done": done, "resources": guard.check(mode)}), flush=True)
    for i, record in enumerate(r for r in records if r["mode"] == "dfa"):
        row = {k: record[k] for k in ("case_id", "language_id", "mode", "family", "partition", "description", "novelty")}
        start = time.perf_counter()
        row.update(correct=False, failure_stage=None, visualization_correct=False, within_scope=record.get("within_model_scope", True))
        try:
            candidates = list(learned.predict(record["description"], 5))
            gold = DFA.from_dict(record["gold_dfa"])
            first = candidates[0]
            row["candidate"] = first.to_dict()
            errors = validate(first)
            eq, witness = equivalent(first, gold) if not errors else (False, None)
            row["correct"], row["counterexample"] = eq, "".join(witness) if witness is not None else None
            row["within_five"] = any(equivalent(c, gold)[0] for c in candidates if not validate(c))
            row["failure_stage"] = None if eq else "structure" if errors else "language_analysis" if row["within_scope"] else "unsupported_state_bound"
            if not errors:
                display = canonicalise(first)
                row["visualization_correct"] = graph_correct(display)
                # Independently walk all short input traces, including ε.
                for word in ("", "0", "1", "0101", "111000"):
                    actual = trace(display, word)
                    current = display.start_state
                    for bit, step in zip(word, actual.steps):
                        assert (step.source, step.symbol, step.destination) == (current, bit, display.transitions[current][bit])
                        current = step.destination
                    assert actual.accepted == (current in display.accept_states)
                if eq and not row["visualization_correct"]:
                    row["failure_stage"] = "visualization"
        except Exception as exc:
            row.update(failure_stage="inference", error=str(exc))
        row["seconds"] = time.perf_counter()-start
        rows.append(row)
        if i % 20 == 0:
            progress("dfa", i+1)
    if not same_encoder:
        del model, tokenizer, learned
        predictor = GrammarPredictor(grammar_checkpoint)
    else:
        predictor = GrammarPredictor(grammar_checkpoint, (model, tokenizer))
    for i, record in enumerate(r for r in records if r["mode"] != "dfa"):
        row = {k: record[k] for k in ("case_id", "language_id", "mode", "family", "partition", "description", "novelty")}
        row.update(input=record["input"], correct=False, failure_stage=None, visualization_correct=False)
        start = time.perf_counter()
        try:
            if record["description"] not in grammar_predictions:
                try:
                    grammar_predictions[record["description"]] = predictor.predict(record["description"])
                except ValueError as exc:
                    grammar_predictions[record["description"]] = exc
            predicted = grammar_predictions[record["description"]]
            if isinstance(predicted, Exception):
                raise predicted
            row["grammar"] = predicted
            row["production_exact"] = grammar_key(predicted) == grammar_key(record["gold_grammar"])
            if record["mode"] == "cfg":
                alphabet = sorted({s for p in CFG.fromstring(record["gold_grammar"]).productions() for s in p.rhs() if isinstance(s, str)})
                if all(len(t) == 1 for t in alphabet):
                    words = ["".join(bits) for n in range(7) for bits in itertools.product(alphabet, repeat=n)]
                    witnesses = [w for w in words if recognizer(predicted, w) != recognizer(record["gold_grammar"], w)]
                    row["bounded_membership_agreement"] = not witnesses
                    row["membership_counterexample"] = witnesses[0] if witnesses else None
                row["correct"] = row["production_exact"] or row.get("bounded_membership_agreement", False)
                row["failure_stage"] = None if row["correct"] else "language_analysis"
                # Test a checked derivation and actual tree layout separately.
                tokens = list(record["input"]) if all(len(t) == 1 for t in alphabet) else record["input"].replace("+", " + ").replace("*", " * ").split()
                try:
                    grammar, spec = grammar_spec(predicted, tokens)
                    parsed = next(iter(EarleyChartParser(grammar).parse(tokens)), None)
                    if parsed is not None:
                        tree = serialise_tree(parsed)
                        errors, _ = check_tree(spec, tree)
                        nodes, links, positions = tree_layout(tree)
                        row["visualization_correct"] = not errors and set(nodes) == set(positions) and len(links) == len(nodes)-1
                    elif row["correct"]:
                        row["failure_stage"] = "parsing"
                except ValueError as exc:
                    row["tree_error"] = str(exc)
                    if row["correct"]:
                        row["failure_stage"] = "parsing"
            else:
                row["expected_valid"] = record["expected_valid"]
                if not row["production_exact"]:
                    row["failure_stage"] = "language_analysis"
                else:
                    try:
                        lexemes = lex_expression(record["input"])
                        grammar, spec = grammar_spec(predicted, [l["token"] for l in lexemes])
                        parsed = next(iter(EarleyChartParser(grammar).parse(spec.input_tokens)), None)
                        if parsed is None:
                            raise ValueError("No derivation for compiler input")
                        tree = serialise_tree(parsed)
                        errors, _ = check_tree(spec, tree)
                        assert not errors, errors
                        compiled, syntax_tree = compile_expression(tree, lexemes)
                        row["compiled"] = True
                        row["ir_semantics_correct"] = actual_expression(syntax_tree) == reference_expression(record["input"])
                        nodes, links, positions = tree_layout(syntax_tree)
                        row["visualization_correct"] = len(links) == len(nodes)-1 and set(nodes) == set(positions)
                        row["correct"] = record["expected_valid"] and row["ir_semantics_correct"] and row["visualization_correct"]
                        row["failure_stage"] = None if row["correct"] else "input_validation" if not record["expected_valid"] else "compiler_lowering"
                    except (ValueError, SyntaxError) as exc:
                        row["compiled"] = False
                        row["correct"] = not record["expected_valid"]
                        row["failure_stage"] = None if row["correct"] else "compiler_parsing"
                        row["error"] = str(exc)
        except Exception as exc:
            row.update(failure_stage="structural_generation", error=str(exc))
        row["seconds"] = time.perf_counter()-start
        rows.append(row)
        if i % 10 == 0:
            progress("grammar/compiler", i+1)
    (output / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    summary = {"dataset_sha256": hashlib.sha256(raw).hexdigest(), "partitions": list(partitions), "checkpoint": str(checkpoint), "grammar_checkpoint": str(grammar_checkpoint), "cases": len(rows), "modes": {}, "failures": dict(Counter(r["failure_stage"] for r in rows if r["failure_stage"])), "resources": guard.check("complete")}
    for mode in ("dfa", "cfg", "compiler"):
        group = [r for r in rows if r["mode"] == mode and r.get("within_scope", True)]
        summary["modes"][mode] = {"cases": len(group), "correct": sum(r["correct"] for r in group), "accuracy": sum(r["correct"] for r in group)/len(group) if group else None, "families": {f: {"cases": len(s := [r for r in group if r["family"] == f]), "correct": sum(r["correct"] for r in s)} for f in sorted({r["family"] for r in group})}}
        summary["modes"][mode]["pipeline_successes"] = sum(r["correct"] and not r["failure_stage"] for r in group)
        summary["modes"][mode]["visualizations_checked"] = sum(r["visualization_correct"] for r in group)
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["# Fresh challenge results", "", "BERT-only prediction. Mathematical references are used for scoring, never for generating predictions.", "", "| Mode | Cases | Correct | Accuracy |", "|---|---:|---:|---:|"]
    for mode, info in summary["modes"].items():
        lines.append(f"| {mode} | {info['cases']} | {info['correct']} | {info['accuracy']:.1%} |")
    lines += ["", "CFG bounded membership is a finite diagnostic, not arbitrary grammar equivalence. Compiler results include correct rejection of invalid sources.", "", "## Failures to review", ""]
    for r in rows:
        if r["failure_stage"]:
            lines += [f"- **{r['case_id']} · {r['failure_stage']}**: {r['description']}" + (f" Input: `{r['input']}`." if "input" in r else "") + (f" Witness: `{r.get('counterexample') or 'ε'}`." if r.get("counterexample") is not None else "")]
    (output / "report.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="data/challenges/toc-compiler-v1.jsonl")
    parser.add_argument("--output", default="artifacts/challenge-baseline")
    parser.add_argument("--checkpoint", default="artifacts/bert-v3/best")
    parser.add_argument("--grammar-checkpoint", default="artifacts/bert-grammar")
    parser.add_argument("--partitions", nargs="+", choices=["development", "validation", "test"], default=["development", "validation"])
    args = parser.parse_args()
    evaluate(args.dataset, args.output, args.checkpoint, args.grammar_checkpoint, args.partitions)
