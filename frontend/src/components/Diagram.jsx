import { useEffect, useId, useRef, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import {
  Maximize2,
  Minimize2,
  Minus,
  Plus,
  RotateCcw,
  Move,
} from "lucide-react";

export const stateColors = [
  "#d03676",
  "#7651bf",
  "#237b91",
  "#5c637d",
  "#8c5895",
  "#497584",
  "#af4e7d",
  "#6f65a8",
];
export function stateColor(dfa, state) {
  return stateColors[
    Math.max(0, dfa?.states.indexOf(state) ?? 0) % stateColors.length
  ];
}
const point = ([x, y]) => [x * 82, -y * 82];

export function StateTag({ state, dfa, small = false }) {
  return (
    <span
      className={`state-tag ${small ? "small" : ""}`}
      style={{ "--state-color": stateColor(dfa, state) }}
    >
      <span />
      {state}
    </span>
  );
}

export default function Diagram({
  graph,
  dfa,
  active,
  transition,
  layout,
  treeStep = 0,
  steps = [],
  onSelect,
  selected,
  className = "",
  compact = false,
  verified = true,
  treeKind = "parse",
}) {
  const uid = useId().replaceAll(":", "");
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState([0, 0]);
  const [expanded, setExpanded] = useState(false);
  const pointer = useRef(null);
  const svgRef = useRef(null);
  const wrapperRef = useRef(null);
  useEffect(() => {
    if (!expanded) return;
    const previous = document.activeElement;
    const element = wrapperRef.current;
    element.querySelector("button")?.focus();
    const keys = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setExpanded(false);
      }
      if (event.key !== "Tab") return;
      const controls = [
        ...element.querySelectorAll('button:not(:disabled), [tabindex="0"]'),
      ];
      if (event.shiftKey && document.activeElement === controls[0]) {
        event.preventDefault();
        controls.at(-1)?.focus();
      } else if (
        !event.shiftKey &&
        document.activeElement === controls.at(-1)
      ) {
        event.preventDefault();
        controls[0]?.focus();
      }
    };
    document.addEventListener("keydown", keys);
    return () => {
      document.removeEventListener("keydown", keys);
      if (previous?.isConnected) previous.focus();
    };
  }, [expanded]);
  const reduced = useReducedMotion();
  const isTree = !!layout;
  const coordinates = isTree
    ? Object.values(layout.positions).map(([x, y]) => [x * 68, -y * 72])
    : [
        ...Object.values(graph?.nodes || {}).map(point),
        ...(graph?.edges || []).flatMap((e) =>
          ["c1", "c2", "label"].map((k) => point(e[k])),
        ),
      ];
  const xs = coordinates.map((p) => p[0]),
    ys = coordinates.map((p) => p[1]);
  const minx = Math.min(...xs, -60) - 65,
    miny = Math.min(...ys, -50) - 64;
  const w = Math.max(260, Math.max(...xs, 60) + 65 - minx);
  const h = Math.max(200, Math.max(...ys, 50) + 90 - miny);
  const box = [
    minx + w / 2 - w / zoom / 2 - pan[0],
    miny + h / 2 - h / zoom / 2 - pan[1],
    w / zoom,
    h / zoom,
  ].join(" ");
  const visibleNodes = new Set(
    isTree
      ? [
          Object.keys(layout.nodes)[0],
          ...steps.slice(0, treeStep).flatMap((s) => s.children),
        ]
      : [],
  );
  const currentProduction = treeKind !== "ast" && treeStep > 0 ? steps[treeStep - 1]?.node_id : null;
  const reset = () => {
    setZoom(1);
    setPan([0, 0]);
  };
  function drag(event) {
    if (!pointer.current) return;
    const [x, y, px, py] = pointer.current;
    const rect = svgRef.current.getBoundingClientRect();
    setPan([
      px + ((event.clientX - x) * w) / rect.width / zoom,
      py + ((event.clientY - y) * h) / rect.height / zoom,
    ]);
  }
  const treePoint = (id) => {
    const [x, y] = layout.positions[id];
    return [x * 68, -y * 72];
  };
  const choose = (event, name) => {
    event.stopPropagation();
    onSelect?.(name);
  };
  return (
    <div
      ref={wrapperRef}
      role={expanded ? "dialog" : undefined}
      aria-modal={expanded ? true : undefined}
      aria-label={expanded ? "Expanded diagram" : undefined}
      className={`diagram ${expanded ? "diagram-expanded" : ""} ${compact ? "diagram-compact" : ""} ${className}`}
    >
      {!compact && (
        <div className="diagram-toolbar">
          <span className="diagram-hint">
            <Move size={12} /> Drag to pan
          </span>
          <div className="canvas-tools" aria-label="Diagram controls">
            <button
              className="icon-button"
              aria-label="Zoom out"
              disabled={zoom <= 0.7}
              onClick={() => setZoom((z) => Math.max(0.7, z - 0.25))}
            >
              <Minus size={15} />
            </button>
            <span className="zoom-value">{Math.round(zoom * 100)}%</span>
            <button
              className="icon-button"
              aria-label="Zoom in"
              disabled={zoom >= 3}
              onClick={() => setZoom((z) => Math.min(3, z + 0.25))}
            >
              <Plus size={15} />
            </button>
            <span className="tool-divider" />
            <button
              className="icon-button"
              aria-label="Reset diagram view"
              onClick={reset}
            >
              <RotateCcw size={14} />
            </button>
            <button
              className="icon-button"
              aria-label={
                expanded ? "Close expanded diagram" : "Expand diagram"
              }
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
          </div>
        </div>
      )}
      <svg
        ref={svgRef}
        className="graph-svg"
        viewBox={box}
        role={compact ? "img" : "group"}
        aria-label={
          compact
            ? "Reference automaton preview; double rings indicate accepting states."
            : isTree
              ? treeKind === "ast" ? "Abstract syntax tree; operators connect to their operands." : "Verified parse tree; purple leaves are terminals. Select a node to inspect its production."
              : `${verified ? "Verified automaton" : "Structurally checked automaton; language equivalence unverified"}. ${dfa?.states.length} states. Active state ${active}. Double rings mark accepting states.`
        }
        onPointerDown={(e) => {
          if (e.target.closest("[data-node]")) return;
          pointer.current = [e.clientX, e.clientY, ...pan];
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={drag}
        onPointerUp={() => {
          pointer.current = null;
        }}
        onPointerCancel={() => {
          pointer.current = null;
        }}
      >
        <defs>
          <marker
            id={`${uid}-arrow`}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerUnits="userSpaceOnUse"
            markerWidth="10"
            markerHeight="10"
            orient="auto"
          >
            <path d="M0 0L10 5L0 10" fill="#a598ac" />
          </marker>
          <marker
            id={`${uid}-active`}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerUnits="userSpaceOnUse"
            markerWidth="11"
            markerHeight="11"
            orient="auto"
          >
            <path d="M0 0L10 5L0 10" fill="#d03676" />
          </marker>
          <filter
            id={`${uid}-shadow`}
            x="-50%"
            y="-50%"
            width="200%"
            height="200%"
          >
            <feDropShadow
              dx="0"
              dy="4"
              stdDeviation="6"
              floodColor="#d03676"
              floodOpacity=".15"
            />
          </filter>
        </defs>
        {!isTree &&
          graph?.edges.map((e, i) => {
            const [start, c1, c2, end, label] = [
              "start",
              "c1",
              "c2",
              "end",
              "label",
            ].map((k) => point(e[k]));
            const highlighted =
              transition?.source === e.source &&
              e.symbols.includes(transition?.symbol);
            const path = `M${start} C${c1} ${c2} ${end}`;
            const labelText = e.symbols.join(", ");
            return (
              <g key={i}>
                <title>{`${e.source} → ${e.target} on ${e.symbols.join(", ")}`}</title>
                <path
                  d={path}
                  fill="none"
                  stroke={highlighted ? "#d03676" : "#a598ac"}
                  strokeWidth={highlighted ? 3.2 : 1.6}
                  markerEnd={`url(#${uid}-${highlighted ? "active" : "arrow"})`}
                />
                {highlighted && !reduced && (
                  <motion.path
                    d={path}
                    fill="none"
                    stroke="#efb2cc"
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeDasharray="9 26"
                    animate={{ strokeDashoffset: [0, -70] }}
                    transition={{
                      duration: 1.7,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  />
                )}
                <rect
                  x={label[0] - (labelText.length * 5 + 10)}
                  y={label[1] - 14}
                  width={labelText.length * 10 + 20}
                  height="28"
                  rx="8"
                  fill={highlighted ? "#fbe8f1" : "#fdfcfd"}
                />
                <text
                  x={label[0]}
                  y={label[1] + 6}
                  textAnchor="middle"
                  className="graph-edge-label"
                  fill={highlighted ? "#d03676" : "#74677e"}
                >
                  {labelText}
                </text>
              </g>
            );
          })}
        {!isTree &&
          dfa?.states.map((state, i) => {
            const [x, y] = point(graph.nodes[state]);
            const isActive = state === active,
              accepting = dfa.accept_states.includes(state),
              color = stateColors[i % stateColors.length];
            return (
              <g
                key={state}
                data-node="true"
                role={compact ? undefined : "button"}
                tabIndex={compact ? undefined : 0}
                aria-label={`${state}${state === dfa.start_state ? ", initial state" : ""}${accepting ? ", accepting state" : ""}${isActive ? ", active" : ""}. Inspect state.`}
                onClick={(e) => choose(e, state)}
                onKeyDown={(e) => {
                  if (["Enter", " "].includes(e.key)) {
                    e.preventDefault();
                    choose(e, state);
                  }
                }}
                className="graph-node"
              >
                {isActive && (
                  <circle cx={x} cy={y} r="43" fill={color} opacity=".075" />
                )}
                <motion.circle
                  cx={x}
                  cy={y}
                  r="31"
                  animate={{ fill: isActive ? color : "#fff", stroke: color }}
                  transition={{ duration: 0.25 }}
                  strokeWidth={selected === state ? 3 : 2}
                  filter={isActive ? `url(#${uid}-shadow)` : undefined}
                />
                {accepting && (
                  <circle
                    cx={x}
                    cy={y}
                    r="25"
                    fill="none"
                    stroke={isActive ? "#fff" : color}
                    strokeWidth="1.5"
                  />
                )}
                <text
                  x={x}
                  y={y + 6}
                  textAnchor="middle"
                  className="graph-state-label"
                  style={{ fontSize: Math.min(18, 48 / Math.max(1, state.length * 0.6)) }}
                  fill={isActive ? "#fff" : "#30273a"}
                >
                  {state}
                </text>
                {state === dfa.start_state && (
                  <>
                    <path
                      d={`M${x} ${y + 75} L${x} ${y + 36}`}
                      fill="none"
                      stroke="#a598ac"
                      strokeWidth="1.5"
                      markerEnd={`url(#${uid}-arrow)`}
                    />
                    <text
                      x={x}
                      y={y + 92}
                      textAnchor="middle"
                      className="graph-small-label"
                    >
                      start
                    </text>
                  </>
                )}
              </g>
            );
          })}
        {isTree &&
          layout.links.map(([a, b]) => {
            const [x, y] = treePoint(a),
              [tx, ty] = treePoint(b);
            return (
              <motion.path
                key={`${a}-${b}`}
                d={`M${x},${y + 19} C${x},${(y + ty) / 2} ${tx},${(y + ty) / 2} ${tx},${ty - 19}`}
                fill="none"
                animate={{
                  stroke: visibleNodes.has(b) ? "#bbaec5" : "#e8e0ed",
                  opacity: visibleNodes.has(b) ? 1 : 0.35,
                }}
                strokeWidth="1.7"
              />
            );
          })}
        {isTree &&
          Object.entries(layout.nodes).map(([id, node]) => {
            const [x, y] = treePoint(id),
              shown = visibleNodes.has(id),
              current = currentProduction === id,
              width = Math.max(42, Math.min(130, node.symbol.length * 11 + 22));
            return (
              <g
                key={id}
                role="button"
                tabIndex="0"
                data-node="true"
                aria-label={`${node.symbol}, ${treeKind === "ast" ? node.terminal ? "operand" : "operator" : node.terminal ? "terminal" : "nonterminal"}, node ${id}. Inspect node.`}
                onClick={(e) => choose(e, id)}
                onKeyDown={(e) => {
                  if (["Enter", " "].includes(e.key)) {
                    e.preventDefault();
                    choose(e, id);
                  }
                }}
                className="graph-node"
              >
                <motion.rect
                  x={x - width / 2}
                  y={y - 21}
                  width={width}
                  height="42"
                  rx="12"
                  animate={{
                    fill: current
                      ? "#d03676"
                      : node.terminal
                        ? "#f8e6f0"
                        : "#fff",
                    opacity: shown ? 1 : 0.25,
                    stroke:
                      selected === id || current
                        ? "#d03676"
                        : node.terminal
                          ? "#daa4c1"
                          : "#bbaec5",
                  }}
                  strokeWidth={selected === id || current ? 2 : 1.5}
                />
                <text
                  x={x}
                  y={y + 6}
                  textAnchor="middle"
                  className="graph-state-label"
                  fill={current ? "#fff" : "#4c3558"}
                  opacity={shown ? 1 : 0.35}
                  fontSize={Math.min(18, 115 / Math.max(1, node.symbol.length))}
                >
                  {node.symbol}
                </text>
                {!node.terminal && node.children.length === 0 && <text x={x} y={y+38} textAnchor="middle" className="graph-small-label" opacity={shown ? 1 : 0.35}>ε</text>}
                {selected === id && (
                  <text
                    x={x}
                    y={y + 36}
                    textAnchor="middle"
                    className="graph-small-label"
                  >
                    {id}
                  </text>
                )}
              </g>
            );
          })}
      </svg>
      {!compact && (
        <div className="canvas-legend">
          {isTree ? (
            <>
              <span>
                <i className="legend-terminal" /> {treeKind === "ast" ? "Operand" : "Terminal"}
              </span>
              <span>
                <i className="legend-nonterminal" /> {treeKind === "ast" ? "Operator" : "Nonterminal"}
              </span>
              <span className="legend-right">Select a node to inspect</span>
            </>
          ) : (
            <>
              <span>
                <i
                  className="legend-active"
                  style={{ backgroundColor: stateColor(dfa, active) }}
                />{" "}
                Active state
              </span>
              <span>
                <i className="legend-accept" /> Accepting state
              </span>
              <span className="legend-right">Select a state to inspect</span>
            </>
          )}
        </div>
      )}
      {expanded && (
        <button className="expanded-close" onClick={() => setExpanded(false)}>
          Close expanded view <Minimize2 size={15} />
        </button>
      )}
    </div>
  );
}

export function HeroDiagram() {
  const reduced = useReducedMotion();
  return (
    <div
      className="hero-diagram"
      aria-label="Reference example: three-state automaton for binary strings ending in 01"
    >
      <div className="hero-diagram-label">
        <span className="mini-dot" /> FINITE AUTOMATON{" "}
        <span>01 / REFERENCE</span>
      </div>
      <svg
        viewBox="0 0 540 300"
        role="img"
        aria-label="Example states q0, q1 and accepting state q2; input 1101"
      >
        <defs>
          <marker
            id="hero-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M0 0L10 5L0 10" fill="#7492ff" />
          </marker>
        </defs>
        <path
          d="M115 148 Q250 10 388 130"
          fill="none"
          stroke="#5271cd"
          strokeWidth="1.7"
          markerEnd="url(#hero-arrow)"
        />
        <path
          d="M290 230 Q195 258 136 177"
          fill="none"
          stroke="#5271cd"
          strokeWidth="1.7"
          markerEnd="url(#hero-arrow)"
        />
        <path
          d="M415 123 C480 70 470 20 430 62"
          fill="none"
          stroke="#5271cd"
          strokeWidth="1.7"
          markerEnd="url(#hero-arrow)"
        />
        <path
          d="M96 121 C44 61 22 162 77 164"
          fill="none"
          stroke="#5271cd"
          strokeWidth="1.7"
          markerEnd="url(#hero-arrow)"
        />
        <path
          d="M421 182 C446 238 365 275 338 236"
          fill="none"
          stroke="#5271cd"
          strokeWidth="1.7"
          markerEnd="url(#hero-arrow)"
        />
        <path
          d="M323 183 Q345 139 376 151"
          fill="none"
          stroke="#7492ff"
          strokeWidth="1.7"
          markerEnd="url(#hero-arrow)"
        />
        {!reduced && (
          <motion.path
            d="M115 148 Q250 10 388 130"
            fill="none"
            stroke="#c9d6ff"
            strokeWidth="3"
            strokeDasharray="18 270"
            animate={{ strokeDashoffset: [0, -580] }}
            transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
          />
        )}
        <g className="hero-edge-text">
          <text x="250" y="72">
            0
          </text>
          <text x="211" y="238">
            1
          </text>
          <text x="465" y="65">
            0
          </text>
          <text x="39" y="116">
            1
          </text>
          <text x="405" y="253">
            1
          </text>
          <text x="345" y="149">
            0
          </text>
        </g>
        <g>
          <circle
            cx="109"
            cy="156"
            r="34"
            fill="#293c74"
            stroke="#7e9aff"
            strokeWidth="1.7"
          />
          <text x="109" y="163" textAnchor="middle" className="hero-node-text">
            q₀
          </text>
        </g>
        <g>
          <circle
            cx="411"
            cy="151"
            r="34"
            fill="#d03676"
            stroke="#9db5ff"
            strokeWidth="1.7"
          />
          <text x="411" y="158" textAnchor="middle" className="hero-node-text">
            q₁
          </text>
        </g>
        <g>
          <circle
            cx="317"
            cy="214"
            r="30"
            fill="#293c74"
            stroke="#a6b8ee"
            strokeWidth="1.7"
          />
          <circle cx="317" cy="214" r="24" fill="none" stroke="#a6b8ee" />
          <text x="317" y="221" textAnchor="middle" className="hero-node-text">
            q₂
          </text>
        </g>
        <path
          d="M49 190L79 172"
          fill="none"
          stroke="#7e9aff"
          strokeWidth="1.5"
          markerEnd="url(#hero-arrow)"
        />
      </svg>
      <div className="hero-tokens">
        <span>INPUT</span>
        {["1", "1", "0", "1"].map((v, i) => (
          <motion.b
            key={i}
            animate={
              reduced
                ? {}
                : { backgroundColor: ["#24335b", "#d03676", "#24335b"] }
            }
            transition={{ duration: 4, delay: i * 0.6, repeat: Infinity }}
          >
            {v}
          </motion.b>
        ))}
        <span className="hero-example-badge">REFERENCE DEMONSTRATION</span>
      </div>
    </div>
  );
}
