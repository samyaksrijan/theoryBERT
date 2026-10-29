"""Offline English/logic supervision and a new frozen comparison set."""

from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import random
import re

from theorybert.contracts import DFA
from theorybert.formal.dfa import canonicalise
from theorybert.formal.plan import LanguagePlan as P, compile_plan


def key(dfa):
    return json.dumps(canonicalise(dfa).to_dict(), sort_keys=True)


def primitives():
    yield P("ALL")
    yield P("NONE")
    for n in range(1, 9):
        for bits in itertools.product("01", repeat=n):
            pattern = "".join(bits)
            for op in ("STARTS", "ENDS", "CONTAINS", "EXACT"):
                yield P(op, (pattern,))
            if n <= 4:
                yield P("NOT", (P("CONTAINS", (pattern,)),))
    for n in range(17):
        for relation in ("EQ", "LE", "GE"):
            yield P("LENGTH_"+relation, (n,))
            for symbol in "01":
                yield P("COUNT_"+relation, (symbol, n))
    for m in range(2, 9):
        for r in range(m):
            yield P("LENGTH_MOD", (m, r))
            for symbol in "01":
                yield P("COUNT_MOD", (symbol, m, r))


def catalog():
    yield from primitives()
    patterns = ["".join(b) for n in (1, 2, 3) for b in itertools.product("01", repeat=n)]
    for p, q in itertools.product(patterns, repeat=2):
        yield P("AND", (P("STARTS", (p,)), P("ENDS", (q,))))
        yield P("AND", (P("CONTAINS", (p,)), P("NOT", (P("CONTAINS", (q,)),))))
        yield P("OR", (P("STARTS", (p,)), P("ENDS", (q,))))
    for p in patterns:
        for a in "01":
            for r in (0, 1):
                yield P("AND", (P("CONTAINS", (p,)), P("COUNT_MOD", (a, 2, r))))


def clause(plan, style):
    op, args = plan.op, plan.args
    i = style % 10
    if op in ("AND", "OR"):
        a, b = clause(args[0], style), clause(args[1], (style+2)%10)
        return f"both {a} and {b}" if op == "AND" else f"either {a} or {b}, with both allowed"
    if op == "NOT":
        p = args[0].args[0]
        return [f"do not contain {p}", f"avoid the substring {p}", f"never include {p} as consecutive bits", f"have zero occurrences of the block {p}", f"have no match for the pattern {p}", f"exclude {p} everywhere", f"are free of the consecutive pattern {p}", f"have not even one occurrence of {p}", f"keep the forbidden block {p} out", f"never exhibit the contiguous sequence {p}"][i]
    if op in ("ALL", "NONE"):
        return "are unrestricted, including empty input" if op == "ALL" else "are never accepted, including empty input"
    if op in ("STARTS", "ENDS", "CONTAINS", "EXACT"):
        p = args[0]
        return {
            "STARTS": [f"start with {p}", f"begin with {p}", f"have the prefix {p}", f"have {p} at the left edge", f"have leading bits {p}", f"have first {len(p)} bits equal to {p}", f"start with the block {p}, followed by any bits", f"have {p} at the beginning", f"have a front block of {p}", f"have {p} at their left boundary"],
            "ENDS": [f"end with {p}", f"finish with {p}", f"have the suffix {p}", f"have {p} at the right edge", f"have trailing bits {p}", f"have last {len(p)} bits equal to {p}", f"end with the block {p}, preceded by any bits", f"have {p} at the end", f"have a final block of {p}", f"have {p} at their right boundary"],
            "CONTAINS": [f"contain {p}", f"include the substring {p}", f"have {p} as consecutive symbols", f"have {p} as a contiguous block somewhere", f"have at least one occurrence of {p}", f"include the adjacent sequence {p}", f"have a match for {p} anywhere", f"have an uninterrupted block {p} somewhere", f"include {p} without gaps", f"exhibit the unbroken run {p} somewhere"],
            "EXACT": [f"equal exactly {p}", f"are precisely the word {p}", f"have {p} as the entire input", f"are identical to {p}", f"contain exactly the complete word {p}, without extra bits", f"equal {p} with no additional bits", f"have {p} as the sole accepted word", f"match the whole word {p}", f"are the singleton word {p}", f"are exactly the full sequence {p}"]
        }[op][i]
    subject = "total length" if op.startswith("LENGTH") else "number of " + ("zeros" if args[0] == "0" else "ones")
    if op.endswith("MOD"):
        m, r = args[-2:]
        if m == 2 and i % 3 == 0:
            parity = "even" if r == 0 else "odd"
            return f"have an {parity} {subject}"
        return [f"have {subject} equal to {r} modulo {m}", f"have a {subject} leaving remainder {r} on division by {m}", f"have {subject} congruent to {r} mod {m}", f"have {subject} of the form {m}k + {r}", f"have {subject} that is {r} more than a multiple of {m}"][i%5]
    n = args[-1]
    relation = op.split("_")[-1]
    return {
        "EQ": [f"have {subject} exactly {n}", f"have a {subject} equal to {n}", f"have precisely {n} as their {subject}", f"have {subject} neither smaller nor larger than {n}", f"have a {subject} of {n}, exactly"],
        "LE": [f"have {subject} at most {n}", f"have a {subject} no greater than {n}", f"have {subject} between zero and {n} inclusive", f"have a {subject} bounded above by {n}", f"have a {subject} that never exceeds {n}"],
        "GE": [f"have {subject} at least {n}", f"have a {subject} no less than {n}", f"have a {subject} of {n} or more", f"have a {subject} bounded below by {n}", f"have a {subject} that reaches {n}, without an upper bound"],
    }[relation][i%5]


