import json

import pytest

from theorybert.data.generators import pattern_dfa
from theorybert.web import solve_dfa


def test_supplied_dfa_can_be_inspected_without_false_equivalence_claim():
    result, private = solve_dfa({"source": "manual", "candidate_json": json.dumps(pattern_dfa("10").to_dict()), "input": "110", "description": "Binary strings that end in 01.", "example_id": "manual-suffix-01"}, lambda _: None)
    assert result["status"] == "REFERENCE_UNAVAILABLE"
    assert result["graph"] and result["trace"]["accepted"]
    assert not result["verified"] and not result["renderable"]
    assert private["evidence"] is None


def test_learned_mode_never_falls_back_to_rules():
    with pytest.raises(ValueError, match="No checkpoint"):
        solve_dfa({"source": "learned", "checkpoint": "artifacts/nonexistent", "description": "Binary strings that end in 01.", "input": "01"}, lambda _: None)


def test_invalid_manual_structure_does_not_produce_a_preview():
    bad = pattern_dfa("10").to_dict()
    bad["transitions"]["q0"]["0"] = "unknown"
    with pytest.raises(ValueError, match="undeclared"):
        solve_dfa({"source": "manual", "candidate_json": json.dumps(bad), "input": ""}, lambda _: None)


def test_app_refuses_random_backbone_smoke_checkpoint(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"training_status": "smoke-trained", "backbone": "tiny-random-bert"}))
    (tmp_path / "weights.pt").write_bytes(b"Not loaded")
    with pytest.raises(ValueError, match="smoke checkpoint"):
        solve_dfa({"source": "learned", "checkpoint": str(tmp_path), "description": "Binary strings that end in 01.", "input": "01"}, lambda _: None)


def test_manual_preview_preserves_user_state_names_and_unreachable_states():
    data = {"states": ["start", "accept", "unreachable"], "alphabet": ["1", "0"], "transitions": {"start": {"0": "start", "1": "accept"}, "accept": {"0": "start", "1": "accept"}, "unreachable": {"0": "unreachable", "1": "unreachable"}}, "start_state": "start", "accept_states": ["accept"]}
    result, _ = solve_dfa({"source": "manual", "candidate_json": json.dumps(data), "input": "01"}, lambda _: None)
    assert result["dfa"]["states"] == data["states"]
    assert set(result["graph"]["nodes"]) == set(data["states"])
    assert result["trace"]["accepted"]


def test_wrong_bert_candidate_is_never_replaced_with_a_constructed_solution(tmp_path, monkeypatch):
    from theorybert import web
    (tmp_path / "config.json").write_text(json.dumps({"training_status": "pretrained fine-tuned", "backbone": "bert"}))
    (tmp_path / "weights.pt").write_bytes(b"mock checkpoint, loader patched")
    wrong = pattern_dfa("11")
    class WrongBert:
        source = "Test BERT predictor"
        def predict(self, description, budget):
            assert description == "Binary strings that end in 01."
            return iter([wrong])
    monkeypatch.setattr(web, "learned_checkpoint", lambda *args: WrongBert())
    public, private = solve_dfa({"source": "learned", "description": "Binary strings that end in 01.", "input": "1101", "checkpoint": str(tmp_path), "example_id": "manual-suffix-01"}, lambda _: None)
    assert public["status"] == "EQUIVALENCE_FAILED"
    assert public["candidate"] == wrong.to_dict()
    assert private["evidence"] is None and not public["verified"]


def test_removed_english_compiler_sources_cannot_bypass_bert():
    for source in ("assisted", "compiled", "rule"):
        with pytest.raises(ValueError, match="supported prediction source"):
            solve_dfa({"source": source, "description": "Binary strings that end in 01", "input": "01"}, lambda _: None)


def mock_grammar_encoder(tmp_path, monkeypatch, grammar):
    from theorybert import web
    base = tmp_path / "encoder"
    base.mkdir()
    (base / "weights.pt").write_bytes(b"fixture")
    (tmp_path / "head.pt").write_bytes(b"fixture")
    (tmp_path / "config.json").write_text(json.dumps({"encoder_checkpoint": str(base)}))
    calls = []
    class Predictor:
        source = "BERT test fixture"
        def predict(self, description):
            calls.append(description)
            return grammar
    monkeypatch.setattr(web, "active_grammar", lambda: {"checkpoint": str(tmp_path)})
    monkeypatch.setattr(web, "learned_grammar", lambda *args: Predictor())
    return calls


def test_failed_compiler_request_retains_actual_bert_productions(tmp_path, monkeypatch):
    from theorybert import web
    from theorybert.formal.compiler import ARITHMETIC_GRAMMAR
    mock_grammar_encoder(tmp_path, monkeypatch, ARITHMETIC_GRAMMAR)
    with pytest.raises(ValueError, match="No derivation") as rejected:
        web.solve_cfg({"grammar_source": "learned", "description": "Arithmetic language", "tokenization": "expression", "input": "a+*b"}, lambda _: None)
    assert rejected.value.candidate_grammar == ARITHMETIC_GRAMMAR


def test_input_only_reparse_reuses_bert_but_new_head_revision_invalidates_it(tmp_path, monkeypatch):
    import os
    from collections import OrderedDict
    from theorybert import web
    calls = mock_grammar_encoder(tmp_path, monkeypatch, "S -> 'a' S 'b' |")
    monkeypatch.setattr(web, "results", OrderedDict())
    data = {"grammar_source": "learned", "description": "Matching blocks", "input": "ab"}
    public, private = web.solve_cfg(data, lambda _: None)
    web.results["prior"] = {"public": public, "private": private}
    second, _ = web.solve_cfg({**data, "input": "aabb", "grammar_result_id": "prior"}, lambda _: None)
    assert len(calls) == 1 and len(second["layouts"][0]["nodes"]) > len(public["layouts"][0]["nodes"])
    head = tmp_path / "head.pt"
    changed = head.stat().st_mtime_ns + 1000000
    os.utime(head, ns=(changed, changed))
    web.solve_cfg({**data, "grammar_result_id": "prior"}, lambda _: None)
    assert len(calls) == 2



def test_semantic_head_checkpoint_uses_learned_plans_and_selected_metadata(tmp_path, monkeypatch):
    from theorybert import web
    from theorybert.formal.plan import LanguagePlan as P, compile_plan
    (tmp_path / 'config.json').write_text(json.dumps({'kind':'semantic_plan','training_status':'trained frozen BERT semantic decoder','backbone':'bert'}))
    (tmp_path / 'head.pt').write_bytes(b'head fixture; loader patched')
    wrong=P('ENDS',('11',));correct=P('ENDS',('01',))
    class Predictor:
        source='BERT semantic plan fixture'
        def predict_with_plans(self,description,budget):
            return [{'plan':p,'dfa':compile_plan(p)} for p in (wrong,correct)]
    monkeypatch.setattr(web,'learned_checkpoint',lambda *args:Predictor())
    result,_=web.solve_dfa({'source':'learned','checkpoint':str(tmp_path),'description':'Binary strings that end in 01.','example_id':'manual-suffix-01','input':'1101'},lambda _:None)
    assert result['verified']
    assert result['language_plan']==correct.to_dict()
    assert result['trace']['accepted']
