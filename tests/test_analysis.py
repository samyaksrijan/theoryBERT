import pytest

from theorybert.formal.analysis import grammar_analysis, tokenize_input
from theorybert.formal.cfg import grammar_spec, ParseError
from theorybert.web import solve_cfg


def test_nullable_first_follow_and_predictive_table():
    _, spec = grammar_spec("S -> A B\nA -> 'a' A |\nB -> 'b' B |", [])
    analysis = grammar_analysis(spec)
    assert analysis["nullable"] == ["A", "B", "S"]
    assert analysis["first"]["S"] == ["a", "b"]
    assert analysis["follow"]["A"] == ["b", "⟨EOF⟩"]
    assert analysis["follow"]["B"] == ["⟨EOF⟩"]
    assert analysis["ll1"]


def test_conflicts_are_not_claimed_to_be_an_ambiguity_proof():
    _, spec = grammar_spec("E -> E '+' E | 'id'", [])
    analysis = grammar_analysis(spec)
    assert not analysis["ll1"]
    assert analysis["conflicts"][0]["lookahead"] == "id"
    assert len(analysis["conflicts"][0]["productions"]) == 2


def test_lexer_longest_match_and_source_spans():
    rows = tokenize_input("S -> 'id' '+' 'id'", "id+id")
    assert [r["token"] for r in rows] == ["id", "+", "id"]
    assert [(r["start"], r["end"]) for r in rows] == [(0, 2), (2, 3), (3, 5)]
    assert [r["token"] for r in tokenize_input("S -> 'aa' | 'a' 'a'", "aa")] == ["aa"]
    assert [r["token"] for r in tokenize_input("S -> 'aa' | 'a' 'a'", "a a", "whitespace")] == ["a", "a"]


def test_lexer_unknown_symbol_is_actionable():
    with pytest.raises(ParseError, match="character 3"):
        tokenize_input("S -> 'a' 'b'", "abx")


def test_tree_changes_with_actual_string_and_epsilon_yield():
    def solve(value):
        return solve_cfg({"grammar": "S -> 'a' S 'b' |", "input": value}, lambda _: None)[0]
    short, long, empty = solve("ab"), solve("aabb"), solve("")
    assert short["verified"] and long["verified"]
    assert len(short["layouts"][0]["nodes"]) < len(long["layouts"][0]["nodes"])
    assert long["steps"][0][-1]["sentential_form"] == "a a b b"
    assert empty["spec"]["input_tokens"] == []
    assert empty["steps"][0][-1]["sentential_form"] == "ε"
