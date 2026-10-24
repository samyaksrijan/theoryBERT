import * as React from "react";
import { useState, useEffect, useRef, useId } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Code2,
  Download,
  FileJson,
  FlaskConical,
  GitBranch,
  GraduationCap,
  History,
  Home,
  Info,
  Layers3,
  Lightbulb,
  Loader2,
  Menu,
  Network,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
  Settings2,
  ShieldCheck,
  ShieldX,
  SkipBack,
  SkipForward,
  Sparkles,
  Terminal,
  Upload,
  Workflow,
  X,
  AlertCircle,
  Monitor,
  ExternalLink,
} from "lucide-react";
import Diagram, { StateTag } from "./components/Diagram";
import { api, downloadJSON, runTask, useStorageState } from "./api";
import Landing from "./Landing";
import { Wordmark } from "./components/Brand";

const initialDfa = {
  description: "Binary strings that end in 01.",
  input: "1101",
  source: "demo",
  example_id: "manual-suffix-01",
  reference_json: "",
  result: null,
  signature: null,
  video: null,
};
const initialCfg = {
  grammar: "E -> E '+' T | T\nT -> T '*' F | F\nF -> '(' E ')' | 'id'",
  input: "id + id * id",
  result: null,
  signature: null,
  video: null,
  treeIndex: 0,
};
const initialSettings = {
  checkpoint: "",
  budget: 5,
  parseLimit: 5,
  quality: "preview",
};
const navItems = [
  { path: "/", label: "Overview", icon: Home },
  { path: "/dfa", label: "DFA Studio", icon: Network },
  { path: "/grammar", label: "Grammar Lab", icon: GitBranch },
  { path: "/examples", label: "Example Library", icon: Layers3 },
  { path: "/research", label: "Research", icon: FlaskConical },
];
const sourceNames = {
  demo: "Reference demonstration",
  learned: "Learned checkpoint",
  rule: "Rule-based baseline",
  incorrect: "Incorrect candidate fixture",
};
const sourceDetails = {
  demo: "A known reference example. No learned prediction.",
  learned: "Direct structured prediction from your local checkpoint.",
  rule: "Limited handwritten patterns. Unsupported requests are reported.",
  incorrect: "A deliberate negative fixture to explore counterexamples.",
};
const phaseLabels = {
  queued: "Waiting for the local engine",
  predicting: "Predicting candidate structure",
  parsing: "Constructing the Earley parse forest",
  verifying: "Checking the mathematics independently",
  rendering: "Building your Manim animation",
  complete: "Complete",
};
const dateFormat = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

