"""Symbolic constructors are dataset/reference tools, never learned predictions."""

import argparse
import hashlib
import itertools
import json
import random
from pathlib import Path
from theorybert.contracts import DFA, BenchmarkRecord
from theorybert.formal.dfa import canonicalise, simulate
from theorybert.pipeline import identity


def pattern_dfa(pattern, kind="ends"):
    if not pattern or set(pattern) - {"0", "1"}:
        raise ValueError("Use a nonempty binary pattern.")
    n = len(pattern)
    states = [f"q{i}" for i in range(n + 1)]
    transitions = {}
    if kind == "starts":
        states.append("dead")
        for i, s in enumerate(states):
            transitions[s] = {
                a: (
                    "dead"
                    if s == "dead"
                    else s
                    if i == n
                    else f"q{i + 1}"
                    if a == pattern[i]
                    else "dead"
                )
                for a in "01"
            }
    elif kind in ("ends", "contains"):
        for i, s in enumerate(states):
            transitions[s] = {}
            for a in "01":
                if i == n and kind == "contains":
                    j = n
                else:
                    suffix = pattern[:i] + a
                    j = max(k for k in range(n + 1) if suffix.endswith(pattern[:k]))
                transitions[s][a] = f"q{j}"
    else:
        raise ValueError("Unknown pattern family.")
    return canonicalise(DFA(states, list("01"), transitions, "q0", [f"q{n}"]))


def modulo_dfa(modulus, remainder, symbol=None):
    if not 1 <= modulus <= 8 or not 0 <= remainder < modulus:
        raise ValueError("Invalid modulo parameters.")
    states = [f"q{i}" for i in range(modulus)]
    return canonicalise(
        DFA(
            states,
            list("01"),
            {
                s: {
                    a: states[(i + int(symbol is None or a == symbol)) % modulus]
                    for a in "01"
                }
                for i, s in enumerate(states)
            },
            "q0",
            [states[remainder]],
        )
    )


def intersection(a, b):
    pairs = list(itertools.product(a.states, b.states))
    names = {p: f"x{i}" for i, p in enumerate(pairs)}
    return canonicalise(
        DFA(
            list(names.values()),
            list("01"),
            {
                names[p]: {
                    s: names[(a.transitions[p[0]][s], b.transitions[p[1]][s])]
                    for s in "01"
                }
                for p in pairs
            },
            names[(a.start_state, b.start_state)],
            [
                names[p]
                for p in pairs
                if p[0] in a.accept_states and p[1] in b.accept_states
            ],
        )
    )


def samples(d):
    pool = ["".join(p) for n in range(6) for p in itertools.product("01", repeat=n)]
    yes = [s for s in pool if simulate(d, s)][:4]
    no = [s for s in pool if not simulate(d, s)][:4]
    return [
        {"string": s, "accepted": simulate(d, s)}
        for s in dict.fromkeys([""] + yes + no)
    ]


def semantic_targets():
    out = []
    for n in (1, 2, 3):
        for bits in itertools.product("01", repeat=n):
            p = "".join(bits)
            for kind in ("starts", "ends", "contains"):
                phrase = {
                    "starts": "start with",
                    "ends": "end in",
                    "contains": "contain",
                }[kind]
                out.append(
                    (
                        kind,
                        pattern_dfa(p, kind),
                        [
                            f"Binary strings that {phrase} {p}.",
                            f"Over alphabet {{0,1}}, accept exactly the strings that {phrase} the pattern {p}.",
                            f"Σ = {{0,1}}; language: strings that {phrase} {p}.",
                        ],
                    )
                )
    for m in range(2, 6):
        for r in range(m):
            for symbol in (None, "0", "1"):
                subject = "length" if symbol is None else f"number of {symbol} symbols"
                texts = [
                    f"Binary strings whose {subject} is {r} modulo {m}.",
                    f"Accept when the {subject} leaves remainder {r} on division by {m}.",
                    f"Σ = {{0,1}}; {subject} ≡ {r} (mod {m}).",
                ]
                if m == 2 and symbol is not None:
                    texts.append(
                        f"Binary strings with an {'even' if r == 0 else 'odd'} count of {symbol}."
                    )
                out.append(
                    (
                        "length_modulo" if symbol is None else "count_modulo",
                        modulo_dfa(m, r, symbol),
                        texts,
                    )
                )
    a, b = pattern_dfa("01", "contains"), modulo_dfa(2, 0, "1")
    out.append(
        (
            "combination",
            intersection(a, b),
            ["Binary strings that contain 01 and have an even count of 1."],
        )
    )
    for accept in ([], ["q0"]):
        out.append(
            (
                "edge_case",
                DFA(["q0"], list("01"), {"q0": {"0": "q0", "1": "q0"}}, "q0", accept),
                [
                    "Accept all binary strings, including ε."
                    if accept
                    else "Accept no binary strings."
                ],
            )
        )
    return out


