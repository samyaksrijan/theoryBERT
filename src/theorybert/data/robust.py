"""Failure-driven supervision, with challenge validation/test quarantined."""

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import random

from theorybert.contracts import DFA
from theorybert.data.challenges import product, complement, grammar_key
from theorybert.data.generators import pattern_dfa, modulo_dfa
from theorybert.formal.dfa import canonicalise
from theorybert.formal.regex import regex_to_binary


def dfa_key(dfa):
    return json.dumps(canonicalise(dfa).to_dict(), sort_keys=True)


def richer_dfas():
    for n in range(1, 8):
        for bits in itertools.product("01", repeat=n):
            p = "".join(bits)
            for kind, phrases in {
                "starts": [f"The first {n} characters of an accepted binary word have to spell {p}; anything may follow.", f"Require {p} at the beginning of a bit sequence. Finding it only later is insufficient.", f"Only words with {p} at the leftmost edge belong to this binary language.", f"A bit sequence is admitted precisely if its leading block is {p}.", f"I care about the prefix {p}, not about the rest of a binary word."],
                "ends": [f"Only the final {n} bits matter: an input over 0 and 1 is accepted exactly when they are {p}.", f"Require {p} at the end of a bit sequence; whatever comes before is allowed.", f"Words over 0 and 1 need {p} at their rightmost edge.", f"A binary sequence belongs to the language if its trailing block spells {p}.", f"Look at the suffix of a binary word and accept if that suffix is {p}."],
                "contains": [f"Find the adjacent block {p} anywhere in a binary word and accept if a match exists.", f"Binary words need at least one contiguous occurrence of {p}, with no requirement on its position.", f"The bits {p} must be together somewhere inside the sequence over 0 and 1.", f"Accept a bit sequence whenever {p} occurs as an uninterrupted substring.", f"Search a binary word for {p}. A match anywhere is sufficient, including overlaps."],
            }.items():
                if kind == "starts" and n == 7:
                    continue
                yield kind, pattern_dfa(p, kind), phrases
            if n <= 4:
                yield "avoids", complement(pattern_dfa(p, "contains")), [f"The block {p} is forbidden in binary words; accept a word only when there are zero occurrences.", f"Reject a bit string as soon as {p} appears anywhere, even in an overlap.", f"A binary word belongs only if it has no consecutive occurrence of {p}.", f"Any occurrence of {p} disqualifies a word over 0 and 1."]
            if n <= 6:
                yield "literal", regex_to_binary(p), [f"This language contains just the bit word {p}, with no additional bits allowed.", f"Equality to {p} is the entire acceptance condition for a binary word.", f"Require the whole binary input to be {p}; a matching prefix or suffix alone is insufficient."]
    for a in (None, "0", "1"):
        subject = "total length" if a is None else f"tally of {'zeros' if a == '0' else 'ones'}"
        for n in range(7):
            for kind in ("exactly", "at most", "at least"):
                count = str(n) if kind == "exactly" else f"0,{n}" if kind == "at most" else f"{n},"
                regex = f"[01]{{{count}}}" if a is None else f"{1-int(a)}*({a}{1-int(a)}*){{{count}}}"
                phrases = {
                    "exactly": [f"A binary word qualifies only when its {subject} equals {n}.", f"For inputs over 0 and 1, require a {subject} of precisely {n}; neither more nor less."],
                    "at most": [f"A binary word's {subject} cannot exceed {n}; include every smaller value down to zero.", f"Set an upper bound of {n} on the {subject} of a binary word."],
                    "at least": [f"Set a lower bound of {n} on the {subject} of a binary word; larger values remain valid.", f"A binary word qualifies once its {subject} reaches {n}; there is no maximum."],
                }[kind]
                yield "bounded_count", regex_to_binary(regex), phrases
        for m in range(2, 9):
            for r in range(m):
                yield "length_modulo" if a is None else "count_modulo", modulo_dfa(m, r, a), [f"For binary input, the {subject} must be {r} more than a multiple of {m}.", f"Divide a binary word's {subject} by {m}; a remainder of {r} is required for acceptance."]
    patterns = ["".join(bits) for n in (1, 2, 3) for bits in itertools.product("01", repeat=n)]
    for p, q in itertools.product(patterns, repeat=2):
        specs = [
            ("both_ends", product(pattern_dfa(p, "starts"), pattern_dfa(q, "ends"), "and"), [f"Binary words must both start with {p} and end with {q}.", f"Require a prefix of {p} together with a suffix of {q} in a bit string.", f"The leading block of a binary word is {p}, and its trailing block is {q}; enforce both."]),
            ("contains_without", product(pattern_dfa(p, "contains"), complement(pattern_dfa(q, "contains")), "and"), [f"Binary words must contain {p} but must not contain {q}.", f"Require {p} somewhere in a bit sequence and forbid {q} everywhere.", f"A binary input qualifies when {p} appears at least once and {q} never appears."]),
            ("alternative", product(pattern_dfa(p, "starts"), pattern_dfa(q, "ends"), "or"), [f"Accept binary words that start with {p} or end with {q}, or both.", f"Either a leading {p} or a trailing {q} is sufficient for a binary input.", f"Take the union of words starting with {p} and words ending with {q} over 0 and 1."]),
        ]
        for family, dfa, phrases in specs:
            if len(dfa.states) <= 8:
                yield family, dfa, phrases


