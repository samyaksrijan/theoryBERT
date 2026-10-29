import pytest

from theorybert.formal.compiler import ARITHMETIC_GRAMMAR
from theorybert.formal.cfg import ParseError
from theorybert.web import solve_cfg


def compile_source(source):
    return solve_cfg({"grammar": ARITHMETIC_GRAMMAR, "input": source, "tokenization": "expression"}, lambda _: None)[0]


@pytest.mark.parametrize("source,operators", [
    ("a+3*b", ["*", "+"]),
    ("(a+3)*b", ["+", "*"]),
    ("a-b-c", ["-", "-"]),
    ("a/(b/c)", ["/", "/"]),
    ("-(a+3)*b", ["+", "unary -", "*"]),
    (".5 + 2.0", ["+"]),
    ("one_input", []),
])
def test_compiler_obeys_precedence_and_keeps_exact_source_values(source, operators):
    result = compile_source(source)
    compiled = result["compiler"]
    assert result["verified"] and compiled["ir_checked"]
    assert [row["operator"] for row in compiled["instructions"]] == operators
    for row in result["lexemes"]:
        assert source[row["start"]:row["end"]] == row["lexeme"]
    if source == "a-b-c":
        assert compiled["instructions"][1]["arguments"][0] == {"kind": "temporary", "value": "t0"}
    if source == "a/(b/c)":
        assert compiled["instructions"][1]["arguments"][1] == {"kind": "temporary", "value": "t0"}


@pytest.mark.parametrize("source", ["a+*b", "(a+b", "a b", ""])
def test_invalid_program_does_not_have_a_syntax_tree(source):
    with pytest.raises(ParseError):
        compile_source(source)


def test_compiler_never_executes_source():
    with pytest.raises(ParseError, match="Unexpected source character"):
        compile_source("__import__('os').system('anything')")
