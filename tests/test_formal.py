import copy
import itertools
import pytest
from theorybert.contracts import DFA, strict_json
from theorybert.formal.dfa import *
from theorybert.data.generators import (
    pattern_dfa,
    generate,
)
from theorybert.formal.cfg import parse, check_tree, EXAMPLES, ParseError


def strings(n=5):
    return ["".join(x) for k in range(n + 1) for x in itertools.product("01", repeat=k)]


@pytest.mark.parametrize("kind", ["starts", "ends", "contains"])
def test_pattern_semantics(kind):
    for pattern in ("0", "01", "101", "00"):
        d = pattern_dfa(pattern, kind)
        for s in strings():
            expected = (
                s.startswith(pattern)
                if kind == "starts"
                else s.endswith(pattern)
                if kind == "ends"
                else pattern in s
            )
            assert simulate(d, s) == expected


def test_equivalence_and_shortest_witness():
    a = pattern_dfa("01", "ends")
    b = pattern_dfa("01", "contains")
    eq, witness = equivalent(a, b)
    assert not eq and not simulate(a, witness) == simulate(b, witness)
    assert all(simulate(a, s) == simulate(b, s) for s in strings(len(witness) - 1))
    c = copy.deepcopy(a)
    c.accept_states = [s for s in c.states if s not in c.accept_states]
    assert equivalent(a, c) == (False, [])


def test_minimal_canonical_reachable_renamed():
    d = pattern_dfa("01")
    other = copy.deepcopy(d)
    names = {s: "name" + s for s in d.states}
    other = DFA(
        list(names.values()) + ["unreachable"],
        d.alphabet,
        {
            **{
                names[s]: {a: names[t] for a, t in row.items()}
                for s, row in d.transitions.items()
            },
            "unreachable": {"0": "unreachable", "1": "unreachable"},
        },
        names[d.start_state],
        [names[s] for s in d.accept_states] + ["unreachable"],
    )
    assert equivalent(d, other) == (True, None)
    assert canonicalise(d) == canonicalise(other)
    assert canonicalise(canonicalise(other)) == canonicalise(other)
    assert equivalent(other, minimise(other))[0]
    for accepting in ([], list(d.states)):
        x = copy.deepcopy(d)
        x.accept_states = accepting
        assert len(minimise(x).states) == 1


def test_structure_and_alphabet():
    d = pattern_dfa("01")
    del d.transitions["q0"]["0"]
    assert validate(d)
    d = pattern_dfa("01")
    d.transitions["q0"]["0"] = "ghost"
    assert validate(d)
    d = pattern_dfa("01")
    d.states.append("q0")
    assert validate(d)
    with pytest.raises(ValueError):
        simulate(pattern_dfa("01"), "2")
    multi = DFA(["a"], ["token"], {"a": {"token": "a"}}, "a", ["a"])
    assert simulate(multi, ["token"])
    with pytest.raises(ValueError):
        equivalent(multi, pattern_dfa("01"))
    with pytest.raises(ValueError, match="Duplicate"):
        strict_json('{"x":1,"x":2}')


def test_grouped_dataset():
    rows = generate(42, 8)
    seen = {}
    for r in rows:
        lid = r["language_id"]
        assert seen.setdefault(lid, r["split"]) == r["split"]
        d = DFA.from_dict(r["ground_truth_dfa"])
        assert not validate(d)
        for example in r["test_strings"]:
            assert simulate(d, example["string"]) == example["accepted"]
    assert rows == generate(42, 8)


@pytest.mark.parametrize("name", list(EXAMPLES))
def test_cfg_examples(name):
    grammar, text = EXAMPLES[name]
    spec, trees, truncated = parse(grammar, text.split())
    assert trees and all(not check_tree(spec, t)[0] for t in trees)
    if name == "Ambiguous expression":
        assert len(trees) == 2


def test_tree_independent_mutations():
    grammar, text = EXAMPLES["Balanced a / b"]
    spec, trees, _ = parse(grammar, text.split())
    root = trees[0]
    wrong = copy.deepcopy(root)
    wrong.symbol = "X"
    assert check_tree(spec, wrong)[0]
    wrong = copy.deepcopy(root)
    wrong.children[0].symbol = "b"
    assert check_tree(spec, wrong)[0]
    wrong = copy.deepcopy(root)
    wrong.children.pop()
    assert check_tree(spec, wrong)[0]
    spec.input_tokens = ["b"]
    assert "Terminal yield differs" in " ".join(check_tree(spec, root)[0])


def test_cfg_epsilon_and_limits():
    spec, trees, _ = parse("S -> 'a' S 'b' |", [])
    assert not check_tree(spec, trees[0])[0]
    for grammar, tokens, kind in [
        ("S -> 'a'", ["b"], "TOKENISATION_FAILURE"),
        ("S -> 'a'", [], "NO_DERIVATION"),
        ("bad grammar", [], "MALFORMED_GRAMMAR"),
    ]:
        with pytest.raises(ParseError) as err:
            parse(grammar, tokens)
        assert err.value.kind == kind
    with pytest.raises(ParseError):
        parse("S -> 'a'", ["a"] * 65)
    with pytest.raises(ParseError):
        parse(EXAMPLES["Arithmetic"][0], ["id"], timeout=0.001)
    spec, trees, truncated = parse(
        EXAMPLES["Ambiguous expression"][0],
        EXAMPLES["Ambiguous expression"][1].split(),
        limit=1,
    )
    assert truncated and len(trees) == 1
