# BERT semantic-plan experiment

The active local DFA model is `artifacts/bert-plan/best`. It uses the immutable evaluated V3 BERT encoder and a 537,385-parameter plan head with learned literal copying. English interpretation stays in BERT and the learned head. Typed formal constructors compile the predicted plan; no English keyword rules or benchmark answer replacement are used.

The canvas, layout, renderer, Manim scenes and principal style sheets are unchanged. Their pre/post hashes are in `artifacts/plan-visual-check.json`. A changed requirement can change states and transitions. A changed test string changes the trace of the same machine.

## Measured comparison

| First-candidate exact equivalence | V3 direct | Plan |
|---|---:|---:|
| Original 641-case regression test | 87.68% | 95.32% |
| Fresh matched test, 57 cases | 7.02% | 66.67% |
| Fresh all-case test, 120 cases | 3.33% | 71.67% |

The all-case comparison includes 63 cases outside the original direct head's supported scope. Matched cases have at most eight states and at most 64 baseline tokens. The comparison is synthetic, uses one seed, and evaluates an architecture plus data change. It is not proof of broad English understanding. Fresh suffix wording remains weak at 1/18 correct, while exact-word and substring cases score 23/23 and 21/21.

Selection used only validation and known product fixtures. Matched fresh validation improves by 51.35 percentage points, original validation improves from 90.34% to 98.39%, and all DFA product fixtures pass. The selection record is written before test prediction. Test cases were not used for retraining. V2 is now exposed and must not be reused as an untouched test for another iteration.

Training took 230.8 seconds including frozen feature extraction. Only the head is trained, compared with 19,015,056 trainable parameters in the earlier direct V3 condition. Measured prediction latency is higher: fresh median approximately 39.7 ms versus 34.0 ms. This is improved correctness and adaptation cost, with a local inference-time cost.

## Data and resources

`english-plan-v1.jsonl` has 11,415 examples, 2,914 canonical languages, and 9,187 / 1,171 / 1,057 train / validation / audit-test rows. Equivalent formal languages remain in one split. The fresh v2 comparison has 134 validation and 120 test cases; none of its languages is in plan training.

The run uses two CPU threads and reduced scheduling priority. An initial dense-cache extraction was stopped after increased memory pressure. The completed implementation caches packed real-token float16 features on disk, pads small batches on demand and removes that cache after training. Resource guards enforce a 3 GiB disk floor, 8% memory-availability floor and 0.75 GiB swap-growth allowance. No unrelated jobs or user files are removed.

## Reproduction and evidence

- `src/theorybert/data/plans.py`: data generation and frozen comparison.
- `src/theorybert/models/semantic.py`: head, pointers, typed beam and resource-guarded training.
- `src/theorybert/formal/plan.py`: exact typed-plan compiler.
- `src/theorybert/models/predictor.py`: checkpoint dispatch and shared encoder injection.
- `scripts/compare_plan_model.py`: validation gates, committed selection, then test.
- `artifacts/plan-promotion-protocol.json`: frozen thresholds.
- `artifacts/plan-comparison/`: full per-case outcomes, latency and selection.
- `artifacts/bert-plan/best/`: head weights, configuration, summary and resources.
- `docs/reports/`: report prose, sources and reproducible PDF builder.

Do not overwrite v2 after observing results. A later study needs new output paths, a new comparison version, matched-data controls and multiple seeds. Model weights and generated datasets are ignored by Git and are not automatically published by this work.
