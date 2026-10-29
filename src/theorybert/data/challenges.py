"""Fresh wording and composition challenges, frozen before model inspection.

Formal constructors are used only for benchmark labels, never live inference.
Known validation/test languages retain their protected assignments.
"""

import argparse
from collections import Counter, deque
import hashlib
import itertools
import json
from pathlib import Path

from nltk import CFG
from theorybert.contracts import DFA
from theorybert.data.generators import pattern_dfa, modulo_dfa
from theorybert.formal.dfa import canonicalise, simulate
from theorybert.formal.regex import regex_to_binary
from theorybert.formal.compiler import ARITHMETIC_GRAMMAR


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def grammar_key(grammar):
    g = CFG.fromstring(grammar)
    return json.dumps((str(g.start()), sorted(str(p) for p in g.productions())))


def product(a, b, operation):
    """Reachable Boolean product for independently labeled supervision."""
    start = (a.start_state, b.start_state)
    names, queue, rows, accepts = {start: "q0"}, deque([start]), {}, []
    while queue:
        s, t = queue.popleft()
        name = names[s, t]
        x, y = s in a.accept_states, t in b.accept_states
        if (x and y) if operation == "and" else (x or y):
            accepts.append(name)
        rows[name] = {}
        for bit in "01":
            pair = (a.transitions[s][bit], b.transitions[t][bit])
            if pair not in names:
                names[pair] = f"q{len(names)}"
                queue.append(pair)
            rows[name][bit] = names[pair]
    return canonicalise(DFA(list(names.values()), list("01"), rows, "q0", accepts))


def complement(dfa):
    dfa = DFA.from_dict(dfa.to_dict())
    dfa.accept_states = [s for s in dfa.states if s not in dfa.accept_states]
    return canonicalise(dfa)


def dfa_cases():
    patterns = ("0", "10", "001", "1101", "01010", "101101", "0010110")
    for p in patterns:
        for family, phrases in {
            "starts": [f"Ignore everything after the first {len(p)} bits: those leading bits must be {p}. Use a binary alphabet.", f"A binary word passes only when {p} is right at its left edge; a later occurrence does not count."],
            "ends": [f"Read a sequence of bits and accept it precisely when its trailing block is {p}.", f"For binary input, require {p} at the right edge. Nothing earlier in the word matters."],
            "contains": [f"In a bit sequence, find {p} as one uninterrupted run somewhere; accept exactly when it occurs.", f"The binary pattern {p} has to occur at least once, possibly overlapping another occurrence."],
        }.items():
            dfa = pattern_dfa(p, family)
            predicate = lambda s, p=p, f=family: s.startswith(p) if f == "starts" else s.endswith(p) if f == "ends" else p in s
            for phrase in phrases:
                yield family, phrase, dfa, predicate, "long_pattern" if len(p) == 7 else "fresh_wording"
        if len(p) <= 5:
            for phrase in [f"Even one occurrence of {p} disqualifies a bit sequence. Otherwise accept it.", f"A binary word is allowed only if the consecutive pattern {p} never appears, including across repeated overlaps."]:
                yield "avoids", phrase, complement(pattern_dfa(p, "contains")), lambda s, p=p: p not in s, "fresh_wording"
    for symbol in "01":
        noun = "zero" if symbol == "0" else "one"
        for n in (0, 2, 4):
            for mode in ("exactly", "at most", "at least"):
                count = str(n) if mode == "exactly" else f"0,{n}" if mode == "at most" else f"{n},"
                regex = f"{1-int(symbol)}*({symbol}{1-int(symbol)}*){{{count}}}"
                phrase = {"exactly": f"For a bit string, the tally of {noun} symbols must be {n}; other bits may appear anywhere.", "at most": f"Allow zero through {n} occurrences of {symbol} in a binary word, and refuse larger tallies.", "at least": f"A sequence over 0 and 1 qualifies after its {n}th occurrence of {symbol}; there is no upper bound on that count."}[mode]
                pred = lambda s, a=symbol, n=n, mode=mode: s.count(a) == n if mode == "exactly" else s.count(a) <= n if mode == "at most" else s.count(a) >= n
                yield "bounded_count", phrase, regex_to_binary(regex), pred, "fresh_wording"
        for modulus, remainder in ((2, 0), (3, 1), (5, 2)):
            phrase = f"Tally the {noun}s in a binary word. Dividing that tally by {modulus} must leave {remainder}; the other symbol does not affect the tally."
            yield "count_modulo", phrase, modulo_dfa(modulus, remainder, symbol), lambda s, a=symbol, m=modulus, r=remainder: s.count(a) % m == r, "fresh_wording"
    for p, q in (("0", "1"), ("01", "10"), ("11", "00"), ("010", "01"), ("101", "10")):
        cases = [
            ("both_ends", f"A binary word must open with {p} and also close with {q}; both requirements apply.", product(pattern_dfa(p, "starts"), pattern_dfa(q, "ends"), "and"), lambda s, p=p, q=q: s.startswith(p) and s.endswith(q)),
            ("contains_without", f"Accept bit strings containing {p}, provided {q} never occurs as a consecutive substring.", product(pattern_dfa(p, "contains"), complement(pattern_dfa(q, "contains")), "and"), lambda s, p=p, q=q: p in s and q not in s),
            ("alternative", f"For binary words, either a prefix of {p} or a suffix of {q} is enough. Having both is also allowed.", product(pattern_dfa(p, "starts"), pattern_dfa(q, "ends"), "or"), lambda s, p=p, q=q: s.startswith(p) or s.endswith(q)),
        ]
        for family, phrase, dfa, pred in cases:
            if len(dfa.states) <= 8:
                yield family, phrase, dfa, pred, "composition"
    for p in ("0", "01", "110", "0101", "10101"):
        yield "literal", f"My binary language has one member, namely {p}. Accept no shorter, longer, or different word.", regex_to_binary(p), lambda s, p=p: s == p, "fresh_wording"
    for m, r in ((2, 1), (3, 0), (4, 2), (7, 3)):
        yield "length_modulo", f"Treat every bit equally. A word's total size must be {r} more than a multiple of {m}.", modulo_dfa(m, r), lambda s, m=m, r=r: len(s) % m == r, "fresh_wording"


