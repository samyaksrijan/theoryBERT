import hashlib
import itertools
import json
from pathlib import Path

from theorybert.data.challenges import product
from theorybert.data.generators import pattern_dfa
from theorybert.formal.dfa import simulate
from theorybert.evaluation.challenge import recognizer, reference_expression


def test_frozen_challenge_bytes_and_language_group_partitions():
    path = Path("data/challenges/toc-compiler-v1.jsonl")
    manifest = json.loads(path.with_suffix(".manifest.json").read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["sha256"]
    rows = list(map(json.loads, path.read_text().splitlines()))
    assert len(rows) == 165 and len({r["case_id"] for r in rows}) == 165
    roles = {}
    for row in rows:
        assert row["language_id"] not in roles or roles[row["language_id"]] == row["partition"]
        roles[row["language_id"]] = row["partition"]
        if row["prior_language_split"] == "test":
            assert row["partition"] == "test"


def test_boolean_gold_is_checked_against_string_operations():
    for operation in ("and", "or"):
        dfa = product(pattern_dfa("01", "starts"), pattern_dfa("10", "ends"), operation)
        for n in range(7):
            for bits in itertools.product("01", repeat=n):
                word = "".join(bits)
                expected = word.startswith("01") and word.endswith("10") if operation == "and" else word.startswith("01") or word.endswith("10")
                assert simulate(dfa, word) == expected


def test_membership_diagnostic_distinguishes_cfg_language_errors():
    balanced = "S -> 'a' S 'b' |"
    nested = "S -> 'a' S 'b' S |"
    assert recognizer(balanced, "aabb") and recognizer(nested, "aabb")
    assert not recognizer(balanced, "abab") and recognizer(nested, "abab")
    assert recognizer(balanced, "")


def test_reference_compiler_checks_grouping_without_executing_code():
    left = reference_expression("a-b-c")
    right = reference_expression("a-(b-c)")
    assert left != right
    # Compilation is symbolic; division by zero is not executed.
    assert reference_expression("1/0")[0] == "/"
