# Prompt audit · 23 October 2026

**Product update · 24 October 2026:** the follow-up request for a multipage React product is implemented in `frontend/` and `src/theorybert/web.py`. React is now the main interface, with a reference-inspired public landing, DFA Studio, Grammar Lab, Example Library and Research page, a shared white/black/pink identity, motion, canvas playback and real API-backed verification/export. The original canvas layout and controls are preserved; diagrams, tables and video exports share the updated state palette. The original Streamlit app remains available as a legacy interface. See `UI-DESIGN.md` for the current product architecture and validation commands.

The local prototype is implemented. Genuine pretrained training and research comparisons remain unexecuted; the original prompt explicitly makes those experiments opt-in. No pretrained research accuracy is claimed.

## Implementation coverage

| Requested area | Implementation and evidence |
|---|---|
| Shared contracts and verification boundary | `contracts.py`, `pipeline.py`: separate candidate/reference/report/trace objects, explicit outcomes, sealed evidence rechecked by the renderer. Missing references and failed candidates cannot animate. |
| Local DFA algorithms | `formal/dfa.py`: validation, simulation, reachability, minimisation, canonicalisation, product-BFS equivalence and shortest witnesses, including ε. |
| Direct learned DFA prediction | `models/`: count, acceptance and transition heads; active-state masks; bounded, deduplicated best-first alternatives. No intent-classifier substitution. |
| Frozen backbone and adaptation | Separate frozen/original and trainable/new embedding tables, contextual extension, matched structured task, BERT and separately configured DistilBERT support. Tests check updates, frozen tensors and reloads. |
| Vocabulary and initialisation | Random, subword mean and literal subword mean plus one; occurrence/norm audits and notation-stratified fertility. |
| Reproducible data | `data/generators.py`: semantic families, structural reconstruction, grouped canonical language splits, held-out demonstration languages and bounded sampling. Small JSONL samples are shipped. |
| Training and checkpoints | `training/train.py`, `configs/`: device selection, accumulation, component losses, validation selection, best/last checkpoints and resume. Tiny random-BERT smoke training is executed. |
| CFG mode | `formal/cfg.py`: bounded NLTK Earley worker, independent root/production/yield/ID checker, epsilon, ambiguous tree selection and serialised leftmost derivations. |
| Animations and caching | `rendering/`: trusted Manim scenes, checked traces, deterministic geometry, atomic video writes, quality/input/tree/version-aware keys and subprocess limits. Actual MP4 rendering succeeds locally. |
| Streamlit learning workspace | Two-column desktop cards; stacked phone layout; examples, explicit sources/scopes, stale-result notices, disabled-action reasons, advanced settings, videos and evidence downloads. |
| Baselines and evaluation | Limited rule baseline, vanilla/adapted structured models and disabled opt-in LLM adapter; CSV/JSON/readable reports, explicit support/release coverage, first-prediction versus retry success and not-run ablation tables. |
| Tests and developer experience | Mathematical/model/pipeline/evaluation tests, browser inspection scripts, dependency/render checker, standalone examples, rendering-fixture validation and documented startup commands. |

Paths in the table are relative to `src/theorybert/` unless a different top-level directory is shown. See `VALIDATION.md` for executed checks and artifact locations.

## Gaps closed during this continuation

- Candidate-budget exhaustion no longer consumes and displays an unverified next candidate. Each checked candidate is snapshotted so a generator cannot mutate the history retrospectively.
- The first prediction, last checked candidate and minimised result remain distinct in tables and evidence exports. Individual candidate structures can be inspected.
- An empty prediction stream produces an explicit resource-limit outcome. Failed equivalence checks are no longer shown with success checkmarks.
- A verified machine above the eight-state drawing limit remains available as evidence and tables; its preview cannot crash the application.
- Small DFA layouts are tighter; the scrubber highlights the consumed transition and explains the current state and final outcome in text. Parse-tree branch inspection enlarges local labels, and the selected ambiguous tree survives mode switches.
- Validation loss now honours the same configured component weights as training. Evaluation records alphabet mismatch as an unsuccessful prediction without aborting the run.
- Readable evaluation reports identify the prediction source and separate support coverage, release coverage and released correctness. The smoke checkpoint is explicitly identified as a tiny random backbone.
- Browser QA includes 320-, 390-, 768- and 1440-pixel widths, keyboard interactions, stale results, branch/tree persistence and the larger-machine boundary. `scripts/validate_rendering.py` reproduces representative videos and extracts final frames.

## What remains

| Work | State and next command |
|---|---|
| Genuine pretrained vanilla BERT training | Not run. `.venv/bin/python -m theorybert.training.train --config configs/vanilla.json` |
| Genuine pretrained TheoryBERT training | Not run. `.venv/bin/python -m theorybert.training.train --config configs/theorybert.json` |
| Three initialisations × three seeds and vanilla comparison | Not run. `.venv/bin/python scripts/ablation.py --run --seeds 13 42 123` |
| DistilBERT research experiment | Not run. `.venv/bin/python -m theorybert.training.train --config configs/distilbert.json` |
| Held-out evaluation of genuine trained checkpoints | Requires those training runs. Use the evaluation command in the README for each saved `best` checkpoint. |
| Windows/Linux validation and full MPS training | Not executed. Installation instructions are documented; this validation covers the local Apple Silicon Mac and CPU smoke training. |
| Optional paid/prompted baseline | Disabled and not run. No external generation service is called automatically. |

The ≥70% equivalence goal is still a research target. A future held-out-template or matched-capacity adapter study would support stronger research claims; the current implementation does not claim those results.

## Run the project

```sh
source .venv/bin/activate
python scripts/run_local.py
```

Open http://localhost:8501. Open **DFA Studio**, choose **Ends in 01**, use **Reference demonstration**, then **Build & verify** and play or export the result. CFG parsing and labelled reference demonstrations work immediately. Learned inference requires a checkpoint; the prepared smoke artifact exercises mechanics only.