def grammar_cases():
    for a, b in (("a", "b"), ("x", "y"), ("0", "1"), ("b", "a"), ("1", "0"), ("y", "x")):
        yield "balanced_count", f"First write some {a}s, then exactly as many {b}s. Zero of each is legal; mixed ordering is illegal. Give a CFG.", f"S -> '{a}' S '{b}' |", a*2+b*2
        yield "balanced_count", f"Produce grammar rules for a block of {a} followed by a block of {b}, with both blocks equally long and possibly empty.", f"S -> '{a}' S '{b}' |", a+b
        yield "balanced_delimiters", f"Let {a} act as an opening bracket and {b} as its closer. Describe arbitrary proper nesting and side-by-side balanced groups with a CFG.", f"S -> '{a}' S '{b}' S |", a+b+a+a+b+b
        yield "ordered_blocks", f"Use a CFG for words consisting of any number of {a}s and then any number of {b}s; the two tallies need not match and either can be zero.", f"S -> '{a}' S | B\nB -> '{b}' B |", a*2+b*3
        x, y = sorted((a, b))
        yield "palindrome", f"Find rules for mirror-symmetric words made from {a} and {b}. Include both parities of length and the empty word.", f"S -> '{x}' S '{x}' | '{y}' S '{y}' | '{x}' | '{y}' |", a+b+b+a
        yield "all_words", f"Generate any finite arrangement of {a} and {b}, with no restriction on order or count. The empty arrangement is included.", f"S -> '{x}' S | '{y}' S |", b+a+a+b
    yield "arithmetic", "Give productions for sums and products of id operands, allowing grouped subexpressions. Products bind tighter than sums.", "E -> E '+' T | T\nT -> T '*' F | F\nF -> '(' E ')' | 'id'", "id+id*id"
    yield "ambiguous", "I want an ambiguous CFG for id plus id plus id: neither left nor right grouping should be privileged.", "E -> E '+' E | 'id'", "id+id+id"


