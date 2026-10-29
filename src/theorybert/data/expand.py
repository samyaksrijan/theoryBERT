"""Extend supervision without moving any previously held-out language into train."""

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path

from theorybert.contracts import DFA
from theorybert.data.generators import pattern_dfa, samples
from theorybert.data.prepare import regex_to_binary
from theorybert.pipeline import identity


def additional_examples():
    for n in range(1, 7):
        for bits in itertools.product("01", repeat=n):
            pattern = "".join(bits)
            for kind, verb, noun in (("starts", "start with", "prefix"), ("ends", "end with", "suffix"), ("contains", "contain", "substring")):
                texts = [
                    f"Construct a deterministic finite automaton for binary strings that {verb} {pattern}.",
                    f"Design a DFA over {{0,1}} to accept strings that {verb} {pattern}.",
                    f"Binary words must {verb} {pattern} to be accepted.",
                    f"Accept binary words with the {noun} {pattern}.",
                    f"Make a state machine for binary inputs that {verb} {pattern}.",
                    f"The language consists of binary sequences that {verb} {pattern}.",
                ]
                yield kind, pattern_dfa(pattern, kind), texts
            if n <= 4:
                positive = pattern_dfa(pattern, "contains")
                positive.accept_states = [s for s in positive.states if s not in positive.accept_states]
                yield "avoids", positive, [
                    f"Binary strings that do not contain {pattern}.",
                    f"Reject any binary string containing {pattern}.",
                    f"Accept binary words without the substring {pattern}.",
                    f"The pattern {pattern} must never occur in the binary input.",
                    f"Construct a DFA for binary sequences avoiding {pattern}.",
                    f"No consecutive substring may equal {pattern} over alphabet {{0,1}}.",
                ]
            yield "literal", regex_to_binary(pattern), [
                f"Accept exactly the binary string {pattern}.",
                f"The only accepted word is {pattern} over alphabet {{0,1}}.",
                f"Build a DFA whose language is the singleton {{{pattern}}}.",
                f"Accept {pattern} and reject every other binary string.",
            ]
    for n in range(7):
        for mode, quantifier in (("exactly", ""), ("at least", ","), ("at most", "0,")):
            for symbol in (None, "0", "1"):
                count = f"{quantifier}{n}" if mode == "at most" else f"{n}{quantifier}"
                regex = f"[01]{{{count}}}" if symbol is None else f"{1-int(symbol)}*({symbol}{1-int(symbol)}*){{{count}}}"
                try:
                    dfa = regex_to_binary(regex)
                except ValueError:
                    continue
                subject = "symbols" if symbol is None else ("zeros" if symbol == "0" else "ones")
                yield "bounded_count", dfa, [
                    f"Binary strings with {mode} {n} {subject}.",
                    f"Accept binary words containing {mode} {n} {subject}.",
                    f"Construct a DFA for binary sequences with {mode} {n} {subject}.",
                    f"The binary input must have {mode} {n} {subject}.",
                ]


def expand(base, output):
    base = Path(base)
    records = [json.loads(line) for line in base.read_text().splitlines() if line.strip()]
    groups, seen = {}, set()
    for row in records:
        key = identity(DFA.from_dict(row["ground_truth_dfa"]))
        if key in groups and groups[key]["split"] != row["split"]:
            raise ValueError("Base corpus leaks equivalent languages across splits")
        groups[key] = {"split": row["split"], "language_id": row["language_id"]}
        seen.add((key, row["description"]))
    original = len(records)
    for family, dfa, texts in additional_examples():
        key = identity(dfa)
        lang = hashlib.sha256(key.encode()).hexdigest()[:16]
        if key not in groups:
            bucket = int(hashlib.sha256(("expansion-v1:" + lang).encode()).hexdigest()[:8], 16) % 100
            groups[key] = {"split": "train" if bucket < 75 else "validation" if bucket < 88 else "test", "language_id": lang}
        group = groups[key]
        # The original validation/test rows stay byte-for-byte as records. No
        # paraphrases of those languages become training supervision.
        if group["split"] != "train" and any(r["language_id"] == group["language_id"] for r in records[:original]):
            continue
        for description in texts:
            if (key, description) in seen:
                continue
            seen.add((key, description))
            digest = hashlib.sha256(description.encode()).hexdigest()[:10]
            records.append({"example_id": f"{lang}-v3-{digest}", "language_id": group["language_id"], "split": group["split"], "family": family, "description": description, "ground_truth_dfa": json.loads(key), "paraphrase_group_id": group["language_id"], "test_strings": samples(dfa), "metadata": {"category": "semantic", "notation": "plain", "source": "symbolic specification generator v3", "split_policy": "Original language splits frozen; new equivalent-language groups hash-split 75/13/12"}})
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records))
    manifest = {"examples": len(records), "added_examples": len(records)-original, "unique_languages": len(groups), "splits": dict(Counter(r["split"] for r in records)), "families": dict(Counter(r["family"] for r in records)), "base": str(base), "base_sha256": hashlib.sha256(base.read_bytes()).hexdigest(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "original_splits_preserved": True}
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="data/generated/english-dfa-expanded.jsonl")
    parser.add_argument("--output", default="data/generated/english-dfa-v3.jsonl")
    args = parser.parse_args()
    print(json.dumps(expand(args.base, args.output), indent=2))
