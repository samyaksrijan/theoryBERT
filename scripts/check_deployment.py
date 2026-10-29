"""Black-box proof that a deployed build uses BERT and preserves formal checks."""
import argparse,json,ssl,time
from pathlib import Path
from urllib.error import URLError,HTTPError
from urllib.request import Request,urlopen


def check(base,expected_commit=None,timeout=600):
    context=ssl.create_default_context()
    try:
        import certifi
        context=ssl.create_default_context(cafile=certifi.where())
    except ImportError:pass
    def request(path,payload=None):
        body=None if payload is None else json.dumps(payload).encode()
        req=Request(base.rstrip('/')+path,data=body,headers={'Content-Type':'application/json'})
        with urlopen(req,context=context,timeout=30) as response:return json.load(response)
    started=time.monotonic();health=None
    while time.monotonic()-started<timeout:
        try:
            health=request('/api/health')
            if health.get('model_ready'):break
        except (URLError,TimeoutError,OSError,ValueError):pass
        time.sleep(3)
    assert health and health['status']=='ready' and health['model_ready'],health
    assert health['runtime']=='bert' and health['active_model']['kind']=='semantic_plan',health
    assert health['active_grammar'],health
    if expected_commit:assert health['commit']==expected_commit,health
    checks=[]
    def task(payload,error=False):
        job=request('/api/jobs',payload)['job_id'];deadline=time.monotonic()+240
        while time.monotonic()<deadline:
            status=request('/api/jobs/'+job)
            if status['status']!='running':
                assert status['status']==('error' if error else 'complete'),status
                return status if error else status['result']
            time.sleep(.5)
        raise AssertionError('Deployed task exceeded its verification budget.')
    # Independent DFA reference built here from suffix matching, not BERT output.
    pattern='0101';states=['q'+str(i) for i in range(len(pattern)+1)]
    transitions={}
    for i,state in enumerate(states):
        transitions[state]={}
        for symbol in '01':
            value=pattern[:i]+symbol
            matched=max(k for k in range(len(pattern)+1) if value.endswith(pattern[:k]))
            transitions[state][symbol]=states[matched]
    reference={'states':states,'alphabet':['0','1'],'transitions':transitions,'start_state':'q0','accept_states':[states[-1]]}
    fixture={'kind':'dfa','source':'learned','description':'Binary strings that end with 0101','input':'110101','reference_json':json.dumps(reference)}
    dfa=task(fixture)
    assert dfa['verified'] and dfa['prediction_source']=='learned',dfa
    assert dfa['language_plan']=={'op':'ENDS','args':['0101']},dfa
    assert len(dfa['dfa']['states'])==5 and dfa['trace']['accepted'] and dfa['graph'],dfa
    checks.append({'case':'BERT suffix with five states','passed':True,'seconds':dfa['elapsed_seconds']})
    rejected=task({**fixture,'input':'1100'})
    assert rejected['verified'] and not rejected['trace']['accepted'],rejected
    checks.append({'case':'DFA rejection follows changed input','passed':True})
    preview=task({**fixture,'reference_json':''})
    assert not preview['verified'] and preview['status']=='REFERENCE_UNAVAILABLE' and preview['graph'],preview
    checks.append({'case':'Unreferenced English never claims equivalence','passed':True})
    cfg=task({'kind':'cfg','grammar_source':'learned','description':'Build a context-free grammar for strings of the form a^n b^n for n >= 0.','input':'aabb','limit':2})
    assert cfg['verified'] and cfg['grammar_source']=='learned' and cfg['layouts'],cfg
    checks.append({'case':'BERT grammar and checked derivation','passed':True,'seconds':cfg['elapsed_seconds']})
    compiler_fixture={'kind':'cfg','grammar_source':'learned','description':'Arithmetic expressions with identifiers and numbers, plus, minus, multiplication, division, parentheses, and unary signs; use standard precedence and left associativity.','tokenization':'expression','input':'(total + 3) * scale - 4 / 2','limit':2}
    compiler=task(compiler_fixture)
    assert compiler['verified'] and compiler['compiler']['layout'],compiler
    checks.append({'case':'BERT compiler grammar and checked AST','passed':True,'seconds':compiler['elapsed_seconds']})
    invalid=task({**compiler_fixture,'input':'a+*b'},error=True)
    assert invalid['candidate_grammar'] and 'No derivation' in invalid['error'],invalid
    checks.append({'case':'Invalid compiler expression rejected','passed':True})
    rendered=task({'kind':'render','result_id':dfa['id'],'quality':'preview'})
    req=Request(base.rstrip('/')+rendered['url'])
    with urlopen(req,context=context,timeout=30) as response:
        content=response.read(64)
        assert response.headers['Content-Type'].startswith('video/mp4') and b'ftyp' in content,content
    checks.append({'case':'Verified animation exports as real MP4','passed':True,'seconds':rendered['seconds']})
    assert request('/api/health')['model_ready']
    return {'passed':True,'health':health,'checks':checks,'seconds':time.monotonic()-started}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True);parser.add_argument('--expect-commit');parser.add_argument('--output',required=True);args=parser.parse_args()
    result=check(args.base_url,args.expect_commit)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
