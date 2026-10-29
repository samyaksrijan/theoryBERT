# TheoryBERT

A local research prototype for **English → adapted BERT → structured DFA → independent formal verification → Manim animation**, with a second mode for verified CFG parse trees.

The input-dependent engine adds automatic test-word simulation, grammar-aware tokenization, FIRST/FOLLOW and LL(1) analysis, an arithmetic compiler with AST and checked three-address code, and a separately trained BERT grammar-production decoder for English-to-CFG requests. BERT interprets natural language; formal algorithms check, execute and render its outputs. No handwritten English compiler or symbolic repair replaces a failed neural prediction. See [the implementation and research notes](docs/INPUT-DEPENDENT-ENGINE.md).

The next-stage [fresh challenge audit](docs/FRESH-CHALLENGE.md) tests unfamiliar wording and combined conditions. It records the large gap from generated-template scores, the retained DFA checkpoint, the promoted grammar decoder, and the remaining limitations rather than substituting constructed answers.

The local learned engine now has a dedicated workflow: pinned `google-bert/bert-base-uncased` weights, audited KB13 regex-to-DFA conversion plus generated English/DFA supervision, fine-tuning of the top two pretrained BERT blocks and direct DFA heads, and exact held-out equivalence evaluation. See [the local BERT guide](docs/LOCAL-BERT.md). There is no rule fallback in learned mode. Model weights stay out of Git history. The evaluated inference assets are published as a versioned GitHub Release bundle, pinned by SHA-256 in `deploy/model-bundle.json`.

The main product is a **React application** with a public landing page, DFA Studio, Grammar Lab, Example Library and Research pages. The landing follows the supplied visual reference: a white canvas, horizontal navigation, bold black/pink typography, a diagonal animated showcase, and a searchable gallery of real worked examples. Its mode switch and gallery open the relevant studio with the selected example loaded. The studios, library, research page and settings share the same white/near-black/pink identity, self-hosted DM Sans typography and a stacked Poppins wordmark (BERT above THEORY). On a fresh landing-page load, the outlined logo writes itself on white and fades into the page; normal navigation and direct studio access remain immediate. Interactive SVG canvases retain their playback, zoom, pan, node inspection and fullscreen controls; their state palette matches tables and Manim exports. A local Starlette API connects it to the existing Python research engine and real Manim exports. No service, API key or trained checkpoint is needed for CFG parsing or labelled reference demonstrations. The earlier Streamlit app is retained as an optional legacy interface.

## Start here

The prepared environment in this workspace is ready:

```sh
source .venv/bin/activate
python scripts/run_local.py
```

Open **http://localhost:8501**. The launcher builds the frontend and serves the product and API together on loopback. DFA Studio defaults to **BERT model**, using the evaluated checkpoint recorded in `artifacts/active-model.json`. Enter an English language description and a binary test string, then **Build & verify**. BERT directly predicts the machine; without an independent reference, semantic equivalence remains unverified. Example chips include independent references, and successful equivalence checks unlock MP4 export. Changing only the test word updates the trace without another BERT forward pass. Grammar Lab defaults to a trained BERT production decoder for English-to-CFG generation; its exact parser checks the selected derivation, not equivalence to arbitrary English. Explicit formal inputs and reference demonstrations remain labeled separately.

The frontend requires Node.js 22.12+ (tested: Node 25.6.1, npm 11.9.0). The first launch uses `npm ci`; later launches reuse installed dependencies. Use `python scripts/run_local.py --skip-build` for an unchanged existing build, or `--port 8502` for another port. Model/checkpoint, candidate budget, tree limit and export quality live in **Workspace settings**. Independent reference JSON can be pasted or uploaded directly in DFA Studio.

