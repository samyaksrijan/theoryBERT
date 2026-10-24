import { useEffect, useId, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  GitBranch,
  Layers3,
  Menu,
  Network,
  Pause,
  Play,
  Search,
  Settings2,
  X,
} from "lucide-react";
import Diagram from "./components/Diagram";
import { Wordmark } from "./components/Brand";

const features = [
  "Explore real automata and context-free grammars",
  "Follow each transition and watch a derivation unfold",
  "Check the mathematics before the animation",
];

/* These are worked illustrations, not predictions. The suffix machine and
   expression tree use the same languages as the shipped reference examples. */
function StateIllustration({ step = 0, dark = false }) {
  const id = useId().replaceAll(":", "");
  const active = [0, 0, 0, 1, 2][step];
  const nodes = [
    [74, 143],
    [218, 70],
    [218, 213],
  ];
  const color = dark ? "#e7dfff" : "#443369";
  return (
    <svg
      viewBox="0 0 310 285"
      role="img"
      aria-label="Reference automaton for binary strings ending in 01; double ring marks accepting state q2"
    >
      <defs>
        <marker
          id={id}
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M0 0L10 5L0 10z" fill={color} />
        </marker>
      </defs>
      <g fill="none" stroke={color} strokeWidth="1.6" markerEnd={`url(#${id})`}>
        <path d="M16 143H46" />
        <path d="M93 122Q137 73 191 70" />
        <path d="M218 98V184" />
        <path d="M194 200Q119 209 89 168" />
        <path d="M237 188Q280 140 237 94" />
        <path d="M48 130C-2 81 94 63 78 115" />
        <path d="M204 45C171 -7 270 0 237 52" />
      </g>
      <g
        fill={color}
        fontFamily="IBM Plex Mono, monospace"
        fontSize="15"
        textAnchor="middle"
      >
        <text x="139" y="83">
          0
        </text>
        <text x="207" y="148">
          1
        </text>
        <text x="136" y="209">
          1
        </text>
        <text x="267" y="149">
          0
        </text>
        <text x="37" y="85">
          1
        </text>
        <text x="224" y="16">
          0
        </text>
      </g>
      {nodes.map(([x, y], i) => (
        <g key={i}>
          <circle
            cx={x}
            cy={y}
            r="27"
            fill={active === i ? "#7256d9" : dark ? "#504095" : "#fcf9f2"}
            stroke={color}
            strokeWidth="1.6"
          />
          {i === 2 && (
            <circle
              cx={x}
              cy={y}
              r="22"
              fill="none"
              stroke={active === i ? "white" : color}
              strokeWidth="1.2"
            />
          )}
          <text
            x={x}
            y={y + 6}
            fill={active === i ? "white" : color}
            textAnchor="middle"
            fontFamily="IBM Plex Mono, monospace"
            fontSize="18"
          >
            q{i}
          </text>
        </g>
      ))}
    </svg>
  );
}