def description(plan, style):
    c = clause(plan, style)
    return [f"Binary strings that {c}.", f"Accept the words over 0 and 1 that {c}.", f"Construct a DFA for binary words that {c}.", f"Recognize the bit strings that {c}."][style%4]


def copyable(plan, text):
    if plan.op in ("STARTS", "ENDS", "CONTAINS", "EXACT"):
        p = plan.args[0]
        return len(p) == 1 or bool(re.search(r"(?<![01])"+p+r"(?![01])", text))
    return all(copyable(a, text) for a in plan.args if isinstance(a, P))


def build():
    frozen = Path("data/challenges/plan-comparison-v2.jsonl")
    if frozen.exists():
        raise FileExistsError("The v2 comparison set is frozen. Choose a new version rather than overwrite it.")
    rng = random.Random(9173)
    old = [json.loads(l) for l in Path("data/generated/english-dfa-v3.jsonl").read_text().splitlines()]
    roles = {key(DFA.from_dict(r["ground_truth_dfa"])): r["split"] for r in old}
    def role_for(k):
        if k in roles:
            return roles[k]
        bucket = int(hashlib.sha256(("plan-stage:"+k).encode()).hexdigest()[:8],16)%100
        return "train" if bucket < 70 else "validation" if bucket < 85 else "test"
    plans, by_language = [], defaultdict(list)
    for plan in catalog():
        try:
            dfa = compile_plan(plan)
        except ValueError:
            continue
        k = key(dfa)
        plans.append((plan, dfa, k))
        by_language[k].append(plan)
    for values in by_language.values():
        values.sort(key=lambda p: (len(p.display()), p.display()))
    rows, seen = [], set()
    def add(text, plan, dfa, role, provenance):
        if text in seen:
            return
        if len(text.split()) > 42:
            return
        seen.add(text)
        k = key(dfa)
        rows.append({"id": hashlib.sha256(text.encode()).hexdigest()[:16], "description": text, "plan": plan.to_dict(), "ground_truth_dfa": dfa.to_dict(), "language_id": hashlib.sha256(k.encode()).hexdigest()[:16], "split": role, "source": provenance})
    covered, omitted = 0, 0
    for record in old:
        dfa = DFA.from_dict(record["ground_truth_dfa"])
        choices = [p for p in by_language.get(key(dfa), []) if copyable(p, record["description"])]
        if not choices:
            omitted += 1
            continue
        add(record["description"], choices[0], dfa, record["split"], "Prior audited English/DFA supervision with equivalent typed-plan annotation")
        covered += 1
    for plan, dfa, k in plans:
        role = role_for(k)
        # Augmentation stays outside all previous held-out language groups.
        styles = rng.sample(range(8), 2) if role == "train" else [8] if role == "validation" else [9]
        for style in styles:
            add(description(plan, style), plan, dfa, role, "Typed-plan supervision generator v1")
    # Retired v1 challenge development can train this new experiment. Its other
    # cases remain regression-only and are never used for gradients.
    retired = [json.loads(l) for l in Path("data/challenges/toc-compiler-v1.jsonl").read_text().splitlines()]
    for r in retired:
        if r["mode"] != "dfa" or r["partition"] != "development":
            continue
        dfa = DFA.from_dict(r["gold_dfa"])
        choices = [p for p in by_language.get(key(dfa),[]) if copyable(p,r["description"])]
        if choices and role_for(key(dfa)) == "train":
            add(r["description"], choices[0], dfa, "train", "Retired v1 development supervision")
    # A distinct wording/template test is frozen before either model is run.
    fresh = []
    candidates = [(p,d,k) for p,d,k in plans if roles.get(k) != "train"]
    rng.shuffle(candidates)
    used_languages = set()
    for plan, dfa, k in candidates:
        role = role_for(k)
        if role == "train" or k in used_languages:
            continue
        text = "For my bit-language recognizer, admit precisely the inputs which " + clause(plan, 9 if role == "test" else 8) + "."
        if len(text.split()) > 42:
            continue
        used_languages.add(k)
        fresh.append({"case_id": hashlib.sha256(text.encode()).hexdigest()[:16], "description": text, "gold_dfa": dfa.to_dict(), "plan": plan.to_dict(), "partition": role, "language_id": hashlib.sha256(k.encode()).hexdigest()[:16], "within_direct_bound": len(dfa.states)<=8, "op": plan.op})
        if sum(r["partition"]=="test" for r in fresh)>=120 and sum(r["partition"]=="validation" for r in fresh)>=80:
            break
    # New comparison wording is not a training/selection target itself. The
    # training file still contains original held-out rows for separate audits.
    withheld = {r["description"] for r in fresh}
    assert not {r["description"] for r in rows if r["split"]=="train"} & withheld
    partitions = defaultdict(set)
    for r in rows:
        partitions[r["language_id"]].add(r["split"])
    assert all(len(v)==1 for v in partitions.values())
    out = Path("data/generated/english-plan-v1.jsonl")
    out.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows))
    fresh_path = Path("data/challenges/plan-comparison-v2.jsonl")
    if fresh_path.exists():
        raise FileExistsError("The v2 comparison set is frozen. Choose a new version rather than overwrite it.")
    fresh_path.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in fresh))
    manifest = {"examples":len(rows),"languages":len(partitions),"splits":dict(Counter(r["split"] for r in rows)),"prior_rows_annotated":covered,"prior_rows_without_copyable_plan":omitted,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"comparison_cases":len(fresh),"comparison_partitions":dict(Counter(r["partition"] for r in fresh)),"comparison_sha256":hashlib.sha256(fresh_path.read_bytes()).hexdigest(),"scope":"Binary regular-language typed programs, copied literal bit spans, counts 0–16, Boolean composition; frozen pretrained BERT features. Comparison wording and protected language groups excluded from training."}
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest,indent=2))
    fresh_path.with_suffix(".manifest.json").write_text(json.dumps({"cases":len(fresh),"sha256":manifest["comparison_sha256"],"partitions":manifest["comparison_partitions"]},indent=2))
    print(json.dumps(manifest,indent=2))
    return manifest


if __name__ == "__main__":
    build()
