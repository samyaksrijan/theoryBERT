# Research protocol and limits

## What is predicted

BERT is an encoder, so it is followed by explicit structured heads. Binary input alphabet `{0,1}`, maximum eight states, and canonical start state `q0` define the first output space. A pooled contextual representation yields:

- state-count logits: `[batch, max_states]`, classes 1…max_states;
- accepting-membership logits: `[batch, max_states]`;
- transition logits: `[batch, max_states, 2, max_states]`.

Training uses minimal, reachable, breadth-first canonical reference targets. Count uses cross-entropy; accepting bits use BCE-with-logits only on active states; transitions use cross-entropy on active source rows with destinations outside the target count masked out. Configurable weights combine the three losses. Padding never contributes to acceptance/transition losses. Inference restricts every destination to active states without consulting the reference.

The first candidate uses argmax count and argmax active-row heads. Alternatives use bounded best-first search with cost `count NLL + sum(local NLL − best local NLL)`. This preserves the ordinary argmax first candidate without a length bias towards one-state automata. Neighbours advance one independent acceptance/transition choice; every state-count choice is a separate search root. Candidates are deduplicated, budgets are bounded, and verification stops on the first equivalent candidate. There is no trained counterexample repair mechanism. First-candidate accuracy and within-budget success remain separate metrics.

## Adaptation

Both vanilla and adapted configurations freeze the pretrained backbone and disable its dropout during training. The adapted variant replaces only input embedding lookup with two separate tables: an immutable copy of all original rows and trainable rows for added token IDs. The optimiser never owns frozen rows, so AdamW decay cannot drift them. Backbone computation remains in autograd to propagate derivatives to new embeddings.

The contextual extension is a small residual Transformer layer applied to contextual token representations with an attention padding mask. Its output participates in pooling and the structured heads. This is **exBERT-inspired**, not an exact reproduction of that architecture or training protocol. Vanilla has no extension. The different trainable parameter counts are recorded; a vanilla/adapted comparison alone therefore does not isolate vocabulary adaptation from adapter capacity. Additional matched-capacity controls would be needed for that stronger claim.

The predefined vocabulary is independent of held-out data. Tokens already present in the original vocabulary are not added. Audits record original-token decomposition, fallback, initial/final norms, surface occurrences and actual token-ID occurrences in training text. Tokens that never occur cannot acquire task gradients; inspect that audit before interpreting an experiment. Standard uncased tokenizer normalisation is retained; notation coverage must be measured rather than assumed.

Initialisation for original embedding table `E` and usable original subword IDs `I(t)`:

| Strategy | Literal definition |
|---|---|
| `random` | Independent Normal(0, σ²) coordinates, σ = empirical standard deviation of `E` |
| `subword_mean` | `mean(E[i] for i in I(t))` |
| `subword_mean_plus_one` | The preceding mean **plus 1.0 in every coordinate** |

Unknown IDs and empty decompositions are unusable; their mean falls back to the seeded random vector and is logged. Plus-one applies after this fallback too. Adding 1.0 is a large distribution shift, not an assumed improvement. Training checks finite loss, clips gradients and records individual component losses and embedding norms. Full stability comparisons remain unrun.

## Data and leakage

Symbolic constructors belong to reference generation and the labelled rule baseline. They never produce a learned prediction. Semantic families include starts/ends/contains patterns, parity, count/length modulo, a bounded conjunction, and universal/empty languages. Structural reconstruction examples describe complete randomly sampled DFA transition systems honestly, without inventing simple semantic meanings.

Canonical language identity means remove unreachable states, minimise, traverse in sorted alphabet order, rename breadth-first. Equivalent languages are grouped **before** splitting; all their paraphrases stay together. Sampling has a finite retry budget. The shipped sample uses seed 42 and 12 additional structural languages, yielding 261 descriptions and 96 unique languages: 181 train, 39 validation, 41 test examples. Manually selected demonstration/challenge languages are excluded from all three splits and stored in `challenges.jsonl`.