function Button({
  children,
  icon: Icon,
  variant = "primary",
  className = "",
  ...props
}) {
  return (
    <button className={`button button-${variant} ${className}`} {...props}>
      {Icon && <Icon size={16} />}
      {children}
    </button>
  );
}
function Badge({ children, tone = "neutral", icon: Icon }) {
  return (
    <span className={`badge badge-${tone}`}>
      {Icon && <Icon size={12} />}
      {children}
    </span>
  );
}
function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef(null),
    id = useId();
  useEffect(() => {
    ref.current.showModal();
    return () => {
      if (ref.current?.open) ref.current.close();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? "modal-wide" : ""}`}
      aria-labelledby={id}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="modal-inner"
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">THEORYBERT WORKSPACE</span>
            <h2 id={id}>{title}</h2>
          </div>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
          >
            <X size={20} />
          </button>
        </div>
        {children}
      </motion.div>
    </dialog>
  );
}
function PageIntro({ eyebrow, title, description, children }) {
  return (
    <div className="page-intro">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="page-actions">{children}</div>
    </div>
  );
}

export default function App() {
  const [catalog, setCatalog] = useState(null),
    [connected, setConnected] = useState(null);
  const [settings, setSettings] = useStorageState(
    React,
    "theorybert.settings.v3",
    initialSettings,
  );
  const [dfa, setDfa] = useStorageState(React, "theorybert.dfa.v3", initialDfa);
  const [cfg, setCfg] = useStorageState(React, "theorybert.cfg.v3", initialCfg);
  const [sessions, setSessions] = useStorageState(
    React,
    "theorybert.sessions.v3",
    [],
  );
  const [busy, setBusy] = useState({}),
    [settingsOpen, setSettingsOpen] = useState(false),
    [guideOpen, setGuideOpen] = useState(false),
    [mobileNav, setMobileNav] = useState(false);
  const [narrow, setNarrow] = useState(() => window.innerWidth <= 800);
  const location = useLocation(),
    navigate = useNavigate();
  const routeName =
    navItems.find((n) => n.path === location.pathname)?.label || "Workspace";
  useEffect(() => {
    const resize = () => setNarrow(window.innerWidth <= 800);
    const escape = (event) => {
      if (event.key === "Escape") setMobileNav(false);
    };
    window.addEventListener("resize", resize);
    window.addEventListener("keydown", escape);
    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("keydown", escape);
    };
  }, []);
  useEffect(() => {
    let live = true;
    const refresh = () =>
      Promise.all([api("/health"), api("/catalog")])
        .then(([, data]) => {
          if (live) {
            setConnected(true);
            setCatalog(data);
          }
        })
        .catch(() => {
          if (live) setConnected(false);
        });
    refresh();
    const timer = setInterval(refresh, 20000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    setMobileNav(false);
    window.scrollTo({ top: 0 });
    document.title = `${routeName} · TheoryBERT`;
  }, [location.pathname]);
  function remember(result, form, signature) {
    setSessions((previous) =>
      [
        {
          id: result.id,
          mode: result.mode,
          name:
            result.mode === "dfa"
              ? result.description
              : catalog?.cfg.find((e) => e.grammar === result.grammar)?.name ||
                "Custom grammar",
          result,
          form,
          signature,
          settings,
          created: Date.now(),
        },
        ...previous.filter((s) => s.id !== result.id),
      ].slice(0, 8),
    );
  }
  function openExample(example, mode) {
    if (mode === "dfa")
      setDfa({
        ...initialDfa,
        description: example.description,
        input: example.test,
        example_id: example.id,
      });
    else
      setCfg({ ...initialCfg, grammar: example.grammar, input: example.input });
    navigate(mode === "dfa" ? "/dfa" : "/grammar");
  }
  function restore(session) {
    setSettings(session.settings);
    if (session.mode === "dfa")
      setDfa({
        ...session.form,
        result: session.result,
        signature: session.signature,
        video: null,
      });
    else
      setCfg({
        ...session.form,
        result: session.result,
        signature: session.signature,
        video: null,
      });
    navigate(session.mode === "dfa" ? "/dfa" : "/grammar");
  }
  const shared = {
    catalog,
    connected,
    settings,
    setSettings,
    busy,
    setBusy,
    remember,
    openSettings: () => setSettingsOpen(true),
  };
  if (location.pathname === "/") {
    return (
      <>
        <Landing
          catalog={catalog}
          connected={connected}
          openExample={openExample}
          openGuide={() => setGuideOpen(true)}
          openSettings={() => setSettingsOpen(true)}
          sessions={sessions}
          restore={restore}
        />
        {settingsOpen && (
          <SettingsModal
            settings={settings}
            setSettings={setSettings}
            catalog={catalog}
            onClose={() => setSettingsOpen(false)}
          />
        )}
        {guideOpen && (
          <Guide onClose={() => setGuideOpen(false)} catalog={catalog} />
        )}
      </>
    );
  }
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to workspace
      </a>
      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside
        className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}
        inert={narrow && !mobileNav ? true : undefined}
        aria-hidden={narrow && !mobileNav ? true : undefined}
      >
        <Wordmark className="workspace-wordmark" />
        <div className="nav-group-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navItems.slice(0, 3).map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <Icon size={18} strokeWidth={1.7} />
              <span>{label}</span>
              {path === "/dfa" && <span className="nav-tag">STUDIO</span>}
            </NavLink>
          ))}
        </nav>
        <div className="nav-group-label discover-label">DISCOVER</div>
        <nav aria-label="Resources">
          {navItems.slice(3).map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <Icon size={18} strokeWidth={1.7} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="sidebar-note-icon">
            <Lightbulb size={19} />
          </span>
          <h3>Make the abstract click.</h3>
          <p>A language. A proof. A visual explanation.</p>
          <button onClick={() => setGuideOpen(true)}>
            Take a quick tour <ArrowUpRight size={15} />
          </button>
        </div>
        <div className="sidebar-bottom">
          <button
            className="nav-item settings-link"
            onClick={() => setSettingsOpen(true)}
          >
            <Settings2 size={18} />
            <span>Workspace settings</span>
          </button>
          <div className="local-status">
            <span
              className={`connection-dot ${connected === false ? "offline" : ""}`}
            />
            <div>
              Local engine
              <small>
                {connected === false
                  ? "Connection unavailable"
                  : connected
                    ? "Connected to your machine"
                    : "Connecting…"}
              </small>
            </div>
            <Monitor size={16} />
          </div>
        </div>
      </aside>
      <div
        className="main-shell"
        inert={narrow && mobileNav ? true : undefined}
      >
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              onClick={() => setMobileNav((v) => !v)}
              aria-label="Open navigation"
              aria-expanded={mobileNav}
            >
              <Menu size={21} />
            </button>
            <span className="breadcrumb-root">Workspace</span>
            <ChevronRight size={13} />
            <span>{routeName}</span>
          </div>
          <div className="topbar-right">
            <span className="local-pill">
              <span
                className={`connection-dot ${connected === false ? "offline" : ""}`}
              />
              {connected === false ? "Engine offline" : "Runs locally"}
            </span>
            <button
              className="topbar-help"
              aria-label="Quick guide"
              onClick={() => setGuideOpen(true)}
            >
              <BookOpen size={16} />
              <span>Quick guide</span>
            </button>
            <span className="avatar" aria-label="Local workspace">
              TB
            </span>
          </div>
        </header>
        {connected === false && (
          <div className="connection-banner" role="alert">
            <AlertCircle size={16} />
            The local engine is unavailable. Start the Python server to verify
            and render your work.
            <button
              onClick={() =>
                api("/health")
                  .then(() => setConnected(true))
                  .catch(() => {})
              }
            >
              Retry connection
            </button>
          </div>
        )}
        <main id="main-content" className="page-content">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 9 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2 }}
            >
              <Routes>
                <Route
                  path="/dfa"
                  element={
                    <DfaStudio {...shared} form={dfa} setForm={setDfa} />
                  }
                />
                <Route
                  path="/grammar"
                  element={
                    <GrammarLab {...shared} form={cfg} setForm={setCfg} />
                  }
                />
                <Route
                  path="/examples"
                  element={
                    <Examples catalog={catalog} openExample={openExample} />
                  }
                />
                <Route path="/research" element={<Research />} />
                <Route
                  path="*"
                  element={
                    <div className="not-found">
                      <Network size={42} />
                      <h1>This state is unreachable.</h1>
                      <p>Let’s take you back to the workspace.</p>
                      <Link className="button button-primary" to="/">
                        Back to overview <ArrowRight size={16} />
                      </Link>
                    </div>
                  }
                />
              </Routes>
            </motion.div>
          </AnimatePresence>
        </main>
        <footer className="app-footer">
          <span>
            TheoryBERT <span className="footer-dot">·</span> An interactive
            formal languages lab
          </span>
          <span>
            <ShieldCheck size={13} />
            Verified before visualised.
          </span>
        </footer>
      </div>
      {settingsOpen && (
        <SettingsModal
          settings={settings}
          setSettings={setSettings}
          catalog={catalog}
          onClose={() => setSettingsOpen(false)}
        />
      )}
      {guideOpen && (
        <Guide onClose={() => setGuideOpen(false)} catalog={catalog} />
      )}
    </div>
  );
}

function usePlayback(resultKey, count) {
  const [step, setStep] = useState(0),
    [playing, setPlaying] = useState(false),
    [speed, setSpeed] = useState(1);
  useEffect(() => {
    setStep(0);
    setPlaying(false);
  }, [resultKey]);
  useEffect(() => {
    if (step >= count) setPlaying(false);
  }, [step, count]);
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(
      () => setStep((s) => Math.min(count, s + 1)),
      950 / speed,
    );
    return () => clearInterval(timer);
  }, [playing, speed, count]);
  return {
    step: Math.min(step, count),
    setStep,
    playing,
    setPlaying,
    speed,
    setSpeed,
    toggle: () => {
      if (step >= count) setStep(0);
      setPlaying((v) => !v);
    },
    reset: () => {
      setStep(0);
      setPlaying(false);
    },
  };
}
function Playback({
  playback,
  count,
  tokens,
  mode = "dfa",
  explanation,
  completed,
}) {
  const { step, setStep, playing, speed, setSpeed, toggle, reset, setPlaying } =
    playback;
  return (
    <div className="playback">
      <div className="input-tape">
        <span className="tape-label">
          {mode === "dfa" ? "INPUT STRING" : "TERMINAL YIELD"}
        </span>
        <div
          className="token-list"
          aria-label={mode === "dfa" ? "Input symbols" : "Terminal yield"}
        >
          {tokens.length ? (
            tokens.map((token, i) => (
              <span
                key={i}
                className={`input-token ${mode === "dfa" && i < step ? "consumed" : ""} ${mode === "dfa" && i === step - 1 ? "current" : ""}`}
              >
                {token}
              </span>
            ))
          ) : (
            <span className="epsilon-token">
              ε <small>empty input</small>
            </span>
          )}
        </div>
        <span className="step-count">
          {String(step).padStart(2, "0")}{" "}
          <span>/ {String(count).padStart(2, "0")}</span>
        </span>
      </div>
      <div className="transport-row">
        <button
          className="play-button"
          disabled={!count}
          onClick={toggle}
          aria-label={playing ? "Pause playback" : "Play playback"}
        >
          {playing ? (
            <Pause size={17} fill="currentColor" />
          ) : (
            <Play size={17} fill="currentColor" />
          )}
        </button>
        <button
          className="icon-button"
          onClick={() => {
            setPlaying(false);
            setStep((s) => Math.max(0, s - 1));
          }}
          disabled={step === 0}
          aria-label="Step backward"
        >
          <SkipBack size={17} />
        </button>
        <button
          className="icon-button"
          onClick={() => {
            setPlaying(false);
            setStep((s) => Math.min(count, s + 1));
          }}
          disabled={step >= count}
          aria-label="Step forward"
        >
          <SkipForward size={17} />
        </button>
        <input
          className="step-slider"
          aria-label="Execution step"
          type="range"
          min="0"
          max={Math.max(1, count)}
          value={step}
          disabled={!count}
          onChange={(e) => {
            setPlaying(false);
            setStep(Number(e.target.value));
          }}
          style={{ "--progress": `${count ? (step / count) * 100 : 0}%` }}
        />
        <select
          aria-label="Playback speed"
          className="speed-select"
          value={speed}
          onChange={(e) => setSpeed(Number(e.target.value))}
        >
          {[0.5, 1, 1.5, 2].map((v) => (
            <option key={v} value={v}>
              {v}×
            </option>
          ))}
        </select>
        <button
          className="icon-button"
          onClick={reset}
          aria-label="Restart playback"
        >
          <RotateCcw size={16} />
        </button>
      </div>
      <div
        className={`execution-explanation ${completed ? "completed" : ""}`}
        aria-live="polite"
      >
        <span className="explanation-icon">
          {completed ? <CheckCheck size={17} /> : <ArrowRight size={17} />}
        </span>
        <span>{explanation}</span>
        {completed && <Badge tone="success">COMPLETE</Badge>}
      </div>
    </div>
  );
}
function Progress({ phase, mode }) {
  if (!phase) return null;
  const rendering = phase === "rendering",
    verifying = phase === "verifying";
  return (
    <div className="progress-overlay" role="status" aria-live="polite">
      <span className="progress-orbit">
        <Loader2 size={26} />
      </span>
      <h3>{phaseLabels[phase] || "Working on your request"}</h3>
      <p>
        {rendering
          ? "Manim is turning the checked trace into a video."
          : "Your inputs stay on this machine."}
      </p>
      <div className="progress-steps">
        <span className={!verifying && !rendering ? "active" : "done"}>
          {verifying || rendering ? <Check size={12} /> : <i />}
          {mode === "cfg" ? "Parsing" : "Predicting"}
        </span>
        <ChevronRight size={12} />
        <span className={verifying ? "active" : rendering ? "done" : ""}>
          Verifying
        </span>
        <ChevronRight size={12} />
        <span className={rendering ? "active" : ""}>Rendering</span>
      </div>
    </div>
  );
}
function EmptyCanvas({ stale, cfg = false, error }) {
  return (
    <div className="canvas-empty">
      <div
        className={`empty-graphic ${cfg ? "empty-tree" : ""}`}
        aria-hidden="true"
      >
        {cfg ? (
          <>
            <span>E</span>
            <div>
              <i>E</i>
              <i>+</i>
              <i>T</i>
            </div>
          </>
        ) : (
          <>
            <i>q₀</i>
            <span>→</span>
            <i>q₁</i>
            <span>→</span>
            <i>q₂</i>
          </>
        )}
      </div>
      <Badge
        icon={stale || error ? AlertCircle : Sparkles}
        tone={stale || error ? "warning" : "neutral"}
      >
        {stale
          ? "INPUTS CHANGED"
          : error
            ? "LET’S ADJUST THE INPUT"
            : "YOUR CANVAS IS READY"}
      </Badge>
      <h3>
        {stale
          ? "A fresh input needs a fresh check."
          : error
            ? "There’s a detail to resolve."
            : cfg
              ? "Every string has a structure."
              : "Give your language a shape."}
      </h3>
      <p>
        {stale
          ? "Verify again to update the diagram, trace, and animation."
          : error ||
            (cfg
              ? "Choose a grammar, then parse and verify to reveal its derivation."
              : "Choose an example or describe a language. Verify it to unlock interactive playback.")}
      </p>
      <div className="empty-proof">
        <ShieldCheck size={15} />
        {cfg
          ? "Every production and terminal leaf is checked."
          : "Only independently verified machines can play."}
      </div>
    </div>
  );
}
function Outcome({ result }) {
  if (result.verified)
    return (
      <Badge tone="success" icon={ShieldCheck}>
        Verified {result.mode === "dfa" ? "language" : "derivation"}
      </Badge>
    );
  return (
    <Badge
      tone={
        result.status === "EQUIVALENCE_FAILED" ||
        result.status === "STRUCTURE_INVALID"
          ? "danger"
          : "warning"
      }
      icon={result.status === "EQUIVALENCE_FAILED" ? ShieldX : AlertCircle}
    >
      {result.status === "REFERENCE_UNAVAILABLE"
        ? "Reference needed"
        : result.status === "EQUIVALENCE_FAILED"
          ? "Candidate rejected"
          : result.status === "RESOURCE_LIMIT"
            ? "Resource limit"
            : "Verification incomplete"}
    </Badge>
  );
}
function FailedResult({ result }) {
  const report = result.reports.at(-1);
  return (
    <div className="failed-result">
      <span
        className={`failed-icon ${result.status === "REFERENCE_UNAVAILABLE" ? "unverified" : ""}`}
      >
        {result.status === "REFERENCE_UNAVAILABLE" ? (
          <ShieldCheck size={32} />
        ) : (
          <ShieldX size={32} />
        )}
      </span>
      <h3>
        {result.status === "REFERENCE_UNAVAILABLE"
          ? "A structure, awaiting a reference."
          : "The verifier found a difference."}
      </h3>
      <p>{report.message}</p>
      {report.counterexample !== null &&
        report.counterexample !== undefined && (
          <div className="counterexample">
            <span className="eyebrow">SHORTEST DISTINGUISHING STRING</span>
            <code>{report.counterexample.join("") || "ε"}</code>
            <small>
              {report.counterexample.length
                ? "The candidate and reference disagree on this input."
                : "The machines disagree on empty-string acceptance."}
            </small>
          </div>
        )}
      <span className="locked-note">
        <ShieldCheck size={14} />
        Animation stays locked until verification passes.
      </span>
    </div>
  );
}
function SourceLine({ result }) {
  return (
    <div className="source-line">
      <span>
        <CircleDot size={12} />
        {result.source}
      </span>
      <span>{Math.round(result.elapsed_seconds * 1000)} ms</span>
    </div>
  );
}

function DfaStudio({
  catalog,
  connected,
  settings,
  form,
  setForm,
  busy,
  setBusy,
  remember,
  openSettings,
}) {
  const [error, setError] = useState(""),
    [selected, setSelected] = useState(null),
    [videoOpen, setVideoOpen] = useState(false);
  const signature = JSON.stringify([
    form.description,
    form.input,
    form.source,
    form.example_id,
    form.reference_json,
    settings.checkpoint,
    settings.budget,
  ]);
  const result = form.result,
    current = !!result && form.signature === signature;
  const trace = current && result.verified ? result.trace : null;
  const playback = usePlayback(
    current ? result.id : "none",
    trace?.steps.length || 0,
  );
  const phase = busy.dfa,
    renderPhase =
      busy.render?.mode === "dfa" && busy.render?.id === result?.id
        ? busy.render.phase
        : null;
  const patch = (values) => setForm((prev) => ({ ...prev, ...values }));
  const selectedExample = catalog?.dfa.find(
    (e) => e.id === form.example_id && e.description === form.description,
  );
  const stringError = /[^01]/.test(form.input)
    ? "Use only 0 and 1, without spaces."
    : form.input.length > 40
      ? "Keep the input to 40 symbols or fewer."
      : "";
  const blocked = !connected
    ? "Connect to the local engine to begin."
    : !form.description.trim()
      ? "Describe a language or choose an example."
      : stringError ||
        (form.source === "demo" && !selectedExample
          ? "Choose an example for a reference demonstration, or change the prediction source."
          : form.source === "learned" && !settings.checkpoint
            ? "Choose a checkpoint in workspace settings."
            : "");
  async function verify() {
    if (blocked || phase) return;
    setError("");
    patch({ result: null, signature: null, video: null });
    setSelected(null);
    setBusy((prev) => ({ ...prev, dfa: "predicting" }));
    const request = {
      kind: "dfa",
      ...form,
      checkpoint: settings.checkpoint,
      budget: settings.budget,
    };
    delete request.result;
    delete request.video;
    try {
      const response = await runTask(request, (value) =>
        setBusy((prev) => ({ ...prev, dfa: value })),
      );
      patch({ result: response, signature, video: null });
      remember(response, { ...form, result: null, video: null }, signature);
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy((prev) => ({ ...prev, dfa: null }));
    }
  }
  const videoReady =
    current &&
    form.video?.result_id === result.id &&
    form.video?.quality === settings.quality;
  async function exportVideo() {
    if (videoReady) {
      setVideoOpen(true);
      return;
    }
    const id = result.id;
    setBusy((prev) => ({
      ...prev,
      render: { mode: "dfa", id, phase: "rendering" },
    }));
    try {
      const video = await runTask(
        { kind: "render", result_id: id, quality: settings.quality },
        (value) =>
          setBusy((prev) => ({
            ...prev,
            render: { mode: "dfa", id, phase: value },
          })),
      );
      setForm((prev) =>
        prev.result?.id === id
          ? { ...prev, video: { ...video, result_id: id } }
          : prev,
      );
      setVideoOpen(true);
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy((prev) => ({ ...prev, render: null }));
    }
  }
  const active = trace
    ? playback.step
      ? trace.steps[playback.step - 1].destination
      : trace.initial_state
    : null;
  const transition =
    trace && playback.step ? trace.steps[playback.step - 1] : null;
  const complete = !!trace && playback.step === trace.steps.length;
  const explanation = trace ? (
    complete ? (
      <>
        <b>{trace.accepted ? "ACCEPT" : "REJECT"}</b> — {active} is{" "}
        {trace.accepted ? "an accepting" : "a non-accepting"} state.
      </>
    ) : transition ? (
      <>
        Read <code>{transition.symbol}</code>:{" "}
        <StateTag small state={transition.source} dfa={result.dfa} /> →{" "}
        <StateTag small state={transition.destination} dfa={result.dfa} />.
        Next, read <code>{trace.symbols[playback.step]}</code>.
      </>
    ) : (
      <>
        Start in <StateTag small state={trace.initial_state} dfa={result.dfa} />
        . The next symbol is <code>{trace.symbols[0]}</code>.
      </>
    )
  ) : null;
  return (
    <>
      <PageIntro
        eyebrow="01 / THEORY OF COMPUTATION"
        title={
          <>
            DFA <em>Studio.</em>
          </>
        }
        description="Give a language a shape. Follow the logic, one transition at a time."
      >
        <Button variant="secondary" icon={Settings2} onClick={openSettings}>
          Configure
        </Button>
      </PageIntro>
      <div className="studio-layout">
        <section className="panel input-panel">
          <div className="studio-panel-title">
            <span className="step-dot">1</span>
            <h2>Define your language</h2>
            <Network size={18} />
          </div>
          <label className="field-label">START WITH AN EXAMPLE</label>
          <div className="example-chips">
            {catalog?.dfa.map((e) => (
              <button
                key={e.id}
                className={selectedExample?.id === e.id ? "selected" : ""}
                disabled={!!phase}
                onClick={() => {
                  patch({
                    description: e.description,
                    input: e.test,
                    example_id: e.id,
                  });
                  setError("");
                }}
              >
                {e.name}
              </button>
            ))}
          </div>
          <label className="field-label" htmlFor="language-description">
            Language description <span>ENGLISH → DFA</span>
          </label>
          <textarea
            id="language-description"
            className="language-editor"
            value={form.description}
            onChange={(e) => patch({ description: e.target.value })}
            maxLength={4000}
            disabled={!!phase}
            placeholder="Binary strings that end in 01."
          />
          <div className="field-under">
            <span>
              Binary alphabet <code>{"{0, 1}"}</code>
            </span>
            <span>{form.description.length}/4000</span>
          </div>
          <label className="field-label" htmlFor="dfa-input">
            Test string <span>OPTIONAL</span>
          </label>
          <div
            className={`text-input with-prefix ${stringError ? "input-invalid" : ""}`}
          >
            <span>Σ*</span>
            <input
              id="dfa-input"
              value={form.input}
              onChange={(e) => patch({ input: e.target.value })}
              disabled={!!phase}
              placeholder="1101"
              maxLength={80}
            />
            <span className="field-suffix">{form.input.length} symbols</span>
          </div>
          {stringError && (
            <p className="inline-error">
              <AlertCircle size={13} />
              {stringError}
            </p>
          )}
          <p className="field-help">
            Leave blank to explore the empty string, ε.
          </p>
          <label className="field-label" htmlFor="prediction-source">
            Prediction source
          </label>
          <div className="select-wrap">
            <select
              id="prediction-source"
              value={form.source}
              onChange={(e) => patch({ source: e.target.value })}
              disabled={!!phase}
            >
              {Object.entries(sourceNames).map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
            <ChevronDown size={15} />
          </div>
          <p className="field-help source-help">{sourceDetails[form.source]}</p>
          {form.source === "learned" && (
            <button className="checkpoint-shortcut" onClick={openSettings}>
              <Settings2 size={13} />
              {settings.checkpoint || "Select a local checkpoint"}
              <ChevronRight size={13} />
            </button>
          )}
          <details className="reference-details">
            <summary>
              <FileJson size={15} />
              Independent reference{" "}
              <span>
                {form.reference_json
                  ? "CUSTOM JSON"
                  : selectedExample
                    ? "BENCHMARK"
                    : "OPTIONAL JSON"}
              </span>
              <ChevronRight size={14} />
            </summary>
            <p>
              A separate formal reference is needed to establish language
              equivalence.
            </p>
            <textarea
              aria-label="Reference DFA JSON"
              className="json-editor"
              value={form.reference_json}
              onChange={(e) => patch({ reference_json: e.target.value })}
              placeholder={'{"schema_version": "1.0", "states": …}'}
              disabled={!!phase}
            />
            <div className="reference-actions">
              <label className="upload-button">
                <Upload size={13} />
                Upload JSON
                <input
                  type="file"
                  accept=".json,application/json"
                  disabled={!!phase}
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    if (file.size > 120000) {
                      setError(
                        "Use a reference JSON file smaller than 120 KB.",
                      );
                      return;
                    }
                    patch({ reference_json: await file.text() });
                    e.target.value = "";
                  }}
                />
              </label>
              {form.reference_json && (
                <button
                  className="text-link"
                  onClick={() => patch({ reference_json: "" })}
                >
                  Clear
                </button>
              )}
            </div>
          </details>
          {error && (
            <div className="form-error" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}
          <Button
            className="verify-button"
            icon={phase ? Loader2 : Sparkles}
            onClick={verify}
            disabled={!!blocked || !!phase}
          >
            {phase ? "Working on your machine…" : "Build & verify"}
            {!phase && <ArrowRight size={16} />}
          </Button>
          {blocked && <p className="action-help">{blocked}</p>}
          <div className="input-guarantee">
            <ShieldCheck size={13} />
            {form.reference_json
              ? "Using your independent reference"
              : selectedExample
                ? "Independent benchmark reference included"
                : "Prediction is allowed without a reference"}
          </div>
        </section>
        <section className="panel canvas-panel">
          <div className="canvas-panel-head">
            <div>
              <span className="eyebrow">THE WORKSPACE</span>
              <h2>Machine canvas</h2>
            </div>
            {current ? (
              <Outcome result={result} />
            ) : (
              <Badge icon={CircleDot}>
                {result ? "Needs a fresh check" : "Ready to explore"}
              </Badge>
            )}
          </div>
          <div className="canvas-body">
            {phase ? (
              <Progress phase={phase} />
            ) : current ? (
              result.verified ? (
                result.graph ? (
                  <Diagram
                    key={result.id}
                    graph={result.graph}
                    dfa={result.dfa}
                    active={active}
                    transition={transition}
                    selected={selected}
                    onSelect={setSelected}
                  />
                ) : (
                  <div className="visual-limit">
                    <Network size={32} />
                    <h3>Verified, with a larger structure.</h3>
                    <p>{result.visual_error}</p>
                    <Badge tone="success" icon={ShieldCheck}>
                      {result.dfa.states.length} states · language verified
                    </Badge>
                  </div>
                )
              ) : (
                <FailedResult result={result} />
              )
            ) : (
              <EmptyCanvas stale={!!result} error={error} />
            )}
          </div>
          {current && result.verified && (
            <>
              <Playback
                playback={playback}
                count={trace.steps.length}
                tokens={trace.symbols}
                explanation={explanation}
                completed={complete}
              />
              {selected && (
                <div className="node-inspector">
                  <StateTag state={selected} dfa={result.dfa} />
                  <span>
                    {result.dfa.accept_states.includes(selected)
                      ? "Accepting state"
                      : "Non-accepting state"}
                    {selected === result.dfa.start_state ? " · initial" : ""}
                  </span>
                  <div>
                    {Object.entries(result.dfa.transitions[selected]).map(
                      ([a, target]) => (
                        <span key={a}>
                          <code>{a}</code> →{" "}
                          <StateTag small state={target} dfa={result.dfa} />
                        </span>
                      ),
                    )}
                  </div>
                  <button
                    className="icon-button"
                    aria-label="Close state inspector"
                    onClick={() => setSelected(null)}
                  >
                    <X size={13} />
                  </button>
                </div>
              )}
            </>
          )}
          {current && <SourceLine result={result} />}
          <div className="canvas-export-bar">
            <span>
              <ShieldCheck size={14} />
              {current && result.verified
                ? "The checked trace powers every frame."
                : "Verification unlocks animation."}
            </span>
            <Button
              variant="secondary"
              icon={renderPhase ? Loader2 : videoReady ? Play : Download}
              disabled={
                !current || !result.renderable || !!renderPhase || !!busy.render
              }
              onClick={exportVideo}
            >
              {renderPhase
                ? "Rendering…"
                : videoReady
                  ? "View video"
                  : "Export animation"}
            </Button>
          </div>
          {renderPhase && (
            <div className="render-progress" role="status">
              <Loader2 size={15} />
              Rendering the verified trace with Manim. This may take a moment.
            </div>
          )}
        </section>
      </div>
      {current && <DfaEvidence result={result} />}
      <div className="scope-note">
        <Info size={15} />
        <p>
          <b>What’s verified?</b> Exact language equivalence to an independent
          reference. A verified machine can accept or reject your test string;
          both are valid executions.
        </p>
      </div>
      {videoOpen && videoReady && (
        <VideoModal
          video={form.video}
          result={result}
          onClose={() => setVideoOpen(false)}
        />
      )}
    </>
  );
}

function GrammarLab({
  catalog,
  connected,
  settings,
  form,
  setForm,
  busy,
  setBusy,
  remember,
  openSettings,
}) {
  const [error, setError] = useState(""),
    [selected, setSelected] = useState(null),
    [videoOpen, setVideoOpen] = useState(false);
  const signature = JSON.stringify([
    form.grammar,
    form.input,
    settings.parseLimit,
  ]);
  const result = form.result,
    current = !!result && form.signature === signature;
  const index = form.treeIndex || 0,
    steps = current ? result.steps[index] : [];
  const playback = usePlayback(
    current ? `${result.id}-${index}` : "none",
    steps.length,
  );
  const phase = busy.cfg,
    renderPhase =
      busy.render?.mode === "cfg" && busy.render?.id === result?.id
        ? busy.render.phase
        : null;
  const patch = (values) => setForm((prev) => ({ ...prev, ...values }));
  const blocked = !connected
    ? "Connect to the local engine to begin."
    : !form.grammar.trim()
      ? "Write a grammar or choose an example."
      : "";
  async function verify() {
    if (blocked || phase) return;
    setError("");
    patch({ result: null, signature: null, video: null, treeIndex: 0 });
    setSelected(null);
    setBusy((prev) => ({ ...prev, cfg: "parsing" }));
    try {
      const response = await runTask(
        {
          kind: "cfg",
          grammar: form.grammar,
          input: form.input,
          limit: settings.parseLimit,
        },
        (value) => setBusy((prev) => ({ ...prev, cfg: value })),
      );
      patch({ result: response, signature, video: null, treeIndex: 0 });
      remember(
        response,
        { ...form, treeIndex: 0, result: null, video: null },
        signature,
      );
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy((prev) => ({ ...prev, cfg: null }));
    }
  }
  const videoReady =
    current &&
    form.video?.result_id === result.id &&
    form.video.tree_index === index &&
    form.video.quality === settings.quality;
  async function exportVideo() {
    if (videoReady) {
      setVideoOpen(true);
      return;
    }
    const id = result.id;
    setBusy((prev) => ({
      ...prev,
      render: { mode: "cfg", id, phase: "rendering" },
    }));
    try {
      const video = await runTask(
        {
          kind: "render",
          result_id: id,
          tree_index: index,
          quality: settings.quality,
        },
        (value) =>
          setBusy((prev) => ({
            ...prev,
            render: { mode: "cfg", id, phase: value },
          })),
      );
      setForm((prev) =>
        prev.result?.id === id
          ? { ...prev, video: { ...video, result_id: id } }
          : prev,
      );
      setVideoOpen(true);
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy((prev) => ({ ...prev, render: null }));
    }
  }
  const chosenNode =
    current && selected ? result.layouts[index]?.nodes[selected] : null;
  const complete = current && playback.step === steps.length;
  const explanation = complete ? (
    <>
      The derivation yields{" "}
      <code>{result.spec.input_tokens.join(" ") || "ε"}</code>. Every production
      is valid.
    </>
  ) : playback.step ? (
    <>
      <span className="mono">{steps[playback.step - 1].production}</span>
      <span className="explanation-separator">·</span>
      <span className="sentential-form">
        {steps[playback.step - 1].sentential_form}
      </span>
    </>
  ) : (
    <>
      Begin with the start symbol{" "}
      <code>{current ? result.spec.start : "E"}</code>. Reveal each production
      to follow the derivation.
    </>
  );
  return (
    <>
      <PageIntro
        eyebrow="02 / COMPILER DESIGN"
        title={
          <>
            Grammar <em>Lab.</em>
          </>
        }
        description="Find the structure beneath a string. Watch a derivation come together."
      >
        <Button variant="secondary" icon={Settings2} onClick={openSettings}>
          Configure
        </Button>
      </PageIntro>
      <div className="studio-layout">
        <section className="panel input-panel">
          <div className="studio-panel-title">
            <span className="step-dot violet">1</span>
            <h2>Define your grammar</h2>
            <GitBranch size={18} />
          </div>
          <label className="field-label">START WITH AN EXAMPLE</label>
          <div className="example-chips">
            {catalog?.cfg.map((e) => (
              <button
                key={e.id}
                className={e.grammar === form.grammar ? "selected" : ""}
                disabled={!!phase}
                onClick={() => {
                  patch({ grammar: e.grammar, input: e.input });
                  setError("");
                }}
              >
                {e.name === "Balanced a / b"
                  ? "Balanced aⁿbⁿ"
                  : e.name === "Ambiguous expression"
                    ? "Ambiguous"
                    : e.name}
              </button>
            ))}
          </div>
          <label className="field-label" htmlFor="grammar-editor">
            Context-free grammar <span>CFG</span>
          </label>
          <div className="code-editor">
            <div className="line-numbers" aria-hidden="true">
              {form.grammar.split("\n").map((_, i) => (
                <span key={i}>{i + 1}</span>
              ))}
            </div>
            <textarea
              id="grammar-editor"
              spellCheck="false"
              value={form.grammar}
              onChange={(e) => patch({ grammar: e.target.value })}
              disabled={!!phase}
              maxLength={12000}
              placeholder="S -> 'a' S 'b' |"
            />
          </div>
          <div className="syntax-help">
            <Code2 size={14} />
            <span>
              Quote terminals. Use <code>|</code> for alternatives.
              <br />A blank right-hand side means ε.
            </span>
          </div>
          <label className="field-label" htmlFor="grammar-input">
            Input tokens
          </label>
          <div className="text-input with-prefix">
            <Terminal size={16} />
            <input
              id="grammar-input"
              value={form.input}
              onChange={(e) => patch({ input: e.target.value })}
              disabled={!!phase}
              placeholder="id + id * id"
            />
          </div>
          <p className="field-help">
            Separate every token with a space. Blank input means ε.
          </p>
          <div className="parser-note">
            <span className="parser-note-icon">
              <GitBranch size={17} />
            </span>
            <div>
              <b>Earley parsing</b>
              <p>
                Handles general CFGs and discovers ambiguous derivations, within
                a bounded search.
              </p>
            </div>
          </div>
          {error && (
            <div className="form-error" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}
          <Button
            className="verify-button"
            icon={phase ? Loader2 : Sparkles}
            onClick={verify}
            disabled={!!blocked || !!phase}
          >
            {phase ? "Finding a derivation…" : "Parse & verify"}
            {!phase && <ArrowRight size={16} />}
          </Button>
          {blocked && <p className="action-help">{blocked}</p>}
          <div className="input-guarantee">
            <ShieldCheck size={13} />
            An independent checker validates each tree.
          </div>
        </section>
        <section className="panel canvas-panel">
          <div className="canvas-panel-head">
            <div>
              <span className="eyebrow">THE WORKSPACE</span>
              <h2>Derivation canvas</h2>
            </div>
            {current ? (
              <Outcome result={result} />
            ) : (
              <Badge icon={CircleDot}>
                {result ? "Needs a fresh check" : "Ready to explore"}
              </Badge>
            )}
          </div>
          {current && (
            <div className="tree-summary">
              <div>
                <Badge tone="violet" icon={GitBranch}>
                  {result.trees.length} tree
                  {result.trees.length === 1 ? "" : "s"} found
                  {result.truncated ? " · capped" : ""}
                </Badge>
                <span>
                  {result.trees.length > 1
                    ? "Explore alternative derivations."
                    : "A legal derivation, independently checked."}
                </span>
              </div>
              {result.trees.length > 1 && (
                <select
                  aria-label="Verified parse tree"
                  value={index}
                  onChange={(e) => {
                    patch({ treeIndex: Number(e.target.value) });
                    setSelected(null);
                  }}
                >
                  {result.trees.map((_, i) => (
                    <option key={i} value={i}>
                      Tree {i + 1} of {result.trees.length}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}
          <div className="canvas-body">
            {phase ? (
              <Progress phase={phase} mode="cfg" />
            ) : current ? (
              result.layouts[index] ? (
                <Diagram
                  key={`${result.id}-${index}`}
                  layout={result.layouts[index]}
                  steps={steps}
                  treeStep={playback.step}
                  onSelect={setSelected}
                  selected={selected}
                />
              ) : (
                <div className="visual-limit">
                  <GitBranch size={32} />
                  <h3>A derivation worth inspecting.</h3>
                  <p>{result.visual_errors[index]}</p>
                  <Badge tone="success" icon={ShieldCheck}>
                    Derivation verified
                  </Badge>
                </div>
              )
            ) : (
              <EmptyCanvas stale={!!result} cfg error={error} />
            )}
          </div>
          {current && (
            <>
              <Playback
                mode="cfg"
                playback={playback}
                count={steps.length}
                tokens={result.spec.input_tokens}
                explanation={explanation}
                completed={complete}
              />
              {chosenNode && (
                <div className="node-inspector">
                  <code>{chosenNode.symbol}</code>
                  <Badge tone={chosenNode.terminal ? "violet" : "neutral"}>
                    {chosenNode.terminal ? "Terminal" : "Nonterminal"}
                  </Badge>
                  <span className="mono">{chosenNode.node_id}</span>
                  <span>
                    {chosenNode.terminal
                      ? "A leaf in the terminal yield."
                      : `${chosenNode.symbol} → ${chosenNode.children.map((c) => c.symbol).join(" ") || "ε"}`}
                  </span>
                  <button
                    className="icon-button"
                    onClick={() => setSelected(null)}
                    aria-label="Close node inspector"
                  >
                    <X size={13} />
                  </button>
                </div>
              )}
              <SourceLine result={result} />
            </>
          )}
          <div className="canvas-export-bar">
            <span>
              <ShieldCheck size={14} />
              {current
                ? "The checked derivation powers every frame."
                : "Verify a derivation to unlock animation."}
            </span>
            <Button
              variant="secondary"
              icon={renderPhase ? Loader2 : videoReady ? Play : Download}
              disabled={
                !current ||
                !result.renderable ||
                !!result.visual_errors[index] ||
                !!busy.render
              }
              onClick={exportVideo}
            >
              {renderPhase
                ? "Rendering…"
                : videoReady
                  ? "View video"
                  : "Export animation"}
            </Button>
          </div>
          {renderPhase && (
            <div className="render-progress" role="status">
              <Loader2 size={15} />
              Rendering the checked derivation with Manim.
            </div>
          )}
        </section>
      </div>
      {current && <CfgEvidence result={result} index={index} />}
      <div className="scope-note">
        <Info size={15} />
        <p>
          <b>What’s verified?</b> The root, each production, and the exact
          terminal yield of this derivation. Bounded tree enumeration does not
          prove that a grammar is unambiguous.
        </p>
      </div>
      {videoOpen && videoReady && (
        <VideoModal
          video={form.video}
          result={result}
          onClose={() => setVideoOpen(false)}
        />
      )}
    </>
  );
}

function EvidencePanel({ tabs, result, children }) {
  const [tab, setTab] = useState(tabs[0]);
  return (
    <section className="panel evidence-panel">
      <div className="evidence-header">
        <div
          className="evidence-tabs"
          role="tablist"
          aria-label="Verification details"
        >
          {tabs.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              tabIndex={tab === t ? 0 : -1}
              onClick={() => setTab(t)}
              onKeyDown={(event) => {
                if (
                  !["ArrowRight", "ArrowLeft", "Home", "End"].includes(
                    event.key,
                  )
                )
                  return;
                event.preventDefault();
                const i = tabs.indexOf(t);
                const next =
                  event.key === "Home"
                    ? 0
                    : event.key === "End"
                      ? tabs.length - 1
                      : (i +
                          (event.key === "ArrowRight" ? 1 : -1) +
                          tabs.length) %
                        tabs.length;
                setTab(tabs[next]);
                event.currentTarget.parentElement
                  .querySelectorAll('[role="tab"]')
                  [next].focus();
              }}
              className={tab === t ? "active" : ""}
            >
              {t}
            </button>
          ))}
        </div>
        <button
          className="evidence-download"
          aria-label="Download verification evidence"
          onClick={() => downloadJSON(result)}
        >
          <Download size={14} />
          <span>Download evidence</span>
        </button>
      </div>
      <div className="evidence-body" role="tabpanel" aria-label={tab}>
        {children(tab)}
      </div>
    </section>
  );
}
function DfaTable({ dfa }) {
  if (!dfa) return <p className="muted">No candidate was produced.</p>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>STATE</th>
            <th>ROLE</th>
            {dfa.alphabet.map((a) => (
              <th key={a}>READ {a}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dfa.states.map((s) => (
            <tr key={s}>
              <td>
                <StateTag state={s} dfa={dfa} />
              </td>
              <td>
                <span className="table-role">
                  {s === dfa.start_state ? "Initial · " : ""}
                  {dfa.accept_states.includes(s)
                    ? "Accepting"
                    : "Non-accepting"}
                </span>
              </td>
              {dfa.alphabet.map((a) => (
                <td key={a}>
                  <StateTag
                    small
                    state={dfa.transitions[s]?.[a] || "Missing"}
                    dfa={dfa}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function DfaEvidence({ result }) {
  const [tableView, setTableView] = useState("minimal");
  const candidate =
    tableView === "first"
      ? result.attempted_candidates[0]
      : tableView === "last"
        ? result.candidate
        : result.minimised_candidate || result.attempted_candidates[0];
  return (
    <EvidencePanel
      result={result}
      tabs={[
        "Verification",
        "Transition table",
        "Execution trace",
        "Candidate history",
      ]}
    >
      {(tab) =>
        tab === "Verification" ? (
          <div className="verification-content">
            <div className="verification-summary">
              <span
                className={`verification-symbol ${result.verified ? "success" : ""}`}
              >
                {result.verified ? (
                  <ShieldCheck size={25} />
                ) : (
                  <ShieldX size={25} />
                )}
              </span>
              <div>
                <h3>
                  {result.verified
                    ? "The language checks out."
                    : result.status === "REFERENCE_UNAVAILABLE"
                      ? "Structure checked. Meaning unverified."
                      : "Review the verification result."}
                </h3>
                <p>{result.reports.at(-1).message}</p>
                <span className="verification-provenance">
                  REFERENCE <b>{result.provenance || "Not supplied"}</b>
                </span>
              </div>
            </div>
            <div className="check-list">
              {result.reports.at(-1).checks.map((c, i) => (
                <div key={c}>
                  {result.verified ? (
                    <Check size={15} />
                  ) : (
                    <CircleDot size={14} />
                  )}
                  <span>{c}</span>
                  <span className="check-index">0{i + 1}</span>
                </div>
              ))}
            </div>
          </div>
        ) : tab === "Transition table" ? (
          <>
            <div className="evidence-subhead">
              <p>Inspect the prediction and its minimised structure.</p>
              <select
                aria-label="Transition table version"
                value={tableView}
                onChange={(e) => setTableView(e.target.value)}
              >
                <option value="first">First prediction</option>
                <option value="last">Last checked candidate</option>
                {result.minimised_candidate && (
                  <option value="minimal">Minimised candidate</option>
                )}
              </select>
            </div>
            <DfaTable dfa={candidate} />
          </>
        ) : tab === "Execution trace" ? (
          result.trace ? (
            <>
              <div className="trace-overview">
                <span>
                  INITIAL{" "}
                  <StateTag
                    small
                    state={result.trace.initial_state}
                    dfa={result.dfa}
                  />
                </span>
                <span>
                  FINAL{" "}
                  <StateTag
                    small
                    state={result.trace.final_state}
                    dfa={result.dfa}
                  />
                </span>
                <Badge tone={result.trace.accepted ? "success" : "neutral"}>
                  {result.trace.accepted ? "ACCEPT" : "REJECT"}
                </Badge>
              </div>
              {result.trace.steps.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>STEP</th>
                        <th>FROM</th>
                        <th>SYMBOL</th>
                        <th>TO</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.trace.steps.map((s) => (
                        <tr key={s.position}>
                          <td className="mono">
                            {String(s.position + 1).padStart(2, "0")}
                          </td>
                          <td>
                            <StateTag state={s.source} dfa={result.dfa} />
                          </td>
                          <td>
                            <code className="symbol-cell">{s.symbol}</code>
                          </td>
                          <td>
                            <StateTag state={s.destination} dfa={result.dfa} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="muted">Empty input: no transitions are taken.</p>
              )}
            </>
          ) : (
            <div className="evidence-empty">
              <ShieldCheck size={22} />
              <p>
                A verified execution trace is available after exact equivalence
                passes.
              </p>
            </div>
          )
        ) : (
          <div className="candidate-list">
            {result.reports.map((r, i) => (
              <details key={i}>
                <summary>
                  <span className="candidate-number">
                    {String(r.attempt).padStart(2, "0")}
                  </span>
                  <div>
                    <b>{r.status.replaceAll("_", " ")}</b>
                    <small>
                      {r.counterexample != null
                        ? `Counterexample: ${r.counterexample.join("") || "ε"}`
                        : r.message}
                    </small>
                  </div>
                  <span className="mono">
                    {(r.elapsed_seconds * 1000).toFixed(1)} ms
                  </span>
                  <ChevronDown size={15} />
                </summary>
                {result.attempted_candidates[i] && (
                  <pre className="json-block">
                    {JSON.stringify(result.attempted_candidates[i], null, 2)}
                  </pre>
                )}
              </details>
            ))}
          </div>
        )
      }
    </EvidencePanel>
  );
}
function CfgEvidence({ result, index }) {
  return (
    <EvidencePanel
      result={{ ...result, selected_tree: index }}
      tabs={[
        "Verification",
        "Grammar & tree",
        "Derivation steps",
        "Parse details",
      ]}
    >
      {(tab) =>
        tab === "Verification" ? (
          <div className="verification-content">
            <div className="verification-summary">
              <span className="verification-symbol success">
                <ShieldCheck size={25} />
              </span>
              <div>
                <h3>A valid derivation, independently checked.</h3>
                <p>
                  Each expansion belongs to your grammar and the leaves
                  reproduce the exact input.
                </p>
                <span className="verification-provenance">
                  SCOPE <b>Selected derivation · Tree {index + 1}</b>
                </span>
              </div>
            </div>
            <div className="check-list">
              {[
                "Root matches the start symbol",
                "Every production belongs to the grammar",
                "Terminal yield equals the supplied input",
                "Stable node IDs are unique",
              ].map((c, i) => (
                <div key={c}>
                  <Check size={15} />
                  <span>{c}</span>
                  <span className="check-index">0{i + 1}</span>
                </div>
              ))}
            </div>
          </div>
        ) : tab === "Grammar & tree" ? (
          <div className="grammar-evidence">
            <div>
              <span className="eyebrow">SUPPLIED GRAMMAR</span>
              <pre className="grammar-code">{result.grammar}</pre>
              <p className="muted">
                Start symbol: <code>{result.spec.start}</code>
              </p>
            </div>
            <details>
              <summary>
                Selected tree JSON <ChevronDown size={14} />
              </summary>
              <pre className="json-block">
                {JSON.stringify(result.trees[index], null, 2)}
              </pre>
            </details>
          </div>
        ) : tab === "Derivation steps" ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>STEP</th>
                  <th>PRODUCTION</th>
                  <th>SENTENTIAL FORM</th>
                  <th>NODE</th>
                </tr>
              </thead>
              <tbody>
                {result.steps[index].map((s, i) => (
                  <tr key={s.node_id}>
                    <td className="mono">{String(i + 1).padStart(2, "0")}</td>
                    <td className="mono">{s.production}</td>
                    <td className="mono">{s.sentential_form}</td>
                    <td>
                      <code>{s.node_id}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="parse-details">
            <div>
              <span>TREES FOUND</span>
              <b>{result.trees.length}</b>
            </div>
            <div>
              <span>ENUMERATION</span>
              <b>{result.truncated ? "Capped" : "Completed"}</b>
            </div>
            <div>
              <span>INPUT TOKENS</span>
              <b>{result.spec.input_tokens.length}</b>
            </div>
            <div>
              <span>PARSE & CHECK</span>
              <b>{Math.round(result.elapsed_seconds * 1000)} ms</b>
            </div>
            <p>
              <Info size={15} />
              Finding one tree does not prove that a grammar is unambiguous.
              Enumeration is bounded by your configured limit.
            </p>
          </div>
        )
      }
    </EvidencePanel>
  );
}
function VideoModal({ video, result, onClose }) {
  return (
    <Modal title="Your theory, in motion." wide onClose={onClose}>
      <div className="video-meta">
        <Outcome result={result} />
        <span>
          {video.quality === "high" ? "1080p · 60 fps" : "480p · 15 fps"} ·
          Manim
        </span>
      </div>
      <video
        className="export-video"
        src={video.url}
        controls
        preload="auto"
        aria-label="Manim animation of the independently verified execution"
      />
      <p className="video-source">
        {result.source}. The animation follows the same checked trace shown in
        your workspace.
      </p>
      <div className="modal-footer">
        <span>
          {video.cache_hit
            ? "Retrieved from the local render cache"
            : `Rendered locally in ${video.seconds.toFixed(1)} seconds`}
        </span>
        <a
          className="button button-primary"
          href={video.url}
          download="theorybert-animation.mp4"
        >
          <Download size={16} />
          Download MP4
        </a>
      </div>
    </Modal>
  );
}

function Examples({ catalog, openExample }) {
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState("All examples");
  const examples = [
    ...(catalog?.dfa || []).map((e) => ({
      ...e,
      mode: "dfa",
      detail: e.description,
    })),
    ...(catalog?.cfg || []).map((e) => ({
      ...e,
      mode: "cfg",
      detail:
        e.name === "Arithmetic"
          ? "Explore operator precedence with an unambiguous expression grammar."
          : e.name === "Balanced a / b"
            ? "See the recursive structure behind balanced aⁿbⁿ strings."
            : "One expression, multiple derivations. Compare verified parse trees.",
    })),
  ];
  const visible = examples.filter(
    (e) =>
      (filter === "All examples" ||
        (filter === "Automata" ? e.mode === "dfa" : e.mode === "cfg")) &&
      `${e.name} ${e.detail}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <PageIntro
        eyebrow="A STARTING POINT FOR CURIOSITY"
        title={
          <>
            Example <em>Library.</em>
          </>
        }
        description="Small languages. Big ideas. Open an example and make it your own."
      />
      <div className="library-toolbar">
        <div className="filter-tabs" aria-label="Example category">
          {["All examples", "Automata", "Grammars"].map((f) => (
            <button
              key={f}
              className={filter === f ? "active" : ""}
              onClick={() => setFilter(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <div className="search-input">
          <Search size={16} />
          <input
            aria-label="Search examples"
            placeholder="Find an example…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              className="icon-button"
              aria-label="Clear search"
              onClick={() => setSearch("")}
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="example-grid">
        {visible.map((e, i) => (
          <motion.article
            key={e.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.045, 0.25) }}
            className="example-card"
          >
            <div
              className={`example-card-visual ${e.mode === "cfg" ? "violet-visual" : ""}`}
            >
              <span className="example-number">
                {String(examples.indexOf(e) + 1).padStart(2, "0")} /{" "}
                {e.mode === "dfa" ? "AUTOMATON" : "GRAMMAR"}
              </span>
              {e.mode === "dfa" ? (
                e.preview ? (
                  <Diagram
                    compact
                    graph={e.preview.graph}
                    dfa={e.preview.dfa}
                  />
                ) : (
                  <Network size={40} />
                )
              ) : (
                <div className="sample-grammar">
                  <span>{e.grammar.split("\n")[0].replaceAll("'", "")}</span>
                  <small>{e.input}</small>
                </div>
              )}
            </div>
            <div className="example-card-copy">
              <Badge tone={e.mode === "dfa" ? "blue" : "violet"}>
                {e.mode === "dfa" ? "DFA STUDIO" : "GRAMMAR LAB"}
              </Badge>
              <h2>{e.name}</h2>
              <p>{e.detail}</p>
              <div className="example-attributes">
                <span>
                  <ShieldCheck size={12} />
                  {e.mode === "dfa"
                    ? "Reference included"
                    : "Independent tree check"}
                </span>
                <span>
                  {e.mode === "dfa" ? "Binary alphabet" : "Earley parser"}
                </span>
              </div>
              <button onClick={() => openExample(e, e.mode)}>
                Open in {e.mode === "dfa" ? "Studio" : "Lab"}{" "}
                <ArrowUpRight size={17} />
              </button>
            </div>
          </motion.article>
        ))}
      </div>
      {!visible.length && (
        <div className="search-empty">
          <Search size={27} />
          <h3>No examples found.</h3>
          <p>Try “binary”, “arithmetic”, or clear the filters.</p>
          <Button
            variant="secondary"
            onClick={() => {
              setSearch("");
              setFilter("All examples");
            }}
          >
            Reset filters
          </Button>
        </div>
      )}
      <div className="library-note">
        <Lightbulb size={20} />
        <div>
          <b>An example is a starting point.</b>
          <p>
            Edit the description, change the test string, or try a different
            grammar. The workspace checks each new request independently.
          </p>
        </div>
        <Link to="/dfa" className="text-link">
          Start exploring <ArrowRight size={15} />
        </Link>
      </div>
    </>
  );
}

function Research() {
  const [data, setData] = useState(null),
    [error, setError] = useState("");
  useEffect(() => {
    api("/research")
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);
  const baseline = data?.baseline?.semantic,
    structural = data?.baseline?.structural;
  const percentage = (value) =>
    value == null ? "—" : `${(value * 100).toFixed(0)}%`;
  return (
    <>
      <PageIntro
        eyebrow="THE RESEARCH NOTEBOOK"
        title={
          <>
            Evidence over <em>estimates.</em>
          </>
        }
        description="A transparent view of the models, measurements, and experiments behind the workspace."
      />
      <div className="research-banner">
        <div className="research-banner-icon">
          <FlaskConical size={24} />
        </div>
        <div>
          <h2>A working prototype. An open research question.</h2>
          <p>
            TheoryBERT studies vocabulary extension and embedding initialisation
            with a frozen BERT backbone. The 70% equivalence goal is a research
            target; full pretrained experiments have not been run.
          </p>
        </div>
        <Badge tone="blue">RESEARCH IN PROGRESS</Badge>
      </div>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <div className="research-grid">
        <section className="panel measurement-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">MEASURED BASELINE</span>
              <h2>How often does the language match?</h2>
            </div>
            <Badge icon={Check}>ACTUALLY EXECUTED</Badge>
          </div>
          <p className="muted">
            Limited rule-based predictor · shipped held-out test split
          </p>
          <div className="big-metric">
            <b>{percentage(baseline?.raw_equivalence)}</b>
            <span>
              exact language equivalence
              <br />
              <small>
                {baseline
                  ? `${Math.round(baseline.examples * baseline.raw_equivalence)} of ${baseline.examples} semantic descriptions`
                  : "Not measured"}
              </small>
            </span>
          </div>
          <div
            className="accuracy-bar"
            aria-label={`Measured rule baseline equivalence ${percentage(baseline?.raw_equivalence)}`}
          >
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(baseline?.raw_equivalence || 0) * 100}%` }}
              transition={{ duration: 0.8 }}
            />
            <span style={{ left: "70%" }}>
              <i />
              <small>70% research target</small>
            </span>
          </div>
          <div className="metric-pairs">
            <div>
              <span>Support coverage</span>
              <b>{percentage(baseline?.supported)}</b>
            </div>
            <div>
              <span>Release coverage</span>
              <b>{percentage(baseline?.released)}</b>
            </div>
            <div>
              <span>Incorrect releases</span>
              <b>{baseline?.incorrect_candidates_released ?? "—"}</b>
            </div>
          </div>
          <p className="measurement-note">
            <Info size={14} />
            The gate uses the evaluation reference. Correctness of released
            outputs reflects the checker, not independent model accuracy.
          </p>
          {structural && (
            <div className="structural-note">
              <span>Structural reconstruction</span>
              <b>{percentage(structural.raw_equivalence)}</b>
              <small>
                {structural.examples} test description · unsupported by this
                baseline
              </small>
            </div>
          )}
        </section>
        <section className="panel architecture-panel">
          <span className="eyebrow">THE LEARNED PATH</span>
          <h2>
            English in.
            <br />
            Structure out.
          </h2>
          <div className="architecture-flow">
            {[
              {
                icon: BookOpen,
                title: "Language description",
                sub: "English + domain notation",
              },
              {
                icon: Layers3,
                title: "Frozen BERT backbone",
                sub: "Trainable vocabulary & contextual extension",
              },
              {
                icon: Network,
                title: "Structured DFA heads",
                sub: "State count · accepting bits · transitions",
              },
              {
                icon: ShieldCheck,
                title: "Independent verification",
                sub: "Exact equivalence before animation",
              },
            ].map(({ icon: Icon, title, sub }, i) => (
              <React.Fragment key={title}>
                <div>
                  <span>
                    <Icon size={17} />
                  </span>
                  <section>
                    <b>{title}</b>
                    <small>{sub}</small>
                  </section>
                </div>
                {i < 3 && <i className="flow-connector" />}
              </React.Fragment>
            ))}
          </div>
          <Badge tone="warning" icon={Info}>
            No trained pretrained checkpoint yet
          </Badge>
        </section>
      </div>
      <section className="panel experiments-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">INITIALISATION STUDY</span>
            <h2>The experiment ledger</h2>
          </div>
          <span className="muted">Seeds 13, 42, 123</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>VARIANT</th>
                <th>NEW TOKEN INITIALISATION</th>
                <th>COMPLETED SEEDS</th>
                <th>SEMANTIC MEAN ± SD</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Vanilla BERT", "Original vocabulary", "vanilla", "none"],
                [
                  "TheoryBERT",
                  "Random · scaled normal",
                  "theorybert",
                  "random",
                ],
                [
                  "TheoryBERT",
                  "Mean of original subwords",
                  "theorybert",
                  "subword_mean",
                ],
                [
                  "TheoryBERT",
                  "Subword mean + 1.0 per coordinate",
                  "theorybert",
                  "subword_mean_plus_one",
                ],
              ].map(([name, strategy, variant, initialisation]) => {
                const row = data?.ablations?.find(
                  (r) =>
                    r.variant === variant &&
                    r.initialisation === initialisation &&
                    r.category === "semantic",
                );
                return (
                  <tr key={strategy}>
                    <td>
                      <b>{name}</b>
                    </td>
                    <td>{strategy}</td>
                    <td className="mono">{row?.completed || 0} / 3</td>
                    <td className="mono">
                      {row?.mean == null
                        ? "—"
                        : `${percentage(row.mean)} ± ${row.std == null ? "—" : percentage(row.std)}`}
                    </td>
                    <td>
                      <Badge tone={row?.completed ? "success" : "neutral"}>
                        {row?.completed ? "Measured" : "Not run"}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="table-footnote">
          Only completed runs enter aggregates. Plus-one is a literal
          experimental condition, not an assumed improvement. DistilBERT is a
          separate configuration.
        </p>
      </section>
      <div className="research-lower">
        <section className="panel environment-panel">
          <div className="panel-heading">
            <h3>
              <Monitor size={17} />
              Local environment
            </h3>
            <Badge tone="success">
              {data?.environment?.minimal_text_render === "passed"
                ? "Manim render verified"
                : "Environment report"}
            </Badge>
          </div>
          <div className="environment-grid">
            {[
              ["Python", data?.environment?.python?.split(" ")[0]],
              ["PyTorch", data?.environment?.torch],
              ["Transformers", data?.environment?.transformers],
              ["Manim", data?.environment?.manim],
            ].map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <code>{value || "—"}</code>
              </div>
            ))}
          </div>
          <p>
            <span className="connection-dot" />
            {data?.environment?.compute?.mps
              ? "Apple MPS available"
              : "CPU execution"}{" "}
            · smoke validation ran on CPU
          </p>
        </section>
        <section className="panel smoke-panel">
          <div className="panel-heading">
            <h3>
              <CheckCheck size={17} />
              Training mechanics
            </h3>
            <Badge
              tone={
                data?.smoke?.smoke_update_and_reload_checks
                  ? "success"
                  : "neutral"
              }
            >
              {data?.smoke?.smoke_update_and_reload_checks
                ? "Passed"
                : "Not measured"}
            </Badge>
          </div>
          <p>
            A tiny random BERT exercises real forward, loss, backward,
            optimiser, and checkpoint reload passes.
          </p>
          <div>
            <span>
              {data?.smoke?.smoke_update_and_reload_checks ? (
                <Check size={14} />
              ) : (
                <CircleDot size={14} />
              )}
              Frozen original weights
            </span>
            <span>
              {data?.smoke?.smoke_update_and_reload_checks ? (
                <Check size={14} />
              ) : (
                <CircleDot size={14} />
              )}
              Trainable extensions
            </span>
            <span>
              {data?.smoke?.smoke_update_and_reload_checks ? (
                <Check size={14} />
              ) : (
                <CircleDot size={14} />
              )}
              Prediction-preserving reload
            </span>
          </div>
          <small>
            Mechanics validation only. This is not research accuracy.
          </small>
        </section>
      </div>
    </>
  );
}

function SettingsModal({ settings, setSettings, catalog, onClose }) {
  const patch = (values) =>
    setSettings((previous) => ({ ...previous, ...values }));
  return (
    <Modal title="Make this workspace yours." onClose={onClose}>
      <div className="settings-section">
        <span className="settings-section-icon">
          <Layers3 size={18} />
        </span>
        <div>
          <h3>Model & inference</h3>
          <p>A trained checkpoint enables direct learned DFA prediction.</p>
        </div>
      </div>
      <label className="field-label" htmlFor="checkpoint-path">
        Local checkpoint directory
      </label>
      <input
        id="checkpoint-path"
        className="text-input standalone mono"
        placeholder="artifacts/theorybert/best"
        value={settings.checkpoint}
        onChange={(e) => patch({ checkpoint: e.target.value })}
      />
      {catalog?.checkpoints.length > 0 && (
        <div className="checkpoint-options">
          {catalog.checkpoints.map((cp) => (
            <button
              key={cp.path}
              className={settings.checkpoint === cp.path ? "selected" : ""}
              onClick={() => patch({ checkpoint: cp.path })}
            >
              <span className="checkpoint-icon">
                <Layers3 size={16} />
              </span>
              <span>
                <b>{cp.path}</b>
                <small>
                  {cp.backbone} · {cp.variant}
                </small>
              </span>
              <Badge tone={cp.status.includes("smoke") ? "warning" : "neutral"}>
                {cp.status.includes("smoke") ? "Smoke only" : "Checkpoint"}
              </Badge>
              {settings.checkpoint === cp.path && <Check size={15} />}
            </button>
          ))}
        </div>
      )}
      <div className="settings-two">
        <div>
          <label className="field-label" htmlFor="candidate-budget">
            Candidate budget
          </label>
          <input
            id="candidate-budget"
            className="text-input standalone"
            type="number"
            min="1"
            max="16"
            value={settings.budget}
            onChange={(e) =>
              patch({
                budget: Math.max(1, Math.min(16, Number(e.target.value))),
              })
            }
          />
          <p className="field-help">Bounded, deduplicated alternatives.</p>
        </div>
        <div>
          <label className="field-label" htmlFor="tree-limit">
            Maximum parse trees
          </label>
          <input
            id="tree-limit"
            className="text-input standalone"
            type="number"
            min="1"
            max="10"
            value={settings.parseLimit}
            onChange={(e) =>
              patch({
                parseLimit: Math.max(1, Math.min(10, Number(e.target.value))),
              })
            }
          />
          <p className="field-help">Safe, bounded tree enumeration.</p>
        </div>
      </div>
      <div className="settings-section rendering-settings">
        <span className="settings-section-icon">
          <Play size={18} />
        </span>
        <div>
          <h3>Animation export</h3>
          <p>Choose the balance between rendering speed and detail.</p>
        </div>
      </div>
      <div className="quality-options">
        {[
          {
            value: "preview",
            name: "Quick preview",
            specs: "480p · 15 fps",
            note: "Ideal for exploring",
          },
          {
            value: "high",
            name: "Presentation",
            specs: "1080p · 60 fps",
            note: "More detail, longer render",
          },
        ].map((q) => (
          <button
            key={q.value}
            className={settings.quality === q.value ? "selected" : ""}
            onClick={() => patch({ quality: q.value })}
          >
            <span className="quality-radio">
              {settings.quality === q.value && <i />}
            </span>
            <b>{q.name}</b>
            <code>{q.specs}</code>
            <small>{q.note}</small>
          </button>
        ))}
      </div>
      <div className="settings-notice">
        <Info size={15} />
        <p>
          Settings save locally. Model and verification changes mark existing
          results as outdated. Export quality never retrains a model.
        </p>
      </div>
      <div className="modal-footer">
        <span>
          <Monitor size={14} />
          Stored on this device
        </span>
        <Button icon={Check} onClick={onClose}>
          Done
        </Button>
      </div>
    </Modal>
  );
}
function Guide({ onClose, catalog }) {
  return (
    <Modal title="A few things worth knowing." onClose={onClose}>
      <div className="guide-intro">
        <GraduationCap size={25} />
        <p>
          TheoryBERT turns formal structures into something you can explore.
          Here’s how to get started.
        </p>
      </div>
      <div className="guide-steps">
        {[
          {
            n: "01",
            title: "Start with a small example",
            text: "Open DFA Studio or Grammar Lab. Example inputs include everything you need for a first exploration.",
          },
          {
            n: "02",
            title: "Check before you play",
            text: "DFA verification compares two independent formal machines. Grammar verification checks one legal derivation of your exact tokens.",
          },
          {
            n: "03",
            title: "Slow the theory down",
            text: "Play the canvas, step in either direction, zoom into a branch, or select a state to inspect it.",
          },
          {
            n: "04",
            title: "Keep the evidence",
            text: "Export the checked trace as a Manim video, or download the complete verification evidence as JSON.",
          },
        ].map((s) => (
          <div key={s.n}>
            <span>{s.n}</span>
            <section>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
            </section>
          </div>
        ))}
      </div>
      <div className="guide-boundary">
        <ShieldCheck size={20} />
        <p>
          <b>A clear boundary, always.</b> Reference demonstrations are
          labelled. Learned inference requires a checkpoint. An unverified
          candidate cannot be animated.
        </p>
      </div>
      <div className="modal-footer">
        <span>All core processing runs locally.</span>
        <Button onClick={onClose}>
          Let’s explore <ArrowRight size={16} />
        </Button>
      </div>
    </Modal>
  );
}
