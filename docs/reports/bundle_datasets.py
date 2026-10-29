"""Package local supervised datasets and provenance, without model weights."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/pdf/TheoryBERT_Datasets_and_Provenance.zip'
files=set(ROOT.glob('data/**/*.jsonl')) | set(ROOT.glob('data/**/*.manifest.json'))
files |= set(ROOT.glob('data/generated/external/*'))
files |= {ROOT/p for p in ['artifacts/bert-grammar-pilot/dataset.jsonl','artifacts/bert-grammar/dataset.jsonl','artifacts/grammar-robust/dataset.jsonl','artifacts/pretrained/bert-base-uncased/source.json','artifacts/report-data-inventory.json','artifacts/report-tech-versions.json','artifacts/plan-promotion-protocol.json','artifacts/plan-comparison/summary.json','artifacts/plan-comparison/selection.json','artifacts/bert-plan/best/config.json','artifacts/bert-plan/best/summary.json']}
files |= set(ROOT.glob('src/theorybert/data/*.py')) | set(ROOT.glob('configs/*.json'))
files |= {ROOT/'src/theorybert/models/grammar.py',ROOT/'src/theorybert/formal/plan.py',ROOT/'docs/SEMANTIC-PLAN.md'}
files |= set(ROOT.glob('src/theorybert/**/*.py'))
files |= set(ROOT.glob('docs/reports/*.py')) | set(ROOT.glob('docs/reports/*.json'))
files |= set(ROOT.glob('artifacts/plan-comparison/*.json'))
files |= {ROOT/p for p in ['scripts/compare_plan_model.py','scripts/check_bert_presets.py','scripts/download_training_assets.py','artifacts/plan-verification.json','artifacts/report-qa.json']}
files={p for p in files if p.is_file()}
registry=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
 for p in sorted(files):archive.write(p,str(p.relative_to(ROOT)))
 archive.writestr('CONTENTS_AND_SHA256.json',json.dumps(registry,indent=2))
 archive.writestr('README.txt','''TheoryBERT local datasets and provenance snapshot, 29 October 2026.

This archive includes overlapping generated corpus versions, the frozen challenge
sets, actual grammar training files, pinned public KB13 source bytes and their
MIT license, local generators/configurations and measured experiment provenance.
Versions overlap: do not sum their rows as independent data. The tiny original
challenge file and reference fixtures are not training benchmarks.

No BERT model weights are included. Pretrained artifact lineage is recorded in
artifacts/pretrained/bert-base-uncased/source.json. Raw BookCorpus and Wikipedia
were not downloaded or used for local training. The project requires the exact
local evaluated V3 encoder to reproduce the plan head. Generated files may not
be available on the public project repository. Paths here preserve project
relative locations. See CONTENTS_AND_SHA256.json for every packaged file.

External KB13 mirror:
https://github.com/nicholaslocascio/deep-regex/tree/096490db7f4b0394fbb46b914cb35a0aa1cba29c/datasets/KB13
License: data/generated/external/LICENSE.md (MIT, 2016 Nick Locascio).
Do not remove source notices when redistributing these external files.

Frozen v2 and retired v1 tests are already exposed. A later experiment needs a
new independent test version. This archive is reproducibility data, not evidence
that model interpretation is universally correct.
''')
print(OUT,OUT.stat().st_size,len(files))
