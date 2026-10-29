"""Run frozen validation, select, then unseal the v2 test exactly once."""
import hashlib
import json
from pathlib import Path
import statistics
import time

import torch
from theorybert.contracts import DFA
from theorybert.formal.dfa import equivalent,validate
from theorybert.models.predictor import load_predictor
from theorybert.training.resources import ResourceGuard

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/plan-comparison'


def score(predictor,records):
    rows=[]
    for r in records:
        text=r['description']
        gold=DFA.from_dict(r.get('gold_dfa',r.get('ground_truth_dfa')))
        started=time.perf_counter()
        try:
            candidates=list(predictor.predict(text,5))
            error=None
        except ValueError as exc:
            candidates=[];error=str(exc)
        seconds=time.perf_counter()-started
        correctness=[equivalent(c,gold)[0] for c in candidates]
        rows.append({'id':r.get('case_id',r.get('example_id')),'description':text,'language_id':r['language_id'],'op':r.get('op',r.get('family')),'gold_states':len(gold.states),'matched_scope':len(gold.states)<=8 and len(predictor.tokenizer.encode(text))<=64,'first_correct':bool(correctness and correctness[0]),'within_five':any(correctness),'valid':bool(candidates and not validate(candidates[0])),'seconds':seconds,'error':error})
    return rows


def aggregate(rows):
    if not rows:return {'examples':0}
    return {'examples':len(rows),'correct':sum(r['first_correct'] for r in rows),'first_equivalence':statistics.mean(r['first_correct'] for r in rows),'within_five':statistics.mean(r['within_five'] for r in rows),'structural_validity':statistics.mean(r['valid'] for r in rows),'mean_prediction_seconds':statistics.mean(r['seconds'] for r in rows),'median_prediction_seconds':statistics.median(r['seconds'] for r in rows),'p95_prediction_seconds':sorted(r['seconds'] for r in rows)[min(len(rows)-1,int(.95*len(rows)))]}


def main():
    import gc
    from check_bert_presets import check
    torch.set_num_threads(2)
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'selection.json').exists():
        raise RuntimeError('Selection exists. Do not overwrite or tune against the frozen test.')
    protocol=json.loads((ROOT/'artifacts/plan-promotion-protocol.json').read_text())
    guard=ResourceGuard(OUT,max_swap_growth_gb=.75)
    comparison=ROOT/protocol['comparison']
    assert hashlib.sha256(comparison.read_bytes()).hexdigest()==protocol['comparison_sha256']
    cases=[json.loads(l) for l in comparison.read_text().splitlines()]
    old=[json.loads(l) for l in (ROOT/'data/generated/english-dfa-v3.jsonl').read_text().splitlines()]
    validation={}
    for name in ('baseline','candidate'):
        p=load_predictor(protocol[name])
        rows=score(p,[r for r in cases if r['partition']=='validation'])
        original=score(p,[r for r in old if r['split']=='validation'])
        detail={'fresh':rows,'original':original}
        (OUT/f'{name}-validation.json').write_text(json.dumps(detail,indent=2))
        validation[name]={'fresh':aggregate(rows),'matched':aggregate([r for r in rows if r['matched_scope']]),'original':aggregate(original)}
        del p;gc.collect();guard.check(name+'_validation')
    presets=check(protocol['candidate'])
    (OUT/'candidate-presets.json').write_text(json.dumps(presets,indent=2))
    gain=validation['candidate']['matched']['first_equivalence']-validation['baseline']['matched']['first_equivalence']
    promote=gain>=protocol['minimum_matched_fresh_first_equivalence_gain'] and validation['candidate']['original']['first_equivalence']>=protocol['minimum_original_validation_first_equivalence'] and presets['passed']
    selection={'candidate_promoted':promote,'matched_validation_gain':gain,'validation':validation,'presets_passed':presets['passed'],'selection_used_test':False,'protocol':protocol,'selected':protocol['candidate'] if promote else protocol['baseline']}
    # Commit selection before evaluating any test predictions.
    (OUT/'selection.json').write_text(json.dumps(selection,indent=2))
    print(json.dumps(selection,indent=2),flush=True)
    tests={}
    for name in ('baseline','candidate'):
        p=load_predictor(protocol[name])
        rows=score(p,[r for r in cases if r['partition']=='test'])
        original=score(p,[r for r in old if r['split']=='test'])
        (OUT/f'{name}-test.json').write_text(json.dumps({'fresh':rows,'original':original},indent=2))
        tests[name]={'fresh':aggregate(rows),'matched':aggregate([r for r in rows if r['matched_scope']]),'original':aggregate(original),'extra_capacity':aggregate([r for r in rows if not r['matched_scope']])}
        del p;gc.collect();guard.check(name+'_test')
    summary={'selection':selection,'test':tests,'test_used_for_selection':False,'comparison_sha256':protocol['comparison_sha256'],'resources':guard.check('complete'),'limitations':'Single seed; synthetic wording and finite typed DSL. No inference-speed or broad natural-language claim follows from fewer trainable parameters.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
    if promote:
        pointer=ROOT/'artifacts/active-model.json'
        previous=json.loads(pointer.read_text())
        pointer.write_text(json.dumps({'checkpoint':protocol['candidate'],'kind':'semantic_plan','training_summary':protocol['candidate']+'/summary.json','evaluation':'artifacts/plan-comparison','pretrained_source':'google-bert/bert-base-uncased','previous_checkpoint':previous['checkpoint'],'selection_used_test':False},indent=2))
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
