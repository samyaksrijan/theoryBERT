"""Auditable supervised data: English specifications paired with formal labels.

Constructors are used here for labels only, never to interpret live requests.
"""

import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import random
import re

from theorybert.contracts import DFA
from theorybert.data.generators import pattern_dfa, modulo_dfa, samples
from theorybert.formal.regex import regex_to_binary
from theorybert.pipeline import identity


def semantic_examples(expanded=True):
    for n in range(1, 5):
        for bits in itertools.product("01", repeat=n):
            p = "".join(bits)
            phrases = {
                "starts": ("start with", "begin with", "have the prefix"),
                "ends": ("end in", "finish with", "have the suffix"),
                "contains": ("contain", "include", "have the substring"),
            }
            for kind, words in phrases.items():
                texts = []
                for word in words:
                    texts.extend((
                        f"Binary strings that {word} {p}.",
                        f"Accept a binary string if it {word.replace('have', 'has').replace('contain', 'contains').replace('include', 'includes').replace('start with', 'starts with').replace('begin with', 'begins with').replace('end in', 'ends in').replace('finish with', 'finishes with')} {p}.",
                        f"Over alphabet {{0,1}}, accept exactly the strings that {word} {p}.",
                        f"Build a DFA for strings that {word} {p} over 0 and 1.",
                    ))
                # Natural phrasing belongs in supervised data, never in a live
                # prompt normalizer or a hand-written prediction rule.
                position, part, verb = {
                    "starts": ("beginning", "first", "start"),
                    "ends": ("end", "last", "end"),
                    "contains": ("any position", "consecutive", "contain"),
                }[kind]
                if kind in ("starts", "ends"):
                    continuous = "starting" if kind == "starts" else "ending"
                    noun = "prefix" if kind == "starts" else "suffix"
                    texts.extend([
                        f"Recognize binary strings {continuous} with {p}.",
                        f"I need an automaton for binary words {continuous} with {p}.",
                        f"A sequence of zeros and ones is valid exactly when its {part} {n} symbols are {p}.",
                        f"The string should {verb} with {p}; the other bits can be anything.",
                        f"Accept any combination of 0 and 1 with {p} at the {position}.",
                        f"The {noun} is {p}. Use the binary alphabet.",
                        f"Reject binary strings unless they {verb} with {p}.",
                        f"Only accept binary sequences whose {noun} equals {p}.",
                        f"For my DFA, {p} must appear at the {position} of every accepted binary string.",
                    ])
                else:
                    texts.extend([
                        f"Recognize binary strings containing {p}.",
                        f"I need an automaton for binary words having {p} somewhere inside.",
                        f"The sequence {p} must appear at least once in the binary string.",
                        f"Accept any combination of 0 and 1 with {p} at any position.",
                        f"The binary input needs the substring {p}.",
                        f"Reject binary strings unless they contain {p}.",
                        f"Only accept binary sequences that include {p} as consecutive symbols.",
                        f"For my DFA, {p} must occur somewhere in every accepted binary string.",
                    ])
                yield kind, pattern_dfa(p, kind), texts if expanded else texts[:12]
    for m in range(2, 9):
        for r in range(m):
            for symbol in (None, "0", "1"):
                subject = "length" if symbol is None else f"number of {symbol} symbols"
                texts = [
                    f"Binary strings whose {subject} is {r} modulo {m}.",
                    f"Accept when the {subject} leaves remainder {r} on division by {m}.",
                    f"The {subject} of the binary string must be congruent to {r} mod {m}.",
                    f"Build a DFA over 0 and 1 where the {subject} modulo {m} equals {r}.",
                    f"Σ = {{0,1}}; {subject} ≡ {r} (mod {m}).",
                    f"The language of binary strings with {subject} equal to {m}k + {r}, for an integer k.",
                    f"For a binary input, divide its {subject} by {m}. Accept only if the remainder is {r}.",
                    f"I need a DFA where the {subject} in a binary word is {r} mod {m}.",
                    f"The {subject} should be {r} more than a multiple of {m}.",
                    f"Only accept binary sequences with {subject} congruent to {r} modulo {m}.",
                    f"Calculate the {subject} of a binary sequence. Dividing by {m} must give remainder {r}.",
                    f"A binary string is valid when its {subject} has remainder {r} after division by {m}.",
                ]
                if not expanded:
                    texts = texts[:6]
                if m == 2:
                    parity = "even" if r == 0 else "odd"
                    if symbol is None:
                        texts += [f"Binary strings of {parity} length.", f"Accept binary strings with {parity} length."]
                    else:
                        texts += [f"Binary strings with an {parity} count of {symbol}.", f"Accept binary strings containing an {parity} number of {symbol}s.", f"The number of {symbol}s must be {parity}."]
                        name = "zeros" if symbol == "0" else "ones"
                        if expanded:
                            texts += [f"The binary input must have an {parity} number of {name}.", f"Count the {name} in a binary sequence and accept if that count is {parity}.", f"I want a DFA that accepts exactly binary words with an {parity} number of {symbol}s."]
                yield "length_modulo" if symbol is None else "count_modulo", modulo_dfa(m, r, symbol), texts
    for accept in ([], ["q0"]):
        yield "edge_case", DFA(["q0"], list("01"), {"q0": {"0": "q0", "1": "q0"}}, "q0", accept), (
            ["Accept all binary strings.", "Every binary string is accepted, including the empty string.", "The language is all strings over 0 and 1."] if accept else
            ["Accept no binary strings.", "Reject every binary string.", "The language over 0 and 1 is empty."]
        )