For a fresh installation, use Python 3.10+ (tested: Python 3.12.4):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/check_environment.py --render
python scripts/run_local.py
```

Alternatively, `uv venv .venv --python python3` followed by `uv pip install -e '.[dev]'`. Use an isolated environment: inheriting globally installed torchvision with a different PyTorch version can break Transformers imports.

Manim system requirements:

- **macOS:** `brew install cairo pango pkg-config ffmpeg`, then install Python dependencies.
- **Debian/Ubuntu:** `sudo apt-get install build-essential pkg-config libcairo2-dev libpango1.0-dev ffmpeg python3-dev python3-venv`, then install Python dependencies.
- **Windows:** use the official Manim local-install guide for Cairo/Pango and install ffmpeg on PATH; WSL with the Linux command is an alternative. Windows and Linux were not tested here.

All scenes use `Text`; LaTeX is unnecessary. Exported animations use the included DM Sans and IBM Plex Mono font assets and the same state palette as the React canvas. Installation references: [Manim](https://docs.manim.community/en/stable/installation.html), [Vite](https://vite.dev/guide/), [Motion](https://motion.dev/docs/react), [Starlette](https://starlette.dev/routing/). Actually tested Python versions are in [requirements-tested.txt](requirements-tested.txt), and frontend versions are pinned in [frontend/package-lock.json](frontend/package-lock.json).

## Verification boundary

Minimisation does **not** prove that a DFA matches English. Exact equivalence needs a second, independently grounded formal reference. For generated benchmarks this is the separately stored ground truth. For live requests, upload or paste an independent reference in DFA Studio; [reference-suffix-01.json](data/examples/reference-suffix-01.json) shows the schema.

Without a reference the model may predict, display its diagram and transition table, and simulate a string, but the result is **REFERENCE_UNAVAILABLE**: structure is checked, language equivalence is unverified, and verified video export stays disabled. Other outcomes are **STRUCTURE_INVALID**, **EQUIVALENCE_FAILED**, **VERIFIED**, **RESOURCE_LIMIT** and **INTERNAL_ERROR**. Only VERIFIED can create a sealed object for video export. The renderer rechecks the sealed candidate/reference pair, creates a trace, and consumes that trace. A verified machine rejecting a string is not a verification failure.

The demonstration source intentionally loads a known reference, identifies that fact, and demonstrates execution. It is excluded from learned accuracy claims. The incorrect fixture complements accepting states of the selected reference; this necessarily changes empty-string membership. Its real shortest counterexample is displayed and rendering is blocked. The model and retry decoder never receive reference transitions or counterexamples.

CFG mode verifies one **derivation**, not equivalence between arbitrary grammars. NLTK Earley constructs trees; a separate recursive checker inspects the root, productions, typed terminal leaves, stable IDs and exact yield. Whitespace separates tokens, quoted strings denote terminals, and an empty right-hand side denotes ε:

```text
S -> 'a' S 'b' |
```

Blank input is the empty string. Grammar-terminal tokenization handles `aabb` or `id+id*id` directly; whitespace tokenization remains available for explicit boundaries. The **Arithmetic compiler** preset handles real identifier/number lexemes, shows an AST, and generates checked three-address code. The **Compiler analysis** tab computes nullable symbols, FIRST/FOLLOW sets and predictive-table conflicts for the supplied grammar. Multiple trees can be selected; bounded enumeration never proves unambiguity. Parsing has an eight-second subprocess budget, 64-token and 200-production limits. Trees above 45 nodes, 12 leaves or ten levels cannot render, with an actionable message.

## Data, training and evaluation commands

Run all commands from the repository root with the environment active.

```sh
# Deterministic data. The shipped sample contains 261 descriptions / 96 languages.
python -m theorybert.data.generators --output data/examples/sample.jsonl --seed 42 --random-languages 12
# More structural reconstruction languages; bounded retries detect an exhausted pool.
python -m theorybert.data.generators --output data/generated/larger.jsonl --seed 42 --random-languages 500

# Mathematical, model and pipeline checks.
python -m pytest -q
# Genuine forward/loss/backward/update/reload test with a tiny RANDOM BERT.
python -m theorybert.training.train --smoke

# These commands download a public pretrained backbone if it is not cached.
# They are larger, opt-in experiments and were NOT run during implementation.
python -m theorybert.training.train --config configs/vanilla.json
python -m theorybert.training.train --config configs/theorybert.json
python -m theorybert.training.train --config configs/distilbert.json
# Set a larger total epochs value in the same config before resuming.
python -m theorybert.training.train --config configs/theorybert.json --resume artifacts/theorybert/last

# Prepare explicit “not run” tables; performs no training.
python scripts/ablation.py
# Full vanilla + 3 initialisation strategies, seeds 13, 42, 123 (opt-in).
python scripts/ablation.py --run --seeds 13 42 123

