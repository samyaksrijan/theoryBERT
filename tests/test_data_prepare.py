import itertools
import json
import re

import pytest

from theorybert.data.prepare import regex_to_binary, prepare
from theorybert.formal.dfa import simulate, validate


@pytest.mark.parametrize("pattern", ["(0|1)*01", "1(0|1){1,3}", "[01]*0", "[^0]{2,}", "[0-9]{3,}", "(00|11)+", "(01)?1*", "(a|0)*1"])
def test_public_regex_conversion_matches_independent_engine(pattern):
    dfa = regex_to_binary(pattern)
    assert not validate(dfa)
    for size in range(9):
        for bits in itertools.product("01", repeat=size):
            value = "".join(bits)
            assert simulate(dfa, value) == bool(re.fullmatch(pattern, value))


@pytest.mark.parametrize("pattern", ["~(0.*)", "(0.*)&(.*1)", r"\b01\b", "(?=01).*", "[01]{20}"])
def test_unsupported_dialects_are_rejected(pattern):
    with pytest.raises(ValueError):
        regex_to_binary(pattern)


def test_equivalent_targets_never_leak_across_splits(tmp_path):
    path = tmp_path / "data.jsonl"
    prepare(path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    splits = {}
    for row in rows:
        assert row["language_id"] not in splits or splits[row["language_id"]] == row["split"]
        splits[row["language_id"]] = row["split"]
    assert set(splits.values()) == {"train", "validation", "test"}