COMPILER_PROMPTS = [
    "Generate an expression grammar with identifier and numeric operands. Support +, -, *, /, parentheses, unary plus/minus, and conventional precedence; binary operators associate left.",
    "I need a CFG for calculator expressions: names or decimal numbers, grouping, signed operands, addition, subtraction, multiplication and division with their usual priorities.",
    "Use id and num leaves. Give unary signs highest priority, then times/divide, then plus/minus; allow parentheses and left-associative binary operations.",
]


def compiler_cases():
    positives = ["a+3*b", "(a+3)*b", "a-b-c", "a/(b/c)", "-(a+3)*b", "--a + +b", "0.5 + .25 * 8", "total_1 / (scale + 2)", "a - -b", "((a))", "3.", "_value2", "1 / 0", "a++b", "a*b/c-d+e"]
    negatives = ["a+*b", "(a+b", "a b", "", "x=3", "f(x)", "a**b", "1e3+2", "a%2", "a.__class__", "a; b", "3..2"]
    for i, source in enumerate(positives + negatives):
        yield COMPILER_PROMPTS[i % len(COMPILER_PROMPTS)], source, i < len(positives)


def build(output="data/challenges/toc-compiler-v1.jsonl"):
    prior = {}
    for name in ("english-dfa-v3.jsonl",):
        path = Path("data/generated") / name
        for line in path.read_text().splitlines():
            row = json.loads(line)
            key = "dfa:" + json.dumps(canonicalise(DFA.from_dict(row["ground_truth_dfa"])).to_dict(), sort_keys=True)
            prior[key] = row["split"]
    for line in Path("artifacts/bert-grammar/dataset.jsonl").read_text().splitlines():
        row = json.loads(line)
        prior["cfg:" + grammar_key(row["grammar"])] = row["split"]
    rows, validated = [], 0
    for family, description, dfa, pred, novelty in dfa_cases():
        dfa = canonicalise(dfa)
        # Validate gold constructors against a separately expressed predicate.
        words = ["".join(bits) for n in range(9) for bits in itertools.product("01", repeat=n)]
        assert all(simulate(dfa, word) == pred(word) for word in words), description
        validated += len(words)
        key = "dfa:" + json.dumps(dfa.to_dict(), sort_keys=True)
        rows.append({"mode": "dfa", "family": family, "description": description, "gold_dfa": dfa.to_dict(), "language_key": key, "novelty": novelty, "within_model_scope": len(dfa.states) <= 8})
    for family, description, grammar, value in grammar_cases():
        rows.append({"mode": "cfg", "family": family, "description": description, "gold_grammar": grammar, "input": value, "language_key": "cfg:" + grammar_key(grammar), "novelty": "fresh_wording"})
    for i, (description, source, valid) in enumerate(compiler_cases()):
        rows.append({"mode": "compiler", "family": "valid_source" if valid else "invalid_source", "description": description, "input": source, "expected_valid": valid, "gold_grammar": ARITHMETIC_GRAMMAR, "language_key": "compiler-program:" + source, "novelty": "fresh_wording"})
    for row in rows:
        key = row["language_key"]
        known = prior.get(key)
        bucket = int(digest("fresh-challenge-v1:" + key)[:8], 16) % 100
        row["partition"] = ("development", "validation", "test")[COMPILER_PROMPTS.index(row["description"])] if row["mode"] == "compiler" else "test" if known == "test" else "validation" if known == "validation" else "development" if bucket < 60 else "validation" if bucket < 80 else "test"
        row["prior_language_split"] = known or "new_language"
        row["case_id"] = digest(row["mode"] + row["description"] + row.get("input", ""))[:16]
        row["language_id"] = digest(key)[:16]
        del row["language_key"]
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError("A frozen challenge set already exists; use a new version/path rather than overwrite it.")
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    manifest = {"version": 1, "examples": len(rows), "by_mode": dict(Counter(r["mode"] for r in rows)), "partitions": dict(Counter(r["partition"] for r in rows)), "sha256": digest(path.read_text()), "independent_gold_membership_checks": validated, "policy": "Frozen before prediction. Inspect development/validation first; test is reserved for the selected final model. Previously protected language splits remain protected. Fresh wording can target previously trained languages and is labeled explicitly."}
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/challenges/toc-compiler-v1.jsonl")
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
