# Executed validation

## React product follow-up — 24 October 2026

The primary interface is now the five-page React product. The Streamlit inspection below documents the earlier interface and is retained as historical evidence.

The production Vite build passed with React 19.3.1, Vite 8.3.5, Node 25.6.1 and npm 11.9.0. The local API ran with Starlette 1.9.0 and Uvicorn 0.54.0. `python -m pytest -q` passed all **26 tests** after the API and rendering changes.

`python scripts/check_web_api.py --base-url http://127.0.0.1:8502` passed real HTTP checks for DFA acceptance and rejection, failed candidates and shortest ε witnesses, missing references/checkpoints, duplicate-key JSON, the larger-machine drawing limit, CFG ambiguity/epsilon, forged result handles, actual DFA and CFG Manim exports, byte-range video playback, and direct React route refreshes. The server keeps verification evidence and rechecks it before rendering.

`python scripts/inspect_react.py --base-url http://127.0.0.1:8502` passed and captured **21 screenshots**, with no page errors or horizontal document overflow. It exercised all five pages, empty and verified workspaces, failed verification, missing reference/checkpoint, stale-result invalidation, keyboard controls, settings, tree selection, example search, rendering progress and completed video playback. Layouts were checked at 1440, 768, 390 and 320 pixels wide. Desktop and mobile screenshots were visually reviewed; native Chrome also exercised DFA trace and real video playback. Manim exports now use the shared rose/violet/teal product palette and packaged DM Sans/IBM Plex Mono fonts.

Evidence: `artifacts/react-build.log`, `artifacts/react-api-checks.log`, `artifacts/react-browser.log`, `artifacts/react-ui/`, `artifacts/frontend-environment.txt`, and `artifacts/tests.log`. These checks validate the local product and formal/rendering integration; no full research training was run.

The public landing was subsequently rebuilt around the user's supplied visual reference, and the same white/black/pink identity was extended through every product page, settings and exports. Canvas geometry and interaction controls were preserved. All 26 formal tests and actual API/video-export checks were rerun successfully after the shared palette/font change. The browser suite additionally checks the hero mode switch loading the arithmetic example, showcase pause, live search, combined category/search empty states, clearing filters, alphabetical sorting, topic-chip selection, gallery navigation and the mobile menu/Escape behavior. Full-page desktop/mobile captures include all six actual reference examples. The landing's arithmetic tree follows the shipped precedence grammar and matches `id + id * id`; its ambiguity and balanced-language previews have their own matching trees.

The stacked Poppins logo and startup write-on sequence were validated separately with `python scripts/inspect_brand.py`. It passed normal playback, automatic landing reveal, Skip/Escape, focus restoration, body-scroll cleanup, no replay during navigation, immediate direct studio access, reduced-motion bypass and 1440/390-pixel layouts. Visual stages are recorded under `artifacts/brand-ui/`; the execution log is `artifacts/brand-browser.log`.

To repeat the current product checks:

```sh
python scripts/run_local.py
# In another terminal, in the same environment:
python -m pytest -q
python scripts/check_web_api.py
python scripts/inspect_react.py
```

## Earlier prototype validation

Validated locally on 23 October 2026, on an Apple Silicon Mac running macOS 26.5.2. Python 3.12.4, PyTorch 2.14.1, Transformers 4.57.6, Streamlit 1.66.1, NLTK 3.10.4, Manim 0.22.0 and ffmpeg 9.0.2 were actually installed. CPU and Apple MPS were detected; CUDA was unavailable. Training smoke and model tests ran on CPU. No full MPS training claim is made.

## Mathematical and model checks

`python -m pytest -q` passed **26 tests**, including parametrised pattern-language and grammar examples. Actual log: `artifacts/tests.log`.

Coverage includes:

- starts/ends/contains constructors checked by exhaustive short strings;
- contains-versus-suffix mismatch and shortest counterexample minimality;
- ε acceptance disagreement, state renaming and unreachable states;
- minimisation language preservation and canonicalisation idempotence;
- missing/invalid transitions, alphabet mismatch, explicit multi-character tokens and duplicate JSON keys;
- valid CFG derivations, wrong root, illegal production, wrong terminal yield, ε, ambiguity, unparseable input and subprocess limits;
- output shapes, active-row/destination padding masks, finite losses, useful new-embedding gradients, extension/head updates and frozen original rows under AdamW;
- BERT and DistilBERT checkpoint reload preserving predictions;
- argmax count decoding, unique bounded alternatives, budget limits, missing-reference and failed-candidate render gates;
- a verified DFA rejecting an input remaining renderable, empty counterexample representation, tree seals and render keys differing by input/quality;
- evaluation distinguishing incorrect first candidates from success after retries.
- budget exhaustion retaining the last actually checked candidate without consuming another prediction, immutable snapshots of reused candidate objects, and explicit empty-stream failure;
- validation respecting configured loss weights, and evaluation reporting incompatible alphabets without terminating the run.