def prepare(output, seed=42, expanded=True):
    groups = {}
    def add(family, dfa, texts, source):
        key = identity(dfa)
        group = groups.setdefault(key, {"dfa": dfa, "family": family, "texts": {}})
        for text in texts:
            group["texts"][text] = source
    for family, dfa, texts in semantic_examples(expanded):
        add(family, dfa, texts, "symbolic specification generator v2")
    external = Path("data/generated/external")
    imported, skipped = 0, Counter()
    descriptions, regexes = external / "kb13-descriptions.txt", external / "kb13-regex.txt"
    if descriptions.exists() and regexes.exists():
        src, tgt = descriptions.read_text().splitlines(), regexes.read_text().splitlines()
        if len(src) != len(tgt):
            raise ValueError("Public dataset alignment mismatch")
        for text, regex in zip(src, tgt):
            try:
                dfa = regex_to_binary(regex)
                if len(dfa.states) == 1:
                    skipped["constant language after binary restriction"] += 1
                    continue
                # Independently check conversion against Python fullmatch on all short strings.
                from theorybert.formal.dfa import simulate
                for n in range(7):
                    for bits in itertools.product("01", repeat=n):
                        value = "".join(bits)
                        if simulate(dfa, value) != bool(re.fullmatch(regex, value)):
                            raise ValueError("independent conversion check failed")
                add("public_regex", dfa, ["Over the binary alphabet {0,1} only, " + text], "DeepRegex/KB13; fullmatch restricted to binary domain")
                imported += 1
            except (ValueError, re.error, OverflowError) as exc:
                skipped[str(exc)] += 1
    rng = random.Random(seed)
    keys = sorted(groups)
    rng.shuffle(keys)
    records = []
    for i, key in enumerate(keys):
        group = groups[key]
        split = "train" if i < .75 * len(keys) else "validation" if i < .875 * len(keys) else "test"
        language = hashlib.sha256(key.encode()).hexdigest()[:16]
        for j, (text, source) in enumerate(group["texts"].items()):
            records.append({"example_id": f"{language}-{j}", "language_id": language, "split": split, "family": group["family"], "description": text, "ground_truth_dfa": group["dfa"].to_dict(), "paraphrase_group_id": language, "test_strings": samples(group["dfa"]), "metadata": {"category": "semantic", "notation": "mixed" if any(c in text for c in "Σ≡") else "plain", "source": source, "split_policy": "equivalent languages grouped before 75/12.5/12.5 split; shared English templates"}})
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    manifest = {"seed": seed, "examples": len(records), "unique_languages": len(groups), "splits": dict(Counter(r["split"] for r in records)), "public_imported": imported, "public_skipped": dict(skipped), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "scope": "binary alphabet; at most eight states; generated families and supported KB13 regex subset"}
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/generated/english-dfa.jsonl")
    parser.add_argument("--base-phrasing", action="store_true", help="Reproduce the initial pilot corpus")
    args = parser.parse_args()
    prepare(args.output, expanded=not args.base_phrasing)
