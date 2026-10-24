import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import paths from "./wordmark-paths.json";

export function LogoMark({ animated = false, className = "" }) {
  return (
    <svg
      className={`logo-mark ${className}`}
      viewBox={paths.viewBox}
      role="img"
      aria-label="TheoryBERT: BERT above THEORY in Poppins"
    >
      {paths.letters.map((letter, i) => (
        <path
          key={i}
          className={animated ? "logo-letter" : undefined}
          d={letter.d}
          pathLength="1"
          style={{ "--letter-delay": `${letter.delay}s` }}
        />
      ))}
      <rect {...paths.dot} className="logo-accent" />
    </svg>
  );
}

export function Wordmark({ className = "" }) {
  return (
    <Link
      to="/"
      className={`brand-logo ${className}`}
      aria-label="TheoryBERT home"
    >
      <LogoMark />
    </Link>
  );
}

export function Startup({ children }) {
  const [active, setActive] = useState(
    () =>
      window.location.pathname === "/" &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [leaving, setLeaving] = useState(false);
  useEffect(() => {
    if (!active) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const fade = setTimeout(() => setLeaving(true), 1950);
    const finish = setTimeout(() => setActive(false), 2350);
    const close = (e) => {
      if (e.key === "Escape") setActive(false);
    };
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const reduce = (e) => {
      if (e.matches) setActive(false);
    };
    document.addEventListener("keydown", close);
    media.addEventListener("change", reduce);
    return () => {
      clearTimeout(fade);
      clearTimeout(finish);
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", close);
      media.removeEventListener("change", reduce);
    };
  }, [active]);
  function skip() {
    setActive(false);
    requestAnimationFrame(() =>
      document
        .getElementById("landing-heading")
        ?.focus({ preventScroll: true }),
    );
  }
  return (
    <>
      <div
        className="startup-content"
        data-ready={!active || leaving}
        inert={active ? true : undefined}
        aria-hidden={active ? true : undefined}
      >
        {children}
      </div>
      {active && (
        <div
          className={`startup-screen ${leaving ? "startup-leaving" : ""}`}
          aria-label="TheoryBERT introduction"
        >
          <div role="status" aria-label="Writing the TheoryBERT logo">
            <LogoMark animated className="startup-logo" />
          </div>
          <button className="startup-skip" onClick={skip}>
            Skip intro <span aria-hidden="true">↗</span>
          </button>
        </div>
      )}
    </>
  );
}
