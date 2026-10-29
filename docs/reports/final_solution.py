"""Final solution framing for the research manuscript and complete project report."""
from report_content import ieee_pages as material_ieee, long_pages as material_long, H,S,C,T,read,pct,link

PROBLEM='The inability of NLP systems to reliably support the translation and understanding of formal-language objects and their behaviour.'

def ieee_pages():
 p=material_ieee()
 p[0][0][0]='<b>Abstract</b> - Natural-language interfaces can produce plausible formal-language answers without establishing that the generated objects represent the requested language or that their visualizations explain the current input. TheoryBERT addresses this translation and understanding gap through a BERT-centered web system for theory of computation and compiler education. A shared contextual encoder supports a typed regular-language plan decoder with learned literal copying and a separate grammar-production decoder. Exact automata construction, reference equivalence checking, production-level derivation checks and arithmetic AST/IR validation connect the learned interpretation to executable formal objects. Interactive views expose the actual machine, grammar, derivation and input-specific behaviour with explicit evidence status. The final DFA model attains 95.32% first-candidate equivalence on 641 generated test requests and 71.67% on 120 frozen fresh-language requests. Grammar and compiler evaluations use task-specific criteria. The approach integrates language interpretation, formal execution and educational representation while retaining explicit limits on English understanding and supported language classes.'
 p[0][0][4]='<b>Central problem statement:</b> '+PROBLEM+' In this work, the statement identifies a reliability gap in an integrated educational setting. It does not imply that prior NLP research has never translated language into programs or regular expressions. The unresolved need is to connect an informal requirement to an appropriate formal object, execute that object correctly and explain its behaviour through an inspectable representation.'
 p[0][0][5]='A learner may describe binary words ending in 0101, yet the required answer is an infinite language represented by finite memory. Understanding that answer requires more than a graph: the learner needs the meaning of each remembered suffix, a total transition function, accepting conditions and a trace for the supplied word. Similarly, a grammar must expose recursive productions and their derivations, while compiler exercises must connect accepted expressions with syntax trees and symbolic instructions.'
 p[0][0][6]='TheoryBERT treats these requirements as one translation-and-understanding task. DFA, CFG and compiler workspaces are related views over model-produced formal structure. BERT interprets the description; explicit mathematical components give that interpretation executable meaning and make its consequences visible.'
 p[0][1][0]='The gap becomes visible when an interface presents a generic diagram for unrelated requirements or labels a plausible candidate as correct without semantic evidence. Mathematical representation must follow the language specification. Execution must follow the particular input. A DFA should keep the same state graph when only its test word changes, while its path and acceptance result change. A context-free derivation tree may grow for a longer input even though its grammar stays fixed.'
 p[1][0][1]='The proposed solution uses BERT as the language-understanding basis and introduces task-specific formal targets. For regular languages, the encoder supplies contextual token features to a compact typed plan decoder. A plan such as ENDS(0101) expresses the intended condition explicitly; learned span pointers preserve the literal. An exact compiler constructs a DFA from the predicted plan. The system also implements a direct structured DFA head as an alternative model interface, with the same downstream contract.'
 p[1][0][3]='The objectives are reliable formal translation within a declared scope, transparent execution of the resulting objects and a visualization whose mathematical content matches the current request. Resource-conscious training and shared encoder reuse support practical operation. Accuracy, formal validity, response latency and adaptation cost remain separate measures because none can stand in for the others.'
 p[1][0][5]='The complete system makes formal-language objects inspectable through an English requirement, a model-produced specification, an executable object and evidence-backed behaviour. Versioned corpora, canonical-language splits and checkpoint fingerprints connect the implementation to reproducible evaluation. The purpose of this methodology is to assess the final solution and its limits rather than present a sequence of development changes.'
 p[1][0][10]='Translation, formal execution and representation are consequently three obligations of the same underlying problem. A failure at any boundary can mislead the learner: an incorrect interpretation yields the wrong language, an incorrect simulator yields the wrong behaviour, and a stale visualization conceals both. The architecture exposes these boundaries without treating DFA, grammar and compiler support as unrelated problem statements.'
 p[1][0][12]='Section II reviews related work and identifies the translation-and-understanding gap. Section III describes the component architecture and algorithms. Section IV states the key contributions. Section V documents datasets and provenance. Section VI evaluates the final system. Section VII presents the web interface, visualization and resource design. Section VIII discusses limitations and future work, and Section IX concludes the paper.'
 p[1][1][3]=p[1][1][3].replace('The new plan experiment freezes that evaluated encoder.','The semantic-plan model uses that evaluated encoder with frozen weights.')
 p[1][1][4]='These adaptation studies inform the choice to retain pretrained language representations while learning explicit formal targets. Vocabulary adaptation can improve domain representation, but it does not itself define a correct automaton or derivation. The present solution therefore combines contextual encoding with typed semantic output and independent formal checks. The role of NLP is interpretation; the role of the formal component is precise execution of the interpretation.'
 p[2][1][5]='The research gap is the absence of a sufficiently reliable, inspectable connection between NLP interpretation and the representation of formal-language behaviour in one educational workflow. Existing semantic parsers demonstrate translation, while automata and compiler tools demonstrate formal execution. TheoryBERT connects those capabilities through typed contracts, task-specific verification and a shared interface that explains the current formal object and input.'
 p[2][1][6]=p[2][1][6].replace('Its new wording comparison tests that complete local approach','Its frozen wording evaluation tests the complete approach')
 p[3][0][6]=S('B. Structured DFA Interface')
 p[3][0][7]='The implemented direct interface predicts a state count, accepting-state bits and binary transition destinations from a pooled BERT representation. It supports up to eight states and constrains destinations to the active range. The semantic-plan interface supplies larger supported constructions without requiring the network to predict every transition independently. Both interfaces emit the same complete DFA JSON contract, allowing the formal checker, simulator and renderer to operate independently of model architecture.'
 p[3][1][1]=p[3][1][1].replace('The new head','The semantic-plan head')
 p[3][1][3]='Training minimizes output-token cross-entropy plus weighted start/end pointer cross-entropies at copy positions. Padding is excluded. The encoder is immutable and fingerprinted for head compatibility. A packed real-token feature cache supports bounded-memory adaptation. Canonical-language groups separate training, validation and testing. Validation selects the checkpoint; final test partitions are excluded from gradient updates and selection.'
 p[4][0][1]='<b>1) BERT-centered formal translation.</b> A shared contextual encoder supports typed regular-language plans, learned literal copying and grammar-production decoding. Operator selection and argument interpretation come from BERT features. Formal constructors execute model-produced specifications instead of independently recognizing English phrases.'
 p[4][0][2]='<b>2) Understanding through executable representation.</b> A common web interface connects the predicted language to states, transitions, input traces, production derivations and arithmetic AST/IR. The displayed structure is generated from the actual formal object, and execution highlights are derived from the current input.'
 p[4][0][3]='<b>3) Explicit correctness boundaries.</b> Structural validation, reference DFA equivalence, derivation validity and compiler consistency are represented as distinct claims. Unreferenced English predictions remain inspectable candidates. Sealed evidence gates video export and prevents a polished visualization from implying unsupported semantic certainty.'
 p[4][0][4]='<b>4) Reproducible end-to-end implementation.</b> Versioned datasets, canonical-language partitions, pinned source revisions, shared encoder loading and resource guards support a complete deployable system. Model evaluation and application integration checks assess the solution at their respective boundaries.'
 p[4][1][4]=p[4][1][4].replace('A retired challenge development subset contributes supervision only when its canonical language belongs to training.','Supplementary challenge descriptions contribute supervision only when their canonical language belongs to training.')
 p[4][1][5]='The challenge assets cover DFA, CFG and compiler requests with different wording and boundary conditions. The 165-case mixed suite supplies regression coverage across all three workspaces. The frozen 254-case plan suite contains 134 validation and 120 test languages outside plan training. A 57-case test subset also satisfies the direct interface bounds of eight states and 64 input tokens. These assets are not independent corpora to be added to training counts.'
 p[4][1][6]='The companion report lists every corpus, its role, counts, hashes, generation code and source links. The dataset provenance archive distributes the permitted local supervision and manifests. The encoder and task heads are published separately as a versioned inference bundle. Generated data is identified as generated; inherited pretraining sources are distinguished from data actually used in local adaptation.'
 p[5][0][:]=[
 H('VI. EVALUATION OF THE FINAL SOLUTION'),S('A. Evaluation Questions and Metrics'),
 'The evaluation asks whether the system translates descriptions into the intended supported formal objects, whether formal execution is correct and whether the interface presents the resulting behaviour faithfully. These questions correspond to one integrated problem but require different evidence. A first-candidate DFA is scored by exact equivalence to an independent reference. Invalid and unsupported outputs count as incorrect. Within-five success reports reference-assisted candidate selection separately.',
 'A formal checker cannot establish the intended meaning of arbitrary English by inspecting a prediction alone. The independent DFA reference supplies a semantic target for measured automata tasks. Without it, structural validation and simulation remain useful but narrower claims. Grammar evaluation records canonical production exactness and checked derivations. Compiler fixtures check both valid-expression lowering and correct rejection of invalid expressions.',
 'Canonical DFA identities group equivalent languages before splitting. The final plan corpus has 2,914 distinct identities. Frozen fresh-language test requests are outside training and do not determine checkpoint selection. Previously inspected mixed cases are reported as regression evidence. Dataset versions overlap, and results from different partitions are not pooled into a single general accuracy claim.',
 S('B. Final DFA and Grammar Results'),
 'The final plan decoder produces 611/641 first-candidate equivalent DFAs on the generated regression test, giving 95.32% exact equivalence. On the 120-case frozen fresh-language test it produces 86 correct first candidates, giving 71.67%. The 57-case capacity-matched subset yields 38/57, or 66.67%. These values measure supported semantic translation and show a meaningful remaining gap between generated and fresh wording.',
 'The grammar decoder produces 130/130 exact canonical production outputs on its generated test set. The inspected mixed grammar suite yields 10/14 successful cases, and the compiler fixture subset yields 9/9 expected outcomes, including negative cases. The small mixed subsets do not establish unrestricted CFG or compiler accuracy. Production exactness and grammar-language equivalence are distinct.'
 ]
 p[5][1][:]=[
 S('C. Final System Measurements'),
 T(['Evaluation asset','Measure','Result'],[
 ['Generated DFA test','First equivalence','611/641; 95.32%'],['Fresh DFA test','First equivalence','86/120; 71.67%'],['Matched fresh subset','First equivalence','38/57; 66.67%'],['Fresh DFA test','Within five','119/120; 99.17%'],['Generated grammar','Production exactness','130/130'],['Mixed CFG fixtures','Expected result','10/14'],['Compiler fixtures','Expected result','9/9']]),
 C('TABLE II. Final task-specific evaluation. Reference-assisted search is not unaided model accuracy.'),
 'The semantic head contains 537,385 trainable parameters over a shared frozen BERT encoder. Its recorded adaptation run takes 230.8 seconds including feature extraction and head training. The encoder still executes at inference, and typed search and automata construction add work. These resource measurements describe the implementation; they are not the central research contribution or a substitute for correctness.',
 'The frozen fresh test reveals uneven language coverage. Exact-word requests yield 23/23 correct first candidates, substring requests 21/21 and prefix requests 20/22, while suffix requests yield only 1/18 under that wording distribution. Aggregate scores therefore cannot justify a claim that every supported operator is reliably understood. Failure analysis remains part of the final solution assessment.',
 'Integration verification exercises the real HTTP job boundary, changed input traces, grammar generation, rejected expressions and MP4 export. The completed suite contains 105 passing tests, and the React production build succeeds locally and in GitHub Actions. Browser checks assess dynamic graph content and responsive layout separately from model scores. A working endpoint or attractive diagram is not semantic evaluation.',
 'The results support a bounded NLP-to-formal workflow with inspectable execution. They also show why exact verification and honest preview labels remain necessary. A derivation proves membership under the displayed grammar, and an equivalent DFA proves agreement with its reference. Neither claim automatically proves that an arbitrary English requirement has been interpreted correctly.'
 ]
 p[6][1][0]=S('C. Input-Dependent Representation')
 p[6][1][1]='The visualization consumes server-produced DFA or tree objects through a common representation contract. Node count, transitions, accepting roles, state visits and highlighted execution come from the current result. Diagram styling and playback controls are reusable presentation components. Mathematical content is regenerated from the object rather than selected from a catalogue of display templates.'
 p[6][1][5]='The training workflow bounds caches, thread count and simultaneous heavy jobs. Frozen encoder features are stored in a packed form and removed after adaptation. Inference heads share compatible encoder weights. CPU memory-mapped loading retains the evaluated FP32 tensors without quantization, reducing anonymous loading copies while preserving model precision.'
 p[6][1][6]='The deployment image builds React and installs CPU inference, Cairo/Pango and ffmpeg. A versioned GitHub Release supplies a SHA-256-pinned model bundle at build time. Startup requires both active checkpoints; the health endpoint exposes model readiness and deployed commit. This defines the deployment architecture. A cloud memory-limit check separately determines whether a particular hosting tier can support the full runtime.'
 p[6][1][7]='Pinned source revisions, dataset hashes, encoder fingerprints and per-case evaluation files make the system reproducible. Resource limits support safe local operation, while the public web interface supplies the formal-language workflow. Training efficiency and server capacity remain operational properties; the primary claim concerns translation and understanding of formal objects and their behaviour.'
 p[7][0][2]='Evaluation uses generated descriptions and one training seed. Canonical grouping reduces formal-target leakage, but shared operator families and template structure limit extrapolation to unrestricted language. The fresh test has 120 cases, with 57 in the matched subset. A human-authored study, several seeds and calibrated unsupported-intent detection are needed before broader reliability claims.'
 p[7][0][6]='TheoryBERT addresses the NLP-to-formal translation and understanding gap through a BERT-centered, executable and inspectable workflow. Typed plans and grammar productions connect natural-language interpretation to exact automata, checked derivations and arithmetic representations. The web system exposes their behaviour through current-object visualization and input-specific execution. Final evaluation demonstrates useful bounded capability while preserving explicit limits on English understanding and formal guarantees.'
 return p