def grammar_phrases(family, grammar):
    from nltk import CFG
    terminals = []
    for p in CFG.fromstring(grammar).productions():
        for t in p.rhs():
            if isinstance(t, str) and t not in terminals:
                terminals.append(t)
    a, b = (terminals + ["", ""])[:2]
    # These are offline supervised labels; inference never calls this generator.
    if family == "balanced_count":
        return [f"Describe words with one block of {a} and then a block of {b} of the same size; either both are empty or neither is.", f"Make a CFG where the number of initial {a}s equals the number of final {b}s, without interleaving.", f"First emit n {a} symbols, then n {b} symbols, for any nonnegative n. Supply productions.", f"I need paired counts, not arbitrary mixing: some {a}s followed by precisely as many {b}s. Empty is allowed.", f"A leading block of {a} must be matched one-for-one by a trailing block of {b}. Give a grammar including epsilon."]
    if family == "balanced_delimiters":
        return [f"For a CFG, let {a} open a group and {b} close it. Groups may nest inside others or appear consecutively.", f"Use {a} and {b} as matching delimiters and generate all properly balanced sequences, including empty.", f"Give productions for arbitrary nesting of {a} ... {b} and concatenations of such groups.", f"An opening {a} must have a later matching closing {b}; support nested groups and multiple groups, including no groups."]
    if family == "ordered_blocks":
        return [f"Use a CFG for a run of {a} and then a run of {b}; their counts are independent and either run may be empty.", f"Grammar rules should place every {a} before every {b}, with no equal-count condition and with the empty word allowed.", f"Choose any nonnegative number of {a}s and independently any number of {b}s; concatenate those blocks and give a CFG.", f"All {a} symbols come first and all {b} symbols come last. Unequal block sizes are permitted; provide productions."]
    if family == "palindrome":
        return [f"Give a CFG for mirror-image strings over {a} and {b}, with a possible middle symbol and including epsilon.", f"Accepted words use {a} and {b} and are unchanged by reversal. Include odd lengths, even lengths and zero length.", f"The left half must mirror the right half, using only {a} and {b}; a central symbol is optional. Supply a grammar.", f"Generate palindromes using the terminals {a} and {b}. Include a single symbol, the empty string, and longer mirrors."]
    if family == "all_words":
        return [f"Use a grammar for unrestricted strings made of {a} and {b}; include all orders, all counts and epsilon.", f"Any combination of {a} and {b} is legal, including none. Write a CFG without further restrictions.", f"Every finite word over {a} and {b} should be generated, even empty. Produce grammar rules.", f"A CFG is needed for arbitrary arrangements of {a} and {b}, with no ordering or balancing constraint."]
    if family == "arithmetic":
        return ["Give an expression grammar with id operands, binary addition and multiplication, and parentheses; multiplication has the higher priority.", "Use + for sums and * for products of id. Permit grouping and enforce multiplication before addition in the CFG.", "I need normal precedence for sums and products of identifiers, allowing brackets. Give grammar productions."]
    if family == "ambiguous":
        return ["Give a grammar for id additions that deliberately allows every binary association, such as both groupings of three operands.", "Use E plus E or id as an ambiguous expression grammar, with no precedence or associativity rule."]
    if family == "expression_compiler":
        return ["Give a CFG for arithmetic with id and num operands, + - * /, parenthesized groups and unary signs. Times/divide bind above addition/subtraction, binary groups associate left.", "Grammar rules are needed for a basic calculator: identifiers or decimal values, parentheses, unary plus and minus, and the four arithmetic binary operators with normal precedence.", "Support numbers and names in expressions with signed operands, grouping, sums, differences, products and quotients, using standard left-associative binary precedence.", "Build arithmetic productions with id and num leaves, unary signs, grouping and + - * / binary operators. Unary binds most tightly; multiplication and division precede addition and subtraction."]
    return []


