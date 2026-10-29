"""Sequential, resource-monitored evaluation and grammar training for this stage."""
import csv
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from theorybert.training.resources import snapshot


def run(wait_pid=None):
    os.nice(8)
    while wait_pid is not None:
        try:
            os.kill(wait_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(5)
    summary_path = Path('artifacts/bert-v3/summary.json')
    if not summary_path.exists():
        raise RuntimeError('DFA training did not finish successfully; no promotion or follow-up training performed.')
    cleanup = []
    for name in ('lower-bert-cache.pt', 'lower-bert-cache.json'):
        path = Path('artifacts/bert-v3') / name
        if path.exists():
            cleanup.append({'path':str(path), 'bytes':path.stat().st_size, 'reason':'Regenerable frozen-activation cache created in this task; training finished'})
            path.unlink()
    Path('artifacts/v3-cache-cleanup.json').write_text(json.dumps(cleanup, indent=2))
    def stage(name, args):
        print(json.dumps({'phase':name, 'resources':snapshot()}), flush=True)
        with Path('artifacts/'+name+'.log').open('w') as log:
            subprocess.run([sys.executable, *args], check=True, stdout=log, stderr=subprocess.STDOUT)
    common = ['-m','theorybert.evaluation.evaluate','--dataset','data/generated/english-dfa-v3.jsonl']
    stage('v3-old-evaluation',common+['--checkpoint','artifacts/bert-engine/best','--output','artifacts/bert-v3-baseline'])
    stage('v3-new-evaluation',common+['--checkpoint','artifacts/bert-v3/best','--output','artifacts/bert-v3-evaluation'])
    original_ids = {r['example_id'] for r in map(json.loads,Path('data/generated/english-dfa-expanded.jsonl').read_text().splitlines()) if r['split']=='test'}
    comparisons = {}
    for label, folder in [('before','bert-v3-baseline'),('after','bert-v3-evaluation')]:
        with Path('artifacts',folder,'results.csv').open() as handle:
            rows=list(csv.DictReader(handle))
        def metrics(items):
            return {'examples':len(items),'first_candidate_equivalence':sum(int(r['raw_equivalence']) for r in items)/len(items),'success_within_five':sum(int(r['released']) for r in items)/len(items)}
        comparisons[label]={'expanded_test':metrics(rows),'original_test':metrics([r for r in rows if r['example_id'] in original_ids])}
    promote = comparisons['after']['expanded_test']['first_candidate_equivalence'] > comparisons['before']['expanded_test']['first_candidate_equivalence'] and comparisons['after']['original_test']['first_candidate_equivalence'] >= comparisons['before']['original_test']['first_candidate_equivalence']
    comparisons['promoted'] = promote
    Path('artifacts/v3-comparison.json').write_text(json.dumps(comparisons, indent=2))
    if promote:
        stage('v3-activation',['scripts/activate_model.py','--checkpoint','artifacts/bert-v3/best','--evaluation','artifacts/bert-v3-evaluation'])
    stage('v3-grammar-training',['-m','theorybert.models.grammar','--encoder','artifacts/bert-v3/best','--output','artifacts/bert-grammar'])
    print(json.dumps({'phase':'complete','comparison':comparisons,'resources':snapshot()}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait-pid', type=int, help='Wait for this training process before evaluating; omit after training completes')
    run(parser.parse_args().wait_pid)