def long_pages():
 pages=material_long()
 pages[0]=('TheoryBERT: Final Technical Solution Report',[
 ('space',15),('lead','BERT-centered translation and understanding of formal-language objects and their behaviour'),S('Central Problem Statement'),PROBLEM,
 'TheoryBERT addresses this single problem through one integrated system. Natural-language requirements are interpreted by BERT, translated into formal specifications and executed by explicit mathematical components. DFA, grammar and compiler support are complementary parts of the solution. The web interface makes their structures, execution and verification evidence inspectable.',
 S('Complete Solution Scope'),
 'The implementation includes a pretrained contextual encoder; a typed semantic-plan decoder with learned literal copying; a structured direct-DFA interface; a grammar-production decoder; exact automata construction, minimization and equivalence; bounded Earley parsing and derivation checking; arithmetic lexing, AST construction and symbolic intermediate code; interactive SVG visualizations; checked Manim export; asynchronous API jobs; model and result caching; versioned datasets; evaluation tools; and deployment packaging.',
 S('Final Evaluation'),
 'The deployed-model candidate attains 611/641 first-candidate DFA equivalence on the generated test and 86/120 on the frozen fresh-language test. Generated grammar production exactness is 130/130. Mixed CFG fixtures yield 10/14 expected results, and compiler fixtures yield 9/9 including correct rejection. These are separate task-specific measurements. They do not constitute universal English understanding.',
 S('Purpose of This Report'),
 'This report presents the final technical solution, architecture, algorithms, data, website, implementation and evaluation. It accompanies the eight-page IEEE-style research manuscript. Dataset variants are documented for provenance and reproduction; model-development chronology and before-and-after efficiency comparisons are not the organizing argument.'
 ])
 pages[2]=('Problem Definition and Solution Requirements',[
 S('One Underlying Problem'),PROBLEM,
 'The problem concerns the complete connection from an informal requirement to the meaning and behaviour of a formal object. NLP may generate a plausible structure, but a learner must also understand what the structure accepts, how its transitions or productions operate and what evidence supports the answer. A language model response alone does not supply that connection.',
 'For a DFA, the language description determines finite memory, transitions and accepting states. A test word determines only one execution through the machine. For a CFG, the grammar determines possible derivations, while the current token sequence determines the returned parse trees. For arithmetic compilation, the accepted expression determines the AST and symbolic instructions under an explicit precedence grammar. These are different formal manifestations of the same translation-and-understanding problem.',
 S('Required Capabilities'),
 T(['Capability','Acceptance criterion'],[['Language interpretation','English requests invoke the trained BERT encoder and the relevant learned head.'],['Formal translation','Predicted plans or productions produce an explicit inspectable object.'],['Behaviour','Simulation, derivation and compiler output follow that object and the current input.'],['Representation','Graph and tree content is computed from current formal data.'],['Correctness evidence','Each claim states its checker, reference and scope.'],['Complete product','A web workflow connects models, formal tools, visualizations and deployment.']]),
 S('Design Objective'),
 'The proposed system connects interpretation with deterministic formal semantics and evidence-aware explanation. Formal algorithms execute predicted meaning; they do not replace BERT with handwritten English rules. The result is an integrated educational tool with measurable translation quality and checkable execution, rather than a conversational answer detached from a formal object.',
 'The scope is bounded binary regular languages, supported context-free productions and symbolic arithmetic. General English ambiguity, unrestricted CFG equivalence and industrial compiler functionality remain outside the established guarantees. The report keeps these limitations visible while describing every implemented component.'
 ])
 pages[4]=('Research Positioning and Key Contributions',[
 S('BERT as the Interpretation Basis'),
 'BERT processes the English requirement and supplies contextual representations to the formal-output heads. The plan head learns operators, numeric arguments, composition and literal-copy locations. The grammar head learns production tokens. A separate structured DFA interface supports direct transition prediction. No hidden phrase matcher constructs replacement answers in the learned path.',
 S('Executable Semantics as the Bridge'),
 'A model-produced ENDS(0101) plan has a defined meaning that the automata compiler can execute exactly. A model-produced conjunction composes two formal languages through reachable product construction. If the interpretation is wrong, the exact compiler still constructs the wrong intended language. This is why semantic reference checks and honest candidate labels are necessary alongside structural validity.',
 S('Contribution 1: Integrated Formal Translation'),
 'The system connects contextual language analysis with typed regular-language plans and grammar productions. Learned span copying preserves literal identity and leading zeros. Shared encoder loading supports multiple tasks without requiring a separate English interpreter in every workspace.',
 S('Contribution 2: Behavioural Understanding'),
 'The interface displays actual machine states and transitions, current input traces, grammar derivations, arithmetic syntax trees and symbolic code. It connects abstract objects with concrete behaviour while preserving the distinction between a language graph and one execution specimen.',
 S('Contribution 3: Checkable Claims'),
 'Independent DFA equivalence, derivation checks, AST/IR consistency and sealed export evidence make correctness claims inspectable. The application distinguishes semantic equivalence, structural validity and valid execution under a predicted grammar.',
 S('Contribution 4: Complete Reproducible System'),
 'The implementation includes versioned supervision, canonical-language partitioning, public source attribution, model fingerprints, guarded adaptation, API jobs, caching, responsive workspaces and a hash-checked deployment bundle. The contribution is their integrated solution to the stated problem. Individual neural and formal techniques build on prior work.'
 ])
 # Preserve the complete model implementation as an architectural alternative,
 # without presenting a chronological model-upgrade narrative.
 pages[6]=('Structured DFA Prediction Interface',[
 S('Representation and Implemented Heads'),
 'The structured DFA interface predicts a machine directly from a pooled BERT representation. Separate heads predict active state count, accepting-state bits and transition destinations for each supported state and binary symbol. The maximum state count is eight. Training masks inactive positions and inference constrains destination indices to the active range.',
 S('Formal Output Contract'),
 'The predicted object contains a declared state set, alphabet, start state, accepting set and total transition map. Structural validation rejects undeclared destinations, missing symbols, duplicate states and invalid accepting roles. Canonicalization removes unreachable structure and minimizes the machine for semantic identity and comparison.',
 S('Bounded Candidate Search'),
 'The first candidate takes the highest-ranked neural decisions. Bounded alternatives explore uncertain count, accepting-bit and transition choices through score-gap search and deduplicate completed machines. References do not generate candidates. When a reference is supplied, exact equivalence identifies a matching candidate; without one, the first candidate remains an explicitly unverified preview.',
 S('Relationship to the Semantic-Plan Model'),
 'The final default regular-language route predicts typed plans and then constructs machines. The direct interface remains implemented for explicit selection, controlled research and compatibility with the same DFA contract. Both use BERT for language interpretation and both connect to the same verifier, simulator and visualization. This is an architectural choice between output representations, not a separate user problem.',
 'Direct prediction can describe small arbitrary transition tables but couples many output decisions. Typed plans express supported families compositionally and expose literal arguments. Neither representation guarantees correct English interpretation. The downstream checker establishes only the claim permitted by available evidence.',
 S('Encoder and Adaptation'),
 'The shared evaluated encoder starts from google-bert/bert-base-uncased. Its domain extension supplies additional token embeddings and a residual contextual module; the recorded encoder adaptation updates the top two BERT blocks while preserving protected lower weights. The semantic-plan and grammar heads bind to this exact checkpoint through fingerprints.',
 'A supported task head must load a compatible encoder. Changing the backbone without retraining and evaluation invalidates that compatibility. Checkpoint dispatch preserves these boundaries while keeping model selection independent of the final visual representation.'
 ])
 pages[14]=('Training Design and Resource Management',[
 S('Supervised Adaptation'),
 'The final semantic head learns typed prefix tokens and literal span pointers from language-plan pairs. Its objective combines token cross-entropy with weighted start and end pointer losses at copy positions. The head contains 537,385 trainable parameters. BERT token features are frozen during this adaptation, and the trained head records the exact encoder fingerprint.',
 S('Data Separation'),
 'Equivalent DFA languages are canonicalized and grouped before partitioning. Protected split assignments keep one canonical language in one partition. Validation selects the checkpoint; test inputs do not enter the feature cache, gradient updates or checkpoint-selection metric. Grammar supervision is grouped by canonical production identity under its declared normalization.',
 S('Bounded Feature Storage'),
 'Feature extraction stores only real tokens in a packed disk-backed float16 cache. Small batches are padded on demand. This representation limits cache storage and avoids a dense array sized by maximum token length. The cache is deleted after completed adaptation. Final inference still uses the original evaluated FP32 encoder and head tensors.',
 S('Local System Controls'),
 'The training launcher runs one heavy job at a time with two CPU threads and reduced scheduling priority. Resource guards record available disk, available memory and swap. The configured stopping conditions preserve 3 GiB free disk, an 8% available-memory floor and a 0.75 GiB allowance for swap growth. These controls reduce resource pressure but cannot prevent unrelated operating-system changes.',
 S('Shared Inference and Storage'),
 'DFA and grammar heads share one compatible immutable encoder in the web process. Small task checkpoints store their heads and configuration without duplicating the backbone. Model weights remain outside Git history and are distributed as a versioned release asset. CPU memory-mapped loading uses meta initialization and assigned file-backed tensors, preserving FP32 values without quantization.',
 S('Measurement Interpretation'),
 'The recorded semantic-head adaptation takes 230.8 seconds including feature extraction. Trainable parameter count, optimizer-state cost, inference latency and translation quality describe different properties. They are documented for reproducibility and operational planning. The research problem remains formal translation and understanding, rather than an efficiency-improvement narrative.'
 ])
 pages[15]=('Evaluation Methodology',[
 S('Questions Evaluated'),
 'The final system is evaluated for translation accuracy, faithful formal execution and faithful presentation. Translation asks whether a predicted object denotes the intended supported language. Execution asks whether traces, derivations and symbolic code follow the object. Presentation asks whether the web view corresponds to the current object and input. These checks assess three boundaries of the same central problem.',
 S('Automata Metrics'),
 'First-candidate exact equivalence is the primary DFA translation metric. A complete product exploration compares the candidate with an independent reference and returns a shortest distinguishing word on disagreement. Unsupported or invalid predictions count as incorrect. Within-five success reports whether a correct candidate exists among a bounded set and requires a reference for selection.',
 S('Grammar and Compiler Metrics'),
 'Generated grammar tests use canonical production exactness. Runtime derivations are independently checked against the displayed productions and terminal yield. Compiler fixtures test expected acceptance or rejection and consistency between a checked parse, AST and symbolic IR. These measurements cannot be collapsed into a single product-wide accuracy percentage.',
 S('Partitions and Scope'),
 'The plan corpus contains 11,415 examples and 2,914 canonical languages. The frozen wording suite has 134 validation and 120 test cases outside training. The generated DFA regression test has 641 cases. A 57-case fresh subset obeys the direct structured interface bounds. Mixed CFG and compiler fixtures are inspected regression evidence and are labelled accordingly.',
 S('Separation of Selection and Reporting'),
 'Checkpoint selection uses validation and known product fixtures. Test outcomes are reported after selection. Tests that have influenced model design are not described as untouched future evidence. Per-case records preserve source descriptions, targets, state counts, candidate outcomes, errors and timing.',
 S('Application Validation'),
 'Unit tests assess formal algorithms and model contracts. HTTP tests exercise real job submission, provenance, changed inputs, invalid requests and video gates. Browser tests compare visible graph/tree content with server results and check responsive layouts. The deployment workflow separately builds the full inference image and exercises it under a declared memory limit.'
 ])
 pages[16]=('Final Translation and Formal-Execution Results',[
 S('DFA Translation'),
 T(['Test asset','First correct','First equivalence','Within five'],[['Generated DFA regression','611/641','95.32%','97.66%'],['Frozen fresh languages','86/120','71.67%','99.17%'],['Capacity-matched fresh subset','38/57','66.67%','100%']]),
 'These are final-model measurements, each tied to a particular evaluation asset. The generated test is useful for established supported families; the fresh suite probes wording outside training languages. The gap between these results makes unrestricted-language claims inappropriate.',
 S('Grammar Translation'),
 'The generated grammar test contains 130 examples with 130 exact canonical production outputs. The mixed CFG fixture subset yields 10 successful expected outcomes out of 14. These values evaluate different distributions and evidence types. A production-exact score does not prove equivalence between arbitrary grammars or general understanding of English specifications.',
 S('Compiler Outcomes'),
 'The compiler fixture subset yields 9 expected outcomes out of 9, counting valid-expression processing and correct rejection. The arithmetic implementation supports identifiers, numbers, parentheses, unary signs and the standard additive and multiplicative operators. It is a symbolic educational compiler path, not a complete industrial compiler.',
 S('Formal Evidence'),
 'DFA equivalence is an exact claim about candidate and reference languages. A checked derivation establishes that the displayed grammar derives the selected token sequence. AST and IR consistency establishes that the symbolic lowering preserves the parsed expression under the implemented arithmetic contract. The claims differ and remain labelled separately in the interface.',
 S('Interpretation'),
 'The evaluation supports a useful bounded language-to-formal solution with inspectable execution. It does not justify guaranteed correctness for arbitrary descriptions. Where an independent reference is absent, the candidate preview helps the user inspect the interpretation, but remains distinct from a proved translation.'
 ])
 pages[17]=('Coverage Analysis and System Verification',[
 S('Operator Coverage'),
 T(['Fresh-test family','First correct','Interpretation'],[['Exact word','23/23','Literal identity and whole-word condition.'],['Contains pattern','21/21','Contiguous substring condition.'],['Starts with pattern','20/22','Prefix interpretation.'],['Ends with pattern','1/18','Substantial wording weakness remains.']]),
 'The suffix result is a material limitation of the final model under the frozen fresh wording. A supported operator in the formal compiler is not a guarantee that its English description is recognized reliably. The report retains this finding because an aggregate score can obscure the behaviour most relevant to a particular user request.',
 S('Software Verification'),
 'The final unit suite contains 105 passing tests and the React production build succeeds. The same software checks pass in GitHub Actions. Model-loader tests compare every tensor and output between copied and memory-mapped loading. Installer tests cover exact bytes, archive corruption, unsafe paths, unlisted members and symlink escapes.',
 S('End-to-End Behaviour'),
 'The local deployment check exercises seven cases: BERT suffix translation against an independent five-state reference; rejection after changing the input; an unreferenced preview without false equivalence; BERT grammar generation and checked parsing; BERT arithmetic grammar and AST; invalid expression rejection; and real MP4 export from verified evidence.',
 S('Visualization Fidelity'),
 'The visible graph follows the formal state set, complete transitions, start state and accepting set. Input traces determine highlights and acceptance. Grammar derivations and compiler syntax trees come from checked structures. Presentation components are reused across model interfaces, so the display does not become a substitute language interpreter.',
 S('Limits of the Evidence'),
 'Passing software tests confirms implemented contracts on exercised cases. It does not raise the semantic score of a model or establish user learning outcomes. A cloud container check establishes behaviour under its measured memory budget. It does not by itself prove internet-scale reliability or indefinite availability.'
 ])
 pages[26]=('Integrated Contributions and Research Scope',[
 S('A Single Research Argument'),PROBLEM,
 'TheoryBERT responds with a BERT-centered translation layer, formal execution layer and interactive understanding layer. DFA, CFG and arithmetic compiler workspaces share that argument. The solution covers language interpretation, mathematical object construction, execution, evidence and presentation in one coherent application.',
 S('Complete Implemented Contribution'),
 'The neural layer provides contextual representations, learned plans, literal copying, direct structured automata and grammar-production decoding. The formal layer supplies construction, minimization, equivalence, simulation, bounded chart parsing, derivation checks, AST construction and symbolic IR. The application layer supplies asynchronous jobs, evidence ownership, caching, responsive studios, research information and reusable dynamic visualization.',
 'The data and operational layer supplies source-pinned preprocessing, generated supervision, canonical-language partitions, challenge assets, manifests, training controls, checkpoint fingerprints, model packaging and a container deployment path. The companion dataset archive and public model release provide distinct distribution units for data and inference artifacts.',
 S('Project Uniqueness'),
 'The distinguishing feature is the integrated contract between learned language interpretation and checkable formal behaviour. The system does not stop at a fluent textual answer or a static graph. It exposes what BERT predicted, how the formal object behaves and which claim the evidence actually supports. This is an integration contribution grounded in established neural and formal methods.',
 S('Research Boundaries and Extension'),
 'Independent human-authored descriptions, several random seeds, calibrated abstention and educational user studies are needed to establish broader reliability and learning benefits. Richer alphabets, statement languages and other grammar classes require additional supervision and new formal contracts. Their absence does not change the central research problem, but limits the current implementation scope.',
 S('Paper Organization'),
 'The IEEE manuscript contains introduction, literature review, proposed solution architecture, key contributions, datasets, final evaluation, web and resource design, limitations and conclusion. This report expands every implemented subsystem and supplies provenance, source links, technology detail and reproducibility information.'
 ])
 # Reframe retained technical material consistently and remove development-only commentary.
 replacements={
 'New BERT Semantic-Plan Model':'BERT Semantic-Plan Translation Model',
 'DFA Corpus Lineage and Use':'DFA Supervision Assets and Dataset Roles',
 'Established Experiments and Their Limits':'Final Translation and Formal-Execution Results',
 'New Plan Comparison and Final Selection':'Coverage Analysis and System Verification',
 'The new head':'The semantic head','The new model':'The semantic-plan model',
 'the new model':'the semantic-plan model','the new experiment':'the implementation',
 'new plan head':'semantic plan head','new plan decoder':'semantic plan decoder',
 'new semantic-plan head':'semantic-plan head','new plan experiment':'semantic-plan approach',
 'new plan dataset':'semantic-plan dataset','new comparison':'frozen evaluation',
 'new work':'solution','current experiment':'evaluation',
 'The original practical concern':'The practical concern',
 'pre-experiment':'fixed presentation',
 'The new model remains imperfect on the fresh test despite large gains over V3.':'The final model remains imperfect on the fresh test.',
 'The comparison uses generated descriptions and one seed.':'The evaluation uses generated descriptions and one seed.',
 'The all-case fresh score includes 63 capacity-mismatched cases.':'The full fresh score includes 63 cases beyond the direct structured interface bounds.',
 'Repository links do not assert that current local changes or large model files have been published.':'Inference weights are distributed through the versioned model release; the source repository contains the pinned bundle manifest.',
 'Local experiment records':'Recorded evaluation assets',
 }
 def text(s):
  for a,b in replacements.items():s=s.replace(a,b)
  return s
 def walk(item):
  if isinstance(item,str):return text(item)
  if isinstance(item,tuple):return tuple(walk(x) for x in item)
  if isinstance(item,list):return [walk(x) for x in item]
  return item
 pages=[(text(title),[walk(b) for b in blocks]) for title,blocks in pages]
 # Replace obsolete operational statements and comparison-oriented paragraphs.
 for index,(title,blocks) in enumerate(pages):
  fixed=[]
  for block in blocks:
   if isinstance(block,str):
    if 'The previous direct checkpoint' in block:continue
    if 'Model weights, generated datasets and evaluation directories are local and ignored by Git.' in block:
     block='Source code, configuration, reports and dataset provenance are distributed through the GitHub project. Large FP32 inference assets are a separate GitHub Release bundle pinned by deploy/model-bundle.json. The Docker build verifies the archive and every member before installing it. Reproduction requires this exact encoder plus compatible task heads.'
    if 'The six frozen presentation files' in block:
     block='Presentation source fingerprints and browser checks protect graph and tree fidelity. Tests compare visible counts and traces with the formal result, verify that changed inputs update execution and check responsive overflow and console errors.'
    if 'The final verification record reports:' in block:
     block='The final software suite passes 105 tests, and the frontend builds locally and in GitHub Actions. The local seven-case deployment check exercises genuine BERT, formal verification, compiler rejection and real video output. These integration checks are separate from held-out model accuracy.'
    if 'The experiment also treats deployment selection' in block:continue
   fixed.append(block)
  pages[index]=(title,fixed)
 # A contents page lists the final solution structure rather than experiment history.
 pages[1]=('Contents and Evidence Conventions',[
 T(['Page','Topic'],[[str(i+1),title] for i,(title,_) in enumerate(pages)]),
 ('small','One problem connects every chapter: reliable NLP support for translation and understanding of formal-language objects and their behaviour. Measured results, implemented capability and future work are distinguished. Verified refers to the explicit formal claim checked, not unrestricted English correctness.'),
 ('small','Dataset variants overlap. Fingerprints identify exact artifacts. Corpus counts are not added as independent training data.')
 ])
 pages[25][1][1]=pages[25][1][1].replace('despite large gains over V3','under the frozen wording distribution')
 pages[18][1][:]=[b.replace('The six recorded presentation files are byte-identical to the recorded pre-experiment baseline.','The presentation components use a consistent formal-object contract.') if isinstance(b,str) else b for b in pages[18][1]]
 pages[3][1][-1]='The research question is how contextual NLP can support translation and understanding through explicit formal targets, executable semantics and inspectable behaviour. Prior work supplies the representation and parsing foundations; this system combines them in a complete educational workflow and evaluates each boundary with task-appropriate evidence.'
 pages[11][1][2]='The dataset registry covers every implemented supervision asset. The shipped sample supports mechanics and canonical splitting. English DFA v1 and expanded DFA provide semantic template supervision over 208 language identities. V3 supplies 6,275 rows over 696 identities for the shared adapted encoder. Corpus names identify reproducible input artifacts rather than stages in a claimed accuracy trajectory.'
 pages[11][1][4]='The 6,738-row robust DFA asset supplies additional wording and protected challenge groups for a separate direct-head training condition. It retains the 641-case generated regression partition. It is included for complete data provenance and reproducibility; it is not the final semantic-plan training corpus.'
 pages[11][1][5]=pages[11][1][5].replace('eligible retired-development rows','eligible supplementary challenge rows')
 pages[11][1][7]='Local generation code supplies the construction recipe. Generated JSONL files stay out of Git history. The companion dataset archive supplies corpus variants, grammar files, pinned KB13 input/license and a file/hash register. The archive is committed with the reports, while large model tensors are distributed as a separate versioned GitHub Release.'
 pages[12][1][4]='Mixed challenge v1 contains 100 DFA, 38 CFG and 27 compiler requests. Its reserved subset contains 23 DFA, 14 CFG and nine compiler cases. It covers wording interpretation, formal structure, unsupported bounds and downstream visualization. Because it is inspected and eligible development cases inform supervision, its outcomes are regression evidence rather than an untouched independent test.'
 pages[13][1][2]='A single role-resolution function assigns each canonical language to its protected partition across generated and supplementary descriptions. Build assertions reject conflicting identities before writing a corpus. Tests verify that the frozen evaluation languages do not occur in plan training. These controls make split integrity an executable requirement.'
 pages[13][1][7]='Internal validation selects the head using plan-and-copy exactness, with loss as a tie-break. Decoded validation and known product fixtures check application compatibility. Reserved test outcomes are recorded after selection and are excluded from retraining and checkpoint selection in the reported evaluation.'
 pages[19][1][4]='The deployment image builds React and installs the CPU inference and rendering runtime. A versioned GitHub Release distributes the original FP32 encoder and compatible heads. The installer verifies archive and member hashes against deploy/model-bundle.json. Startup loads both evaluated active checkpoints and fails if either is unavailable. The health response reports model readiness and the Render source commit. A constrained cloud container test separately checks the hosting memory budget.'
 pages[22][1][8]='The final visualization uses stable reusable geometry and presentation components. Browser and HTTP checks verify current graph counts, changing trace acceptance, grammar tree growth and compiler behaviour against formal results. This protects representation fidelity without treating visual appearance as a proof of language interpretation.'
 pages[24][1][8]=S('Model Compatibility')
 pages[24][1].insert(9,'The active pointer selects the BERT semantic-plan decoder. Its head and the grammar head require the exact fingerprinted V3 encoder. Explicit checkpoint selection must retain compatible configuration and source evidence. A changed encoder requires matching adaptation and evaluation rather than silent substitution.')
 return pages