def prepare(challenges="data/challenges/toc-compiler-v1.jsonl"):
    challenge_rows = list(map(json.loads, Path(challenges).read_text().splitlines()))
    heldout_prompts = {r["description"] for r in challenge_rows if r["partition"] != "development"}
    development_keys = {dfa_key(DFA.from_dict(r["gold_dfa"])) for r in challenge_rows if r["mode"] == "dfa" and r["partition"] == "development" and r["within_model_scope"]}
    protected = {}
    for r in challenge_rows:
        if r["mode"] == "dfa" and r["partition"] != "development":
            protected[dfa_key(DFA.from_dict(r["gold_dfa"]))] = r["partition"]
    base = list(map(json.loads, Path("data/generated/english-dfa-v3.jsonl").read_text().splitlines()))
    previous = {dfa_key(DFA.from_dict(r["ground_truth_dfa"])): r["split"] for r in base}
    # Historical validation/test languages always remain outside training.
    for key, split in previous.items():
        if split != "train":
            protected[key] = "validation" if split == "validation" else "test"
    groups = defaultdict(list)
    for row in base:
        groups[dfa_key(DFA.from_dict(row["ground_truth_dfa"]))].append(row)
    rows, seen = [], set()
    rng = random.Random(731)
    for key, values in groups.items():
        if values[0]["split"] == "train":
            if key in protected:
                continue
            values = sorted(values, key=lambda r: hashlib.sha256(r["description"].encode()).hexdigest())[:5]
        rows.extend(values)
        seen.update(r["description"] for r in values)
    def add(family, dfa, descriptions, split=None):
        key = dfa_key(dfa)
        if key in protected:
            role = protected[key]
            split = "validation" if role == "validation" else "test"
        else:
            bucket = int(hashlib.sha256(("robust:"+key).encode()).hexdigest()[:8],16)%100
            split = "train" if key in development_keys else split or ("train" if bucket < 85 else "validation")
        # New test supervision stays in the sealed challenge, not in this
        # training-stage file. Replayed original tests above remain unchanged.
        if split == "test":
            return
        language = hashlib.sha256(key.encode()).hexdigest()[:16]
        for description in descriptions:
            if description in seen or description in heldout_prompts:
                continue
            seen.add(description)
            rows.append({"example_id": "robust-"+hashlib.sha256(description.encode()).hexdigest()[:16], "language_id": language, "split": split, "family": family, "description": description, "ground_truth_dfa": json.loads(key), "paraphrase_group_id": language, "metadata": {"category": "semantic", "notation": "plain", "source": "failure-driven linguistic supervision; formal labels only", "split_policy": "Prior held-out and fresh challenge held-out language groups protected"}})
    for family, dfa, descriptions in richer_dfas():
        # Two different phrasings per formal language keep this a modest run.
        descriptions = rng.sample(descriptions, min(2, len(descriptions)))
        add(family, dfa, descriptions)
    for r in challenge_rows:
        if r["mode"] == "dfa" and r["partition"] == "development" and r["within_model_scope"]:
            add(r["family"], DFA.from_dict(r["gold_dfa"]), [r["description"]], "train")
    # All equivalent DFA labels in a stage must have the same split, including
    # replayed base rows and new descriptions of a known language.
    for row in rows:
        key = dfa_key(DFA.from_dict(row["ground_truth_dfa"]))
        if key in previous and previous[key] == "train" and key not in protected:
            row["split"] = "train"
    path = Path("data/generated/english-dfa-robust.jsonl")
    path.write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in rows))
    grammar_base = list(map(json.loads,Path("artifacts/bert-grammar/dataset.jsonl").read_text().splitlines()))
    grammar_protected = {grammar_key(r["gold_grammar"]): r["partition"] for r in challenge_rows if r["mode"] == "cfg" and r["partition"] != "development"}
    old_splits = {grammar_key(r["grammar"]): r["split"] for r in grammar_base}
    grammar_extra, used = [], set()
    def add_grammar(family, grammar, texts, role=None):
        key = grammar_key(grammar)
        prior = old_splits.get(key)
        split = "test" if prior == "test" or grammar_protected.get(key) == "test" else "validation" if prior == "validation" or grammar_protected.get(key) == "validation" else role or "train"
        if split == "test":
            return
        for text in texts:
            if text in used or text in heldout_prompts:
                continue
            used.add(text)
            grammar_extra.append({"family": family, "grammar": grammar, "description": text, "language_id": hashlib.sha256(key.encode()).hexdigest(), "split": split})
    for row in grammar_base:
        key = grammar_key(row["grammar"])
        if key not in used:
            add_grammar(row["family"],row["grammar"],grammar_phrases(row["family"],row["grammar"]))
            used.add(key)
    for r in challenge_rows:
        if r["partition"] == "development" and r["mode"] in ("cfg", "compiler"):
            add_grammar(r["family"] if r["mode"] == "cfg" else "expression_compiler", r["gold_grammar"], [r["description"]])
    grammar_path = Path("data/generated/grammar-robust.jsonl")
    grammar_path.write_text("".join(json.dumps(r)+"\n" for r in grammar_extra))
    # Audit after the actual files have been written, before any training.
    splits = defaultdict(set)
    for r in rows:
        splits[dfa_key(DFA.from_dict(r["ground_truth_dfa"]))].add(r["split"])
    overlap = [k for k, v in splits.items() if len(v)>1]
    if overlap:
        raise ValueError(f"Equivalent DFA groups cross stage partitions: {len(overlap)}")
    assert not ({r["description"] for r in rows if r["split"] == "train"} & heldout_prompts)
    assert not ({r["description"] for r in grammar_extra if r["split"] == "train"} & heldout_prompts)
    manifest = {"dfa_examples": len(rows), "dfa_splits":dict(Counter(r["split"] for r in rows)), "dfa_languages":len(splits), "grammar_extra":len(grammar_extra), "grammar_splits":dict(Counter(r["split"] for r in grammar_extra)), "heldout_prompt_overlap":0, "dfa_language_split_overlap":0, "challenge_sha256":hashlib.sha256(Path(challenges).read_bytes()).hexdigest(), "dfa_sha256":hashlib.sha256(path.read_bytes()).hexdigest(), "grammar_sha256":hashlib.sha256(grammar_path.read_bytes()).hexdigest()}
    Path("artifacts/challenge-training-data-audit.json").write_text(json.dumps(manifest,indent=2))
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