This main evaluation holds out **formal targets/parameters**, while sharing English templates across splits. It is not a held-out-template or unseen-family evaluation. A future template-generalisation study must use a separate split protocol and report it separately. The script does not silently label the main split as that study. Semantic and structural categories receive separate results; notation strata are also recorded. A 96-token input limit can truncate longer structural descriptions; evaluation logs that fact and a research run should increase the configured sequence length when required.

## Formal algorithms

DFA structural checks cover unique/nonempty names, unique/nonempty alphabet symbols, declared start/accept states, exactly one destination for every state/symbol, and declared targets. Strict JSON loading rejects duplicate keys before a Python dictionary could conceal conflicting definitions. The formal core accepts explicit symbol sequences, including multi-character symbols; the initial UI uses binary character strings and rejects out-of-alphabet input.

Reachability uses traversal; minimisation uses partition refinement; canonicalisation uses fixed-alphabet BFS. Equivalence uses product BFS directly, without unnecessary prior minimisation. Accepting disagreement reconstructs a shortest distinguishing string via predecessors. `null` means no witness; `[]` means the empty-string witness. Alphabet sets must match: there is no silent completion or union policy. Reachability/minimisation of one candidate is never treated as a proof against English.

The verifier issues a sealed, serialised candidate/reference pair only for exact equivalence. The renderer accepts that object, rechecks it and generates the trace before starting the fixed scene. Parse-tree evidence likewise rechecks productions and yield. The renderer cannot accept an arbitrary candidate dictionary.

## Metrics

Evaluation writes per-example `results.csv`, category `summary.json`, readable `report.md`, notation `fertility.json` and run `metadata.json`. Training writes component losses, training time, trainable counts, and CUDA peak allocated memory if supported. CPU/MPS peak-memory measurements are explicitly unavailable rather than guessed. Rendering latency is null unless `--render` is requested; cache hits report zero rendering work.

| Metric | Definition |
|---|---|
| Raw / first-candidate equivalence | Exact language equivalence of first prediction to independent ground truth; unsupported counts as incorrect |
| Within-budget success | At least one of the bounded candidates passes exact equivalence |
| Structural validity | First candidate has a complete, well-formed DFA |
| Canonical exact match | Minimal language-canonical dictionary equality |
| Transition-table exact match | Reachable BFS graph table, **without minimisation**, including state count, destinations and accepting roles |
| Rule coverage | Fraction of requests supported by the restricted baseline |
| Release coverage | Fraction with a VERIFIED candidate |
| Released correctness | Equivalence among released candidates; null if none released |
| Incorrect candidates released | Absolute count of released inequivalent candidates |
| Fertility | Non-special tokenizer tokens / whitespace-delimited input units, identical input text for comparisons |

Fertility's denominator is an operational text measure, not a linguistic word count. Notation tables report the mean of per-example ratios, separately for plain English, mixed notation and notation-heavy structural text; empty strata are “not measured”. Lower fertility does not establish higher accuracy. Metrics are per example, not balanced by language; unique-language counts accompany them.

The gate uses the same independently generated ground truth as the evaluator. Consequently, accepted-output correctness is an expected property of a correct checker, **not an independent model achievement**. Mutation tests complement accepting states (provably changing ε membership); arbitrary transition mutations are not assumed negative without checking language change.

Ablations configure seeds 13, 42 and 123. Aggregate mean and sample standard deviation include completed runs only; standard deviation is null for fewer than two runs. DistilBERT is separately labelled and excluded from BERT-only ablation tables.

## Execution status

| Experiment | State |
|---|---|
| Tiny random-BERT forward/backward/checkpoint smoke | Executed; mechanics only |
| Limited rule-based baseline on shipped test set | Executed; measured report in artifacts |
| Vanilla pretrained BERT training/evaluation | Not run |
| Adapted pretrained BERT training/evaluation | Not run |
| Three initialisations × three seeds | Not run |
| DistilBERT research training | Not run |
| Paid/prompted LLM baseline | Disabled; not run |

No accuracy target is used as a hardcoded output. ≥70% equivalence remains a research objective.
