import copy
import pytest
from theorybert.contracts import Status
from theorybert.data.generators import pattern_dfa
from theorybert.pipeline import verify, run_candidates, VerifiedDFA
from theorybert.rendering.renderer import payload_for, render_key, seal_tree
from theorybert.formal.cfg import parse


def test_strict_gate_and_rejected_execution():
    d = pattern_dfa("01")
    report = verify(d)
    assert report.status == Status.REFERENCE_UNAVAILABLE and report.equivalent is None
    result = run_candidates([d], d, "independent fixture")
    assert result.verified
    payload = payload_for(result.verified, list("00"))
    assert not payload["trace"]["accepted"]
    with pytest.raises(TypeError):
        payload_for(d)
    assert render_key(payload) != render_key(payload_for(result.verified, list("01")))
    assert render_key(payload, "preview") != render_key(payload, "high")
    wrong = pattern_dfa("01", "contains")
    failed = run_candidates([wrong], d)
    assert (
        failed.verified is None
        and failed.reports[0].status == Status.EQUIVALENCE_FAILED
    )
    with pytest.raises(ValueError):
        VerifiedDFA(
            __import__("json").dumps(wrong.to_dict()),
            __import__("json").dumps(d.to_dict()),
            "forged",
        ).checked()


def test_retry_dedup_budget_and_invalid():
    d = pattern_dfa("01")
    wrong = pattern_dfa("01", "contains")
    result = run_candidates([wrong, wrong, d], d, budget=2)
    assert result.verified and len(result.reports) == 2
    assert run_candidates([wrong, d], d, budget=1).verified is None
    assert len(run_candidates((wrong for _ in range(100)), d, budget=2).reports) == 1
    invalid = copy.deepcopy(d)
    invalid.transitions["q0"]["0"] = "ghost"
    assert verify(invalid, d).status == Status.STRUCTURE_INVALID
    epsilon = copy.deepcopy(d)
    epsilon.accept_states = [s for s in d.states if s not in d.accept_states]
    assert verify(epsilon, d).counterexample == []


def test_verified_tree_render_contract():
    spec, trees, _ = parse("S -> 'a' S 'b' |", ["a", "b"])
    seal = seal_tree(spec, trees[0])
    assert payload_for(seal)["mode"] == "cfg"
    trees[0].symbol = "ghost"
    with pytest.raises(ValueError):
        seal_tree(spec, trees[0])


def test_resource_report_and_shortest_negative():
    from theorybert.formal.dfa import equivalent

    a = pattern_dfa("01")
    b = pattern_dfa("10")
    with pytest.raises(TimeoutError):
        equivalent(a, b, max_pairs=1)
    result = run_candidates([a], a, timeout=-1)
    assert result.verified is None and result.reports[0].status == Status.RESOURCE_LIMIT


def test_candidate_matches_its_report_when_budget_expires():
    reference = pattern_dfa("01")
    wrong = pattern_dfa("01", "contains")
    consumed = []

    def candidates():
        consumed.append("wrong")
        yield wrong
        consumed.append("reference")
        yield reference

    result = run_candidates(candidates(), reference, budget=1)
    assert consumed == ["wrong"]
    assert result.candidate.to_dict() == wrong.to_dict()
    assert [d.to_dict() for d in result.attempted_candidates] == [wrong.to_dict()]
    assert result.reports[0].status == Status.EQUIVALENCE_FAILED
    assert result.verified is None


def test_candidate_history_snapshots_reused_objects():
    reference = pattern_dfa("01")
    candidate = copy.deepcopy(reference)
    candidate.accept_states = []

    def candidates():
        yield candidate
        candidate.accept_states = list(reference.accept_states)
        yield candidate

    result = run_candidates(candidates(), reference, budget=2)
    assert result.verified
    assert result.attempted_candidates[0].accept_states == []
    assert result.attempted_candidates[1].accept_states == reference.accept_states


def test_empty_candidate_stream_is_an_explicit_failure():
    result = run_candidates([], pattern_dfa("01"))
    assert result.candidate is None and result.verified is None
    assert result.reports[0].status == Status.RESOURCE_LIMIT
    assert result.reports[0].message


def test_unverified_preview_keeps_first_ranked_valid_prediction():
    first, alternative = pattern_dfa("01"), pattern_dfa("10")
    consumed = []
    def predictions():
        consumed.append("first")
        yield first
        consumed.append("alternative")
        yield alternative
    result = run_candidates(predictions(), reference=None, budget=5)
    assert result.candidate.to_dict() == first.to_dict()
    assert consumed == ["first"]
    assert result.verified is None
    assert len(result.reports) == 1
