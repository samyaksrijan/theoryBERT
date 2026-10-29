import itertools
import json
from pathlib import Path

import pytest
import torch

from theorybert.formal.dfa import simulate, equivalent, validate
from theorybert.formal.plan import LanguagePlan as P, compile_plan
from theorybert.models.semantic import targets, decode, VOCAB, MAX_PLAN_LENGTH, pattern_spans


def words(n=6):
    return [''.join(b) for size in range(n+1) for b in itertools.product('01', repeat=size)]


@pytest.mark.parametrize('plan,predicate', [
    (P('AND',(P('STARTS',('01',)),P('ENDS',('10',)))),lambda w:w.startswith('01') and w.endswith('10')),
    (P('OR',(P('EXACT',('001',)),P('COUNT_EQ',('1',2)))),lambda w:w=='001' or w.count('1')==2),
    (P('NOT',(P('CONTAINS',('010',)),)),lambda w:'010' not in w),
    (P('COUNT_LE',('0',2)),lambda w:w.count('0')<=2),
    (P('COUNT_GE',('1',3)),lambda w:w.count('1')>=3),
    (P('COUNT_MOD',('0',3,2)),lambda w:w.count('0')%3==2),
    (P('LENGTH_EQ',(0,)),lambda w:len(w)==0),
    (P('LENGTH_LE',(4,)),lambda w:len(w)<=4),
    (P('LENGTH_GE',(2,)),lambda w:len(w)>=2),
    (P('LENGTH_MOD',(3,1)),lambda w:len(w)%3==1),
])
def test_plan_compiler_matches_independent_predicate(plan,predicate):
    dfa=compile_plan(plan)
    assert not validate(dfa)
    assert all(simulate(dfa,w)==predicate(w) for w in words())


def test_typed_neural_decoder_copies_exact_literal_including_leading_zeros():
    text='Accept inputs containing 00101 and ending with 10.'
    offsets=[(0,0)]+[(i,i+1) for i in range(len(text))]+[(0,0)]
    plan=P('AND',(P('CONTAINS',('00101',)),P('ENDS',('10',))))
    # Test the decoder independently of learned scores: perfect head logits
    # must yield the intended tree, not a shorter or fixed default language.
    tokens,starts,ends=targets(plan,text,offsets)
    out={'tokens':torch.full((1,MAX_PLAN_LENGTH,len(VOCAB)),-30.),'start':torch.full((1,MAX_PLAN_LENGTH,len(offsets)),-30.),'end':torch.full((1,MAX_PLAN_LENGTH,len(offsets)),-30.)}
    for pos,t in enumerate(tokens):
        out['tokens'][0,pos,t]=30
        if starts[pos]>=0:
            out['start'][0,pos,starts[pos]]=30
            out['end'][0,pos,ends[pos]]=30
    predicted=decode(out,text,offsets,1)
    assert predicted[0]['plan']==plan
    assert equivalent(predicted[0]['dfa'],compile_plan(plan))[0]
    assert not any(value=='0010' for _,_,value in pattern_spans(text,offsets))


def test_plan_validation_bounds_modulus_and_state_budget():
    for plan in [P('COUNT_MOD',('1',0,0)),P('LENGTH_MOD',(2,2)),P('STARTS',('abc',)),P('LENGTH_EQ',(True,))]:
        with pytest.raises(ValueError):compile_plan(plan)
    with pytest.raises(ValueError,match='state budget'):
        compile_plan(P('EXACT',('00101',)),max_states=3)


def test_plan_data_language_partitions_and_frozen_comparison_do_not_leak():
    path=Path('data/generated/english-plan-v1.jsonl')
    if not path.exists():pytest.skip('Local generated dataset not distributed')
    rows=[json.loads(l) for l in path.read_text().splitlines()]
    groups={}
    for r in rows:groups.setdefault(r['language_id'],set()).add(r['split'])
    assert all(len(s)==1 for s in groups.values())
    training_languages={r['language_id'] for r in rows if r['split']=='train'}
    fresh=[json.loads(l) for l in Path('data/challenges/plan-comparison-v2.jsonl').read_text().splitlines()]
    assert not training_languages & {r['language_id'] for r in fresh}