The training smoke used six examples, a **tiny randomly initialised BERT**, one epoch and a vocabulary extension. It performed real forward/loss/backward/optimiser passes, checked frozen tensors exactly, verified updates for new embeddings, extension and each head, then reloaded and compared predictions exactly. Logs and checkpoint metadata are under `artifacts/smoke/` and `artifacts/smoke.log`. This is mechanics validation, not pretrained-model research accuracy.

The limited rule baseline was actually evaluated on the shipped test split: 8 of 40 semantic descriptions supported and equivalent (20% coverage and raw equivalence); the single structural-reconstruction test description was unsupported. No incorrect candidate was released. Correctness among released outputs uses the same reference as the gate and is a checker property. Actual CSV/JSON/Markdown measurements are in `artifacts/evaluation/`. The smoke-checkpoint evaluation is separately labelled under `artifacts/smoke-evaluation/` and is not used as a BERT/adaptation comparison.

## Actual rendering

`python scripts/check_environment.py --render` passed a real minimal Manim text render. It was not mocked. The dependency report is `artifacts/environment.json`.

Real Manim/ffmpeg MP4s were rendered and final frames inspected for:

- suffix recogniser accepting `1101`;
- the same verified machine rejecting `00`;
- empty input;
- an eight-state structural reference fixture;
- no accepting states and an all-accepting one-state machine;
- the arithmetic parse tree.

`artifacts/visuals/manifest.json` records the concrete video paths, actual render times and cache-hit flags. Final frame images are alongside it. A 22-symbol execution also rendered through the running UI while its progress state was captured. Long executions use a moving 12-symbol window in the video so the current symbol remains readable. Input, source/destination and final outcomes come from the checked trace, not an independently inferred animation.

`python scripts/validate_rendering.py` reproduces the representative fixtures and extracts final frames with ffmpeg. Drawing geometry and video cache identities were updated together to avoid replaying stale visuals.

## Browser inspection

Chromium/Playwright inspected the running Streamlit app at **1440 × 1100** and **390 × 844**, with additional empty-workspace layout checks at **320 × 1000** and **768 × 1000**. Full-content screenshots temporarily increase viewport height at the same width, while detail captures retain the actual narrow diagram width. The controls remain standard Streamlit widgets; CSS targets app-owned classes and documented container key hooks.

The inspection exercised empty and populated states, verification success, verified string rejection, deliberately incorrect fixture, shortest ε witness, unavailable checkpoint, missing independent reference, stale results after edits, rendering progress, completed DFA/CFG videos, arithmetic parsing, ambiguity and no derivation. Assertions check disabled actions, absence of old videos after input edits, page exceptions and horizontal document overflow. Screenshots were visually reviewed for spacing, label clarity, wrapping and graph/tree layout; diagram framing, fonts, start arrows and mobile label sizes were adjusted from those observations.

Additional checks exercised the actual local smoke checkpoint, malformed reference JSON, reference upload, long-video playback readiness, switching modes without losing inputs/results or a selected ambiguous tree, branch inspection, and changing rendering quality while retaining verification. A verified nine-state machine remains inspectable with a disabled render control and an explicit drawing-limit message. Keyboard controls are used for the execution scrubber and rendering quality. Scripts: `scripts/inspect_ui.py` and `scripts/inspect_advanced_ui.py`; evidence: `artifacts/ui/`, `artifacts/browser.log`, `artifacts/browser-advanced.log`. Each browser report lists the screenshots captured by that run, separately from older artifact files.

To repeat:

```sh
streamlit run app.py
# In another terminal, in the same environment:
python -m playwright install chromium
python scripts/inspect_ui.py
python scripts/inspect_advanced_ui.py
# Reproduce representative videos and final-frame screenshots:
python scripts/validate_rendering.py
```

Run the browser scripts sequentially. They perform actual local renders; do not run a full training job concurrently. Pure import/compilation and unused-import checks also passed.

## Remaining work and limits

No concrete dependency blocker remains on this Mac. There is **no genuinely trained pretrained BERT checkpoint**. Vanilla/adapted research training, multi-seed initialisation ablations, DistilBERT research experiments and optional paid LLM evaluation were not run. `scripts/ablation.py` produces explicit not-run rows; it does not invent mean/std values.

Windows/Linux instructions are documented but were not executed. The v1 learned task is binary and bounded to eight states. Visualisation is intentionally bounded: 40 DFA input symbols and parse trees of at most 45 nodes, 12 leaves and ten levels. Dense automata can have crossing curves; deterministic placement keeps node and label positions stable and the execution highlight identifies the traversed edge. Larger formal structures can still be inspected as tables/evidence, without pretending an unreadable video is useful.