function TreeIllustration({ kind = "ambiguous" }) {
  const nodes =
    kind === "arithmetic"
      ? [
          ["E", 160, 22],
          ["E", 60, 69],
          ["+", 160, 69],
          ["T", 255, 69],
          ["T", 60, 116],
          ["T", 205, 116],
          ["*", 255, 116],
          ["F", 310, 116],
          ["F", 60, 163],
          ["F", 205, 163],
          ["id", 310, 163],
          ["id", 60, 210],
          ["id", 205, 210],
        ]
      : kind === "ambiguous"
        ? [
            ["E", 180, 27],
            ["E", 83, 92],
            ["+", 180, 92],
            ["E", 277, 92],
            ["id", 83, 160],
            ["E", 227, 160],
            ["+", 277, 160],
            ["E", 327, 160],
            ["id", 227, 223],
            ["id", 327, 223],
          ]
        : [
            ["S", 180, 27],
            ["a", 70, 92],
            ["S", 180, 92],
            ["b", 290, 92],
            ["a", 125, 160],
            ["S", 180, 160],
            ["b", 235, 160],
            ["ε", 180, 223],
          ];
  const edges =
    kind === "arithmetic"
      ? [
          [0, 1],
          [0, 2],
          [0, 3],
          [1, 4],
          [4, 8],
          [8, 11],
          [3, 5],
          [3, 6],
          [3, 7],
          [5, 9],
          [9, 12],
          [7, 10],
        ]
      : kind === "ambiguous"
        ? [
            [0, 1],
            [0, 2],
            [0, 3],
            [1, 4],
            [3, 5],
            [3, 6],
            [3, 7],
            [5, 8],
            [7, 9],
          ]
        : [
            [0, 1],
            [0, 2],
            [0, 3],
            [2, 4],
            [2, 5],
            [2, 6],
            [5, 7],
          ];
  return (
    <svg
      viewBox="0 0 360 250"
      role="img"
      aria-label={
        kind === "arithmetic"
          ? "Parse tree of id + id * id; multiplication is nested inside addition"
          : kind === "ambiguous"
            ? "One valid parse tree of id + id + id, grouped on the right"
            : "Parse tree of a a b b using S → a S b or empty"
      }
    >
      <g stroke="currentColor" strokeWidth="1.4" opacity=".45">
        {edges.map(([a, b], i) => (
          <path
            key={i}
            d={`M${nodes[a][1]} ${nodes[a][2] + 14}V${(nodes[a][2] + nodes[b][2]) / 2}H${nodes[b][1]}V${nodes[b][2] - 14}`}
            fill="none"
          />
        ))}
      </g>
      {nodes.map(([s, x, y], i) => (
        <g key={i}>
          <rect
            x={x - 18}
            y={y - 15}
            width="36"
            height="30"
            rx="9"
            fill={["E", "S", "T", "F"].includes(s) ? "white" : "#f4bbd2"}
            stroke="currentColor"
            strokeWidth="1"
          />
          <text
            x={x}
            y={y + 5}
            fill="currentColor"
            textAnchor="middle"
            fontSize="16"
            fontFamily="IBM Plex Mono, monospace"
          >
            {s}
          </text>
        </g>
      ))}
    </svg>
  );
}

function Showcase({ grammar }) {
  const [step, setStep] = useState(0),
    [playing, setPlaying] = useState(true);
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!playing || reduce) return;
    const timer = setInterval(() => setStep((s) => (s + 1) % 5), 1350);
    return () => clearInterval(timer);
  }, [playing, reduce]);
  return (
    <div className={`landing-showcase ${grammar ? "showcase-grammar" : ""}`}>
      <div className="showcase-composition" aria-hidden="true">
        <div className="showcase-poster poster-tokens">
          <span>A LANGUAGE OF POSSIBILITIES</span>
          <b>
            0 1<br />0 1 1<br />1 0 0 1
          </b>
          <div className="token-pattern">
            {Array.from({ length: 12 }, (_, i) => (
              <i key={i} />
            ))}
          </div>
        </div>
        <div className="showcase-poster poster-statement">
          <span>THEORY, IN MOTION ↗</span>
          <p>
            Small steps.
            <br />
            Big <i>understanding.</i>
          </p>
          <div className="poster-orbit">
            <i />
            <i />
            <i />
          </div>
          <small>FOLLOW THE LOGIC. FIND THE PATTERN.</small>
        </div>
        <div className="showcase-poster poster-tree">
          <span>THERE’S A STRUCTURE TO IT.</span>
          <TreeIllustration />
          <b>
            One string.
            <br />
            More than one story.
          </b>
        </div>
        <div className="showcase-poster poster-machine">
          <span>01 / FINITE AUTOMATA</span>
          <h3>
            Every transition
            <br />
            tells a story.
          </h3>
          <StateIllustration step={step} />
          <div className="poster-input">
            <span>INPUT</span>
            {"1101".split("").map((s, i) => (
              <b className={step === i + 1 ? "current" : ""} key={i}>
                {s}
              </b>
            ))}
            <ArrowRight size={17} />
          </div>
        </div>
        <div className="showcase-poster poster-mint">
          <span>02 / CONTEXT-FREE GRAMMARS</span>
          <h3>
            Find the shape
            <br />
            inside the string.
          </h3>
          <TreeIllustration kind="balanced" />
          <small>S → a S b | ε</small>
        </div>
        <div className="showcase-poster poster-notes">
          <span>MAKE THE ABSTRACT CLICK.</span>
          <b>
            Think it.
            <br />
            Check it.
            <br />
            See it.
          </b>
          <div className="note-dots">
            {Array.from({ length: 9 }, (_, i) => (
              <i key={i} />
            ))}
          </div>
        </div>
      </div>
      <div
        className="showcase-description"
        role="img"
        aria-label="Animated collection of TheoryBERT worked examples: an automaton for strings ending in 01, a balanced grammar tree, and an ambiguous expression tree."
      />
      <div className="showcase-credit">
        <span className="showcase-credit-symbol">
          <Network size={20} />
        </span>
        <span>
          Made for your <b>aha moment.</b>
        </span>
      </div>
      <button
        className="showcase-pause"
        aria-label={
          playing ? "Pause showcase animation" : "Play showcase animation"
        }
        onClick={() => setPlaying((v) => !v)}
      >
        {playing ? <Pause size={17} /> : <Play size={17} />}
      </button>
    </div>
  );
}

