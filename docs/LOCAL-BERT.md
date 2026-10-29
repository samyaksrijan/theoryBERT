# Local pretrained BERT engine

The 29 October expansion is now activated at `artifacts/bert-v3/best`: 6,275 descriptions / 696 languages, 87.68% exact equivalence on the expanded held-out test and 90.24% on the original test (previously 62.53%). The separate BERT grammar-production decoder is also trained. See [current architecture, scope, results and resource controls](INPUT-DEPENDENT-ENGINE.md); the 28 October record below is historical.

The engine uses the actual `google-bert/bert-base-uncased` encoder. Training updates its top two pretrained Transformer blocks, a contextual extension, normalization, and direct structured prediction heads. Those heads predict state count, acceptance bits, and every binary transition. No rule parser, reference lookup, or dataset lookup generates learned-mode answers.

The original generic training workflow remains available for the original frozen-backbone vocabulary-adaptation experiments. The dedicated local workflow is a separate condition: new embeddings and lower BERT blocks are frozen, and upper BERT blocks are fine-tuned. It must not be reported as the original matched adaptation study.

## Assets and data

Run from the repository root with the existing virtual environment:

```bash
.venv/bin/python scripts/download_training_assets.py
.venv/bin/python -m theorybert.data.prepare --base-phrasing
```

The asset downloader saves only required model files, tokenizer assets, licenses, and the small KB13 corpus. Source manifests record revisions, URLs, byte counts, and SHA-256 hashes. The original BERT weights are about 421 MiB. No project files or dataset are uploaded by these scripts.

The pilot dataset has 1,785 English/DFA records representing 208 canonical languages. The expanded engine dataset has 3,207 descriptions of the same languages, adding ordinary ways of expressing prefixes, suffixes, substrings, and counts. Both combine 55 successfully converted public KB13 rows with symbolic supervision for starts/ends/contains patterns, count/length modulo, parity, and empty/universal languages. Public descriptions are explicitly restricted to the binary alphabet; targets are full-match regex semantics on that domain. Unsupported BRICS operators, word boundaries, oversized repetition, and constant languages after restriction are rejected, with counts in the manifest. Public targets are checked against Python's independent fullmatch engine on all binary strings up to length six; unit tests exercise conversion separately through length eight.

Equivalent DFAs and all their descriptions are grouped before a seeded 75%/12.5%/12.5% split. The pilot contains 1,363 training, 213 validation, and 209 test descriptions. The expanded corpus contains 2,437 training, 391 validation, and 379 test descriptions, with identical language assignments to each split. English templates overlap across splits; the main score measures unseen formal languages, not unseen language families or arbitrary natural language generalization.

## Training and resource limits

```bash
.venv/bin/python -u -m theorybert.training.local --config configs/local-bert.json
```

The initial run's held-out test measured 59.8% first-candidate equivalence and 79.9% success within five candidates. A subsequent custom-wording audit motivated the expanded supervised corpus. Continue genuine BERT fine-tuning with fresh optimizer state and a lower learning rate:

```bash
.venv/bin/python -m theorybert.data.prepare --output data/generated/english-dfa-expanded.jsonl
.venv/bin/python -u -m theorybert.training.local \
  --config configs/bert-engine.json --initialize artifacts/local-bert/best
```

The pilot and final reports are iterative development measurements, not a strictly blind benchmark across the whole development process. No test examples entered training, and epochs in both stages were selected only by validation performance. The second stage's cache contains only frozen lower-BERT activations; its supervision remains English/DFA pairs.

This configuration is intended for an M1 MacBook Air with 8 GB shared memory. The model caches the immutable first ten BERT blocks' activations in float16, then trains the last two pretrained blocks and the prediction layers in float32 on MPS. Inference runs full BERT normally; it does not need the activation cache or training data. The largest encoded dataset description has 33 tokens, below the 64-token limit. Training fails on truncation instead of silently dropping requirements.

Batch size is two with four-step gradient accumulation. The process limits its MPS allocation to half the recommended budget. A read-only guard samples available storage, system memory availability, and swap throughout encoding, training, and checkpointing. It stops below 3 GiB free disk, below 8% memory availability, or after swap grows more than 1.5 GiB from that process's startup. It never deletes personal files, clears OS caches, or kills other applications. Snapshots are appended to `artifacts/local-bert/resources.jsonl`.

The initial batch-eight attempt completed one epoch before the guard stopped it for swap growth. Training continued with the smaller batch from that saved best checkpoint, restarting optimizer state because the best checkpoint is inference-only. This interruption and restart are preserved in `artifacts/local-bert-run.log` and the epoch CSV. The expanded stage has its own output directory, `artifacts/bert-engine`, and log, `artifacts/bert-engine-run.log`. The trainer uses validation equivalence, then validation loss, for best selection; test data is never used for selection. `best` omits optimizer state to save storage; `last` includes it for a full resume:

```bash
.venv/bin/python -m theorybert.training.local \
  --config configs/bert-engine.json --resume artifacts/bert-engine/last
```

Training writes actual BERT weight fingerprints before and after, verifies frozen layers stayed unchanged, and records time, trainable parameters, dataset hash, and system status. Each stage keeps at most `best` and `last`, updating weights atomically. Rebuildable pip, npm, and uv package caches were cleared for headroom; installed packages and personal files were preserved. The app also refuses smoke checkpoints and overlong descriptions. Without a reference, candidate selection keeps the first valid ranked prediction, rather than accidentally showing the final alternative.