# Limited rule-based baseline; unsupported cases count as incorrect, coverage reported.
python -m theorybert.evaluation.evaluate --output artifacts/evaluation
# Genuine learned checkpoint evaluation after training.
python -m theorybert.evaluation.evaluate --checkpoint artifacts/theorybert/best --dataset data/examples/sample.jsonl --output artifacts/theorybert-evaluation
# Mechanics-only evaluation of the smoke checkpoint; never research evidence.
python -m theorybert.evaluation.evaluate --checkpoint artifacts/smoke/best --output artifacts/smoke-evaluation
# Optional real rendering latency on released outputs.
python -m theorybert.evaluation.evaluate --render --output artifacts/render-evaluation

# Real standalone reference-demo and verified-tree videos.
python scripts/render_example.py --mode dfa --string 1101
python scripts/render_example.py --mode dfa --string 00
python scripts/render_example.py --mode cfg
# Add --quality high for 1080p/60 fps; default preview is 480p/15 fps.

# Actual HTTP and isolated browser acceptance checks against the running React product.
python scripts/check_web_api.py
python -m playwright install chromium
python scripts/inspect_react.py
# Representative verified video fixtures and final-frame images.
python scripts/validate_rendering.py
```

Configurations are JSON under [configs](configs). Adjust `dataset`, `output`, state bound, sequence length, batch size, accumulation, epochs, learning rate, device and component loss weights. Defaults are deliberately conservative, not a guarantee of fitting every 8 GB GPU. Mixed precision is disabled; CPU, CUDA and Apple MPS are detected. DistilBERT is a separate configuration, never merged into BERT comparison rows.

The smoke run saves `artifacts/smoke/best` and `last`, with explicit **tiny random backbone** metadata. This checkpoint exercises the architecture but is not trained BERT research evidence. The genuine pilot is preserved at `artifacts/local-bert/best`; the expanded active engine and resumable state are at `artifacts/bert-engine/best` and `last`. Activation requires separate held-out evaluation. Weights are not committed to Git.

Training persists tokenizer, backbone configuration, DFA schema version, model/optimizer state, CSV component losses, validation equivalence/loss and embedding audits. Best selection maximises validation equivalence, breaking ties by validation loss. The test split is not used for selection. Resuming restores optimiser and epoch state. No training runs from a Streamlit rerun.

## Research design

See [docs/RESEARCH.md](docs/RESEARCH.md) for architecture, initialisation definitions, splits, metric meanings and limits. The primary model predicts state count, accepting bits and transition destinations directly; it is neither an intent classifier nor a handwritten constructor disguised as learning.

- Frozen vanilla BERT: original tokenizer, frozen backbone, trainable normalisation and structured heads.
- TheoryBERT: original weights frozen, separate trainable new-token embeddings, a trainable contextual Transformer extension, the same structured heads.
- Rule-based baseline: explicitly restricted patterns and honest unsupported results.
- Optional prompted LLM adapter: disabled by default; requires an explicitly supplied generation callable. No networking or paid calls happen automatically.

The local pretrained fine-tuning run is recorded separately from fair vanilla/adapted comparisons, initialisation ablations and multi-seed research experiments, which remain **not run**. The Research page reads the activated model's actual evaluation files and never substitutes verified-release precision for model accuracy.

## Demonstration and validation

1. **Correct:** reference demo `Ends in 01`, `1101`, build and verify, then play or export; change to `00` and verify/play the REJECT execution. Once genuinely trained, choose **Learned checkpoint** and set its path in Workspace settings to demonstrate learned inference against the benchmark reference.
2. **Incorrect:** select **Incorrect candidate fixture**, verify, inspect `ε` as a shortest counterexample and the disabled render control. This is a deliberate fixture, not a model failure.
3. **Comparison:** inspect `artifacts/bert-engine-evaluation/report.md` for the active learned engine, `artifacts/local-bert-evaluation/report.md` for the pilot, and `artifacts/evaluation/report.md` for the historical limited rule baseline. These use different datasets and are not a controlled comparison. Matched vanilla/adapted experiments remain unrun.

The [prompt audit](docs/COMPLETION.md) maps the requirements to implementation and lists the remaining opt-in experiments. The tested environment, actual validations, screenshots and remaining limits are documented in [docs/VALIDATION.md](docs/VALIDATION.md). Generated videos, datasets, checkpoints and screenshots live under ignored `artifacts/` or `data/generated/`. Source, small examples and configurations are retained.

## Source map

| Location | Responsibility |
|---|---|
| `frontend/src/`, `frontend/public/` | React pages, design system, persistent sessions, interactive SVG diagrams, bundled fonts |
| `src/theorybert/web.py`, `scripts/run_local.py` | Local product/API server, background jobs, server-owned render evidence and startup |
| `app.py`, `src/theorybert/ui/` | Optional legacy Streamlit workspace |
| `contracts.py` | JSON-safe DFA, CFG, tree, trace, benchmark and report contracts |
| `formal/` | Validation, simulation, reachability, minimisation, BFS equivalence, Earley and independent tree checker |
| `data/` | Symbolic references, paraphrases, structural reconstructions, grouped splits |
| `models/` | Split embeddings, contextual extension, structured heads, masked loss and bounded decoding |
| `training/`, `evaluation/` | Checkpoints, experiment logs and measured CSV/JSON/Markdown results |
| `pipeline.py` | Candidate deduplication, bounded verification and renderable evidence boundary |
| `rendering/` | Shared layout, SVG previews, trusted Manim scenes and atomic video cache |
| `tests/`, `scripts/` | Correctness checks, reproducible demos, dependency and browser checks |

## Frontend development and legacy interface

For live frontend editing, run `.venv/bin/python -m theorybert.web --port 8502` and, in `frontend/`, run `npm run dev`. Vite serves **http://localhost:5173** and proxies `/api` to the Python engine. For normal use, the single-server launcher above is sufficient.

The original Streamlit interface remains available with `streamlit run app.py --server.port 8503`. Its browser scripts are `scripts/inspect_ui.py` and `scripts/inspect_advanced_ui.py`; those scripts target the legacy interface on port 8501 and are not the acceptance tests for the React product. See [docs/UI-DESIGN.md](docs/UI-DESIGN.md) for the new design and interaction model.

## Render deployment

The repository includes a multi-stage `Dockerfile` and `render.yaml`. Render builds the React frontend, installs Cairo/Pango/ffmpeg, then serves the frontend and Python API together with a single Uvicorn process bound to `0.0.0.0:$PORT`. The health endpoint is `/api/health`.

The default Docker build installs CPU PyTorch and Transformers plus a hash-checked release bundle containing the evaluated FP32 BERT encoder, semantic plan head and grammar head. BERT interprets English; formal compilation, equivalence checking and derivation checking establish the displayed mathematical properties. CPU memory-mapped loading retains every weight byte and precision, while sharing the encoder between heads. Startup fails if either active checkpoint cannot load. `/api/health` reports model readiness and the deployed Render commit. `--build-arg THEORYBERT_RUNTIME=demo` is an explicit reference-only image, with no neural inference. Small recorded validation reports in `data/research/` describe the executed local runs, not Render hardware. The hosted parser has a 45-second wall-clock budget to include Python/NLTK worker startup on the free CPU; local parsing retains its eight-second default, and grammar/token/tree limits stay in effect.

Use one application process: verified result handles are kept in process memory. The free configuration runs one background task at a time, with a second queued request allowed. Browser inputs and session snapshots persist in browser storage. Render's free filesystem is ephemeral: cached videos and server verification handles disappear on restart; verify and export again when needed. Free services also sleep after inactivity and may take a moment to wake up. See [Render Docker deployment](https://render.com/docs/docker) and [free service limits](https://render.com/docs/free).

## Latest local DFA approach

The active model is now a [BERT semantic-plan decoder](docs/SEMANTIC-PLAN.md) with learned literal copying and exact DFA construction. The final graph and playback presentation are unchanged. First-candidate equivalence improves from 87.68% to 95.32% on the 641-case regression set and from 7.02% to 66.67% on the 57-case matched fresh test. This is a single-seed generated comparison; suffix wording remains a documented weakness. Inference is slightly slower, while the trainable head is much smaller. Full results and resource details are in the linked experiment note.

The eight-page IEEE-style manuscript and comprehensive report are generated under `output/pdf/` from `docs/reports/`. They include source links, data lineage, architecture, measured comparisons and limitations.

The GitHub verification workflow runs the unit suite and frontend build. Its optional model-container job builds the actual release bundle and exercises BERT DFA, grammar, compiler, invalid-input rejection and MP4 export in a Docker container limited to 512 MB. Deployment readiness is measured by this job, not inferred from model size. The technical reports and dataset provenance archive are in `output/pdf/`.