const topicChips = [
  ["Ends in 01", "all"],
  ["Contains 01", "all"],
  ["Even number of 1s", "dfa"],
  ["Arithmetic", "cfg"],
  ["Ambiguous", "cfg"],
];

export default function Landing({
  catalog,
  connected,
  hosted,
  openExample,
  openGuide,
  openSettings,
  sessions,
  restore,
}) {
  const [menu, setMenu] = useState(false),
    [notice, setNotice] = useState(true),
    [mode, setMode] = useState("dfa");
  const [category, setCategory] = useState("all"),
    [query, setQuery] = useState(""),
    [sort, setSort] = useState("featured");
  const examples = [
    ...(catalog?.dfa || []).map((e) => ({ ...e, mode: "dfa" })),
    ...(catalog?.cfg || []).map((e) => ({ ...e, mode: "cfg" })),
  ];
  const filtered = examples.filter(
    (e) =>
      (category === "all" || e.mode === category) &&
      `${e.name} ${e.description || ""} ${e.grammar || ""} ${e.mode === "cfg" ? "grammar parse tree" : "finite automata"}`
        .toLowerCase()
        .includes(query.toLowerCase().trim()),
  );
  if (sort === "name") filtered.sort((a, b) => a.name.localeCompare(b.name));
  function search(event) {
    event.preventDefault();
    document
      .getElementById("explorations")
      .scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function start() {
    const sample =
      mode === "dfa"
        ? catalog?.dfa[0]
        : catalog?.cfg.find((e) => e.name === "Arithmetic");
    if (sample) openExample(sample, mode);
  }
  useEffect(() => {
    const listener = (e) => {
      if (e.key === "Escape") setMenu(false);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);
  return (
    <div className="landing">
      <a href="#main-content" className="landing-skip">
        Skip to content
      </a>
      <header className="landing-header">
        <Wordmark />
        <nav className="landing-desktop-nav" aria-label="Landing navigation">
          <a href="#explore">
            Explore <ChevronDown size={15} />
          </a>
          <div className="landing-nav-dropdown">
            <button aria-haspopup="true">
              The studios <ChevronDown size={15} />
            </button>
            <div className="landing-dropdown-content">
              <Link to="/dfa">
                <Network size={18} />
                <span>
                  DFA Studio
                  <small>Build a language. Follow a transition.</small>
                </span>
              </Link>
              <Link to="/grammar">
                <GitBranch size={18} />
                <span>
                  Grammar Lab<small>Find the structure inside a string.</small>
                </span>
              </Link>
            </div>
          </div>
          <button onClick={openGuide}>How it works</button>
          <Link to="/research">
            The research <ArrowUpRight size={14} />
          </Link>
        </nav>
        <div className="landing-header-actions">
          <Link to="/dfa" className="landing-header-cta">
            <Network size={18} />
            Open workspace
          </Link>
          <button
            className="landing-icon"
            aria-label="Quick guide"
            onClick={openGuide}
          >
            <BookOpen size={22} />
          </button>
          <button
            className="landing-icon"
            aria-label="Workspace settings"
            onClick={openSettings}
          >
            <Settings2 size={22} />
          </button>
          <button
            className="landing-menu-button landing-icon"
            aria-label={menu ? "Close menu" : "Open menu"}
            aria-expanded={menu}
            onClick={() => setMenu((v) => !v)}
          >
            {menu ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </header>
      {menu && (
        <nav
          className="landing-mobile-nav"
          aria-label="Mobile landing navigation"
        >
          <a href="#explore" onClick={() => setMenu(false)}>
            Explore examples <ArrowRight size={17} />
          </a>
          <Link to="/dfa">
            DFA Studio <Network size={17} />
          </Link>
          <Link to="/grammar">
            Grammar Lab <GitBranch size={17} />
          </Link>
          <Link to="/research">
            The research <ArrowUpRight size={17} />
          </Link>
          <button
            onClick={() => {
              setMenu(false);
              openGuide();
            }}
          >
            How it works <BookOpen size={17} />
          </button>
        </nav>
      )}
      <main id="main-content">
        <AnimatePresence initial={false}>
          {notice && (
            <motion.aside
              className="landing-notice"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, height: 0, marginBottom: 0, padding: 0 }}
            >
              <span className="notice-icon">
                <BookOpen size={20} />
              </span>
              <p>
                New to formal languages?{" "}
                <span>Start with a worked example. Make it your own.</span>
              </p>
              <a href="#explore">
                Find your first example <ArrowRight size={14} />
              </a>
              <button
                aria-label="Dismiss introduction banner"
                onClick={() => setNotice(false)}
              >
                <X size={20} />
              </button>
            </motion.aside>
          )}
        </AnimatePresence>
        <section className="landing-hero" aria-labelledby="landing-heading">
          <div className="landing-hero-copy">
            <div
              className="landing-mode-toggle"
              aria-label="Choose a learning mode"
            >
              <button
                aria-pressed={mode === "dfa"}
                onClick={() => setMode("dfa")}
              >
                FINITE AUTOMATA
              </button>
              <button
                aria-pressed={mode === "cfg"}
                onClick={() => setMode("cfg")}
              >
                GRAMMARS
              </button>
            </div>
            <h1 id="landing-heading" tabIndex={-1}>
              Explore the theory of
              <br />
              <span>
                {mode === "dfa" ? "finite automata." : "parse trees."}
              </span>
            </h1>
            <ul className="landing-benefits">
              {features.map((f) => (
                <li key={f}>
                  <span>
                    <Check size={16} strokeWidth={3} />
                  </span>
                  {f}
                </li>
              ))}
            </ul>
            <div className="landing-primary-action">
              {catalog ? (
                <button className="landing-cta" onClick={start}>
                  {mode === "dfa" ? (
                    <Network size={20} />
                  ) : (
                    <GitBranch size={20} />
                  )}
                  Start exploring <ArrowRight size={18} />
                </button>
              ) : (
                <Link
                  className="landing-cta"
                  to={mode === "dfa" ? "/dfa" : "/grammar"}
                >
                  Open the studio <ArrowRight size={18} />
                </Link>
              )}
              <span className="landing-local-status">
                <i className={connected === false ? "is-offline" : ""} />
                {connected === false
                  ? hosted
                    ? "Hosted engine offline"
                    : "Local engine offline"
                  : connected
                    ? hosted
                      ? "Hosted demo"
                      : "Runs locally"
                    : "Connecting…"}
              </span>
            </div>
          </div>
          <Showcase grammar={mode === "cfg"} />
        </section>
        <section
          className="landing-explore"
          id="explore"
          aria-label="Explore worked examples"
        >
          <div
            className="landing-explore-tabs"
            role="group"
            aria-label="Example category"
          >
            {[
              ["all", "All explorations", Layers3],
              ["dfa", "Finite automata", Network],
              ["cfg", "Grammars", GitBranch],
            ].map(([key, label, Icon]) => (
              <button
                key={key}
                aria-pressed={category === key}
                onClick={() => setCategory(key)}
              >
                <Icon size={20} />
                {label}
              </button>
            ))}
            <Link to="/examples">
              View the library <ArrowUpRight size={16} />
            </Link>
          </div>
          <form className="landing-search" role="search" onSubmit={search}>
            <label className="sr-only" htmlFor="landing-query">
              Search worked examples
            </label>
            <input
              id="landing-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What would you like to understand?"
            />
            <button type="submit" aria-label="Search examples">
              <Search size={24} />
            </button>
          </form>
          <div className="landing-discovery">
            <div className="landing-popular">
              <b>Try:</b>
              {topicChips.map(([q, c]) => (
                <button
                  key={q}
                  className={query === q ? "selected" : ""}
                  onClick={() => {
                    setQuery(query === q ? "" : q);
                    setCategory(c);
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
            <select
              aria-label="Sort examples"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="featured">Featured</option>
              <option value="name">Name: A–Z</option>
            </select>
          </div>
          <div className="landing-gallery-heading" id="explorations">
            <h2>
              {query
                ? `Results for “${query}”`
                : category === "dfa"
                  ? "A state for every possibility."
                  : category === "cfg"
                    ? "There’s a structure to it."
                    : "A good place to get curious."}
            </h2>
            <span>
              {catalog
                ? `${filtered.length} worked examples`
                : "Loading the local library…"}
            </span>
          </div>
          <div className="landing-gallery">
            {filtered.map((example, i) => (
              <motion.article
                className={`landing-example landing-example-${example.mode}`}
                key={example.id}
                initial={false}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3, delay: Math.min(i, 2) * 0.05 }}
              >
                <button
                  className={`landing-example-art example-art-${example.mode === "dfa" ? example.id : example.name === "Arithmetic" ? "arithmetic" : example.name === "Balanced a / b" ? "balanced" : "ambiguous"}`}
                  aria-label={`Explore ${example.name}`}
                  onClick={() => openExample(example, example.mode)}
                >
                  <span className="example-art-category">
                    {example.mode === "dfa"
                      ? "FINITE AUTOMATA"
                      : "CONTEXT-FREE GRAMMARS"}
                  </span>
                  {example.mode === "dfa" ? (
                    <Diagram
                      compact
                      dfa={example.preview.dfa}
                      graph={example.preview.graph}
                    />
                  ) : (
                    <TreeIllustration
                      kind={
                        example.name === "Balanced a / b"
                          ? "balanced"
                          : example.name === "Arithmetic"
                            ? "arithmetic"
                            : "ambiguous"
                      }
                    />
                  )}
                  <span className="example-art-input">
                    {example.mode === "dfa"
                      ? `INPUT / ${example.test}`
                      : example.input}
                  </span>
                  <span className="example-art-open">
                    <ArrowUpRight size={21} />
                  </span>
                </button>
                <div className="landing-example-caption">
                  <div>
                    <h3>
                      <button
                        onClick={() => openExample(example, example.mode)}
                      >
                        {example.name}
                      </button>
                    </h3>
                    <span>
                      {example.mode === "dfa" ? "DFA Studio" : "Grammar Lab"}{" "}
                      <i>·</i> Worked example
                    </span>
                  </div>
                  <span className="example-type-icon">
                    {example.mode === "dfa" ? (
                      <Network size={19} />
                    ) : (
                      <GitBranch size={19} />
                    )}
                  </span>
                </div>
              </motion.article>
            ))}
          </div>
          {catalog && !filtered.length && (
            <div className="landing-no-results">
              <Search size={28} />
              <h3>No examples match that search.</h3>
              <p>Try “arithmetic”, “01”, or choose a different category.</p>
              <button
                onClick={() => {
                  setQuery("");
                  setCategory("all");
                }}
              >
                Show all examples <ArrowRight size={16} />
              </button>
            </div>
          )}
          {!catalog && (
            <p className="landing-library-unavailable">
              {connected === false
                ? "The local library is unavailable. Open a studio to work with your own inputs."
                : "Connecting to your local example library…"}
            </p>
          )}
          <Link to="/dfa" className="landing-bottom-cta">
            Have a language in mind? Build your own. <ArrowRight size={18} />
          </Link>
        </section>
        {!!sessions.length && (
          <section className="landing-recents">
            <h2>Pick up where you left off.</h2>
            <div>
              {sessions.slice(0, 3).map((s) => (
                <button key={s.id} onClick={() => restore(s)}>
                  <span>
                    {s.mode === "dfa" ? (
                      <Network size={18} />
                    ) : (
                      <GitBranch size={18} />
                    )}
                  </span>
                  {s.name}
                  <ArrowUpRight size={18} />
                </button>
              ))}
            </div>
          </section>
        )}
      </main>
      <footer className="landing-footer">
        <Wordmark />
        <p>A little less abstract. A lot more understood.</p>
        <nav aria-label="Footer navigation">
          <Link to="/dfa">DFA Studio</Link>
          <Link to="/grammar">Grammar Lab</Link>
          <Link to="/research">Research</Link>
          <button onClick={openGuide}>Quick guide</button>
        </nav>
        <span>Built to explore. Verified before visualised.</span>
      </footer>
    </div>
  );
}