## Evaluation and activation

```bash
.venv/bin/python -m theorybert.evaluation.evaluate \
  --checkpoint artifacts/bert-engine/best \
  --dataset data/generated/english-dfa-expanded.jsonl \
  --output artifacts/bert-engine-evaluation
.venv/bin/python scripts/activate_model.py
.venv/bin/python scripts/check_learned_engine.py
```

The important measures are exact first-candidate language equivalence and bounded-candidate success against independent held-out DFA targets. Structural validity alone is not semantic accuracy. Per-example results, errors, timing, and aggregate metrics are stored alongside the report. The test split must not be used to choose epochs or tune architecture.

`artifacts/active-model.json` records the evaluated default checkpoint and measured score. Activation checks the dataset fingerprint, held-out split, matching checkpoint path, and successful BERT-weight audit. The API advertises it to the frontend, which defaults to learned inference and automatically selects the active real checkpoint. A missing checkpoint is an error; there is no silent fallback. Old browser demo settings use a different storage version so they cannot silently replace the new default. Manually selected reference fixtures and the labelled research rule baseline remain separate tools. The runtime audit disables the rule predictor, counts full BERT forward passes, and compares a trained upper layer and unchanged lower layer against the original downloaded pretrained weights.

## Using the app

```bash
.venv/bin/python scripts/run_local.py --skip-build
```

Open `http://localhost:8501/dfa`. Describe the binary regular language, enter a test string, keep **BERT model**, and build. With no independent reference, the predicted machine's diagram, transitions, and execution are visible as an unverified candidate. Supplying a reference or selecting a benchmark allows exact equivalence checking and verified MP4 export. A failed equivalence check remains a failure, with a distinguishing counterexample; it is never relabelled as successful inference.

Choose **My own DFA JSON** to validate and inspect a machine you provide. That path does not claim AI prediction. Grammar Lab continues to use an Earley parser and an independent derivation checker for supplied grammars: CFG parsing is a formal algorithm and this DFA model is not a grammar generator.

The scope is a binary alphabet and at most eight learned states. Successful training does not imply correctness on arbitrary English or nonregular languages. The locally trained engine is not automatically uploaded to the existing Render deployment, whose runtime excludes Torch and model artifacts.

## Recorded result — 28 October 2026

The activated checkpoint is `artifacts/bert-engine/best`, selected at expanded-stage epoch 9 by validation performance. The final stage updated 19,015,056 parameters, including the two upper pretrained BERT blocks, in 1,062 seconds on MPS. The best expanded validation equivalence was 69.1%. The frozen-layer fingerprints matched before and after training; upper BERT weights changed. The separately measured test result is:

| Measure | Observed result |
| --- | --- |
| First-candidate exact language equivalence | 237 / 379 descriptions, **62.5%** |
| Success within five candidates, with independent reference | 304 / 379 descriptions, **80.2%** |
| Held-out canonical languages | 26 |
| Structural validity | 100% |
| Incorrect candidates admitted by the equivalence gate | 0 |

The 70% first-prediction research target has not been achieved on this held-out set. The bounded success rate requires an independent reference to identify a correct alternative; a custom request without a reference shows the first valid model prediction and explicitly leaves semantic equivalence unverified. These are measured development results for the documented families, not a guarantee of arbitrary English understanding.

The runtime audit disabled `RuleBased.predict`, counted four full BERT forward calls, compared upper/lower weights against the original downloaded BERT, and independently confirmed the custom request “Please recognize binary strings ending with 10.” produced exactly that language. All three built-in benchmark requests also passed equivalence within five learned candidates. No rule or dataset lookup supplies the learned predictions.

Validation passed **52 automated tests**, the HTTP boundary checks, and desktop/mobile browser checks with **26 screenshots** and no page errors. These exercised real learned inference, custom English previews and playback, imported DFA names and unreachable states, CFG parsing/ambiguity/epsilon, proof-gated export, byte ranges, navigation, and mobile overflow. A fresh uncached BERT-to-verified-video export rendered in 4.33 seconds; its final frame was visually inspected and showed the expected accepting state. Screenshots were also inspected.

The server was left running on `http://localhost:8501/dfa`, with the evaluated checkpoint automatically selected. Available disk space after cleanup was approximately **7.4 GiB**. macOS reported no thermal or performance warning. Pip/npm/uv download caches, the superseded pilot resume copy, and completed frozen-activation caches were removed; installed packages, both best checkpoints, the final-stage resumable checkpoint, datasets, source, videos, and logs were retained. There are no training processes left running.

Evidence files:

- `artifacts/implementation-validation.json`: combined completion and resource record.
- `artifacts/bert-engine-evaluation/`: per-example CSV, exact metrics, metadata and report.
- `artifacts/bert-engine/summary.json` and `training.csv`: training measurements and BERT-weight fingerprints.
- `artifacts/bert-engine/resources.jsonl`: memory, swap, and storage samples during training.
- `artifacts/learned-engine-audit.json`: real forward calls, disabled-rule audit, weight comparison, and custom prediction.
- `artifacts/bert-video-export.json` and `bert-video-final.png`: fresh end-to-end video and inspected final frame.
- `artifacts/learned-ui/` and `artifacts/react-ui/`: browser reports and screenshots.
- `artifacts/training-cleanup.json`: exact project-generated files removed during cleanup.