def generate(seed=42, random_languages=24, max_states=8):
    rng = random.Random(seed)
    targets = semantic_targets()
    seen = {identity(d) for _, d, _ in targets}
    added = 0
    for _ in range(max(100, random_languages * 50)):
        if added >= random_languages:
            break
        n = rng.randint(2, max_states)
        states = [f"q{i}" for i in range(n)]
        d = canonicalise(
            DFA(
                states,
                list("01"),
                {s: {a: rng.choice(states) for a in "01"} for s in states},
                "q0",
                [s for s in states if rng.random() < 0.5],
            )
        )
        key = identity(d)
        if key in seen:
            continue
        seen.add(key)
        added += 1
        desc = f"Structural reconstruction: states {', '.join(d.states)}; start {d.start_state}; accepting states {', '.join(d.accept_states) or 'none'}. "
        desc += " ".join(
            f"δ({s},{a}) = {t}."
            for s, row in d.transitions.items()
            for a, t in row.items()
        )
        targets.append(("structural_reconstruction", d, [desc]))
    if added < random_languages:
        raise ValueError(
            "Insufficient unique languages. Reduce --random-languages or increase --max-states."
        )
    grouped = {}
    for family, d, texts in targets:
        if len(d.states) > max_states:
            continue
        key = identity(d)
        if key not in grouped:
            grouped[key] = [family, d, []]
        grouped[key][2].extend(texts)
    keys = sorted(grouped)
    rng.shuffle(keys)
    records = []
    for i, key in enumerate(keys):
        family, d, texts = grouped[key]
        split = (
            "train"
            if i < 0.7 * len(keys)
            else "validation"
            if i < 0.85 * len(keys)
            else "test"
        )
        lid = hashlib.sha256(key.encode()).hexdigest()[:16]
        for j, text in enumerate(dict.fromkeys(texts)):
            records.append(
                BenchmarkRecord(
                    f"{lid}-{j}",
                    lid,
                    split,
                    family,
                    text,
                    d.to_dict(),
                    lid,
                    samples(d),
                    {
                        "seed": seed,
                        "category": "structural"
                        if family == "structural_reconstruction"
                        else "semantic",
                        "notation": "notation-heavy"
                        if family == "structural_reconstruction"
                        else "mixed"
                        if any(c in text for c in "Σδ≡ε")
                        else "plain",
                        "split_policy": "language-grouped; held-out canonical targets; shared templates",
                    },
                ).to_dict()
            )
    return records


def benchmark_examples():
    return [
        {
            "name": "Ends in 01",
            "description": "Binary strings that end in 01.",
            "dfa": pattern_dfa("01", "ends"),
            "test": "1101",
            "id": "manual-suffix-01",
        },
        {
            "name": "Contains 01",
            "description": "Binary strings that contain 01.",
            "dfa": pattern_dfa("01", "contains"),
            "test": "010",
            "id": "manual-contains-01",
        },
        {
            "name": "Even number of 1s",
            "description": "Binary strings with an even count of 1.",
            "dfa": modulo_dfa(2, 0, "1"),
            "test": "1010",
            "id": "manual-even-ones",
        },
    ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="data/generated/dataset.jsonl")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--random-languages", type=int, default=24)
    p.add_argument("--max-states", type=int, default=8)
    a = p.parse_args()
    records = generate(a.seed, a.random_languages, a.max_states)
    # Manual demonstration/challenge languages stay outside research training.
    excluded = {identity(e["dfa"]) for e in benchmark_examples()}
    records = [
        r
        for r in records
        if identity(DFA.from_dict(r["ground_truth_dfa"])) not in excluded
    ]
    path = Path(a.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    print(
        json.dumps(
            {
                "examples": len(records),
                "unique_languages": len({r["language_id"] for r in records}),
                "splits": {
                    s: sum(r["split"] == s for r in records)
                    for s in ("train", "validation", "test")
                },
            }
        )
    )


if __name__ == "__main__":
    main()
