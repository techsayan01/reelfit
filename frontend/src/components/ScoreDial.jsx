import { useEffect, useState } from "react";

const CIRCUMFERENCE = 2 * Math.PI * 45;

/** The Fit Score dial — Reelfit's signature element (BRD §6.4).
    Marquee Amber fill proportional to score on a quiet Reel Ink ring;
    animates once on reveal, respecting reduced-motion via CSS. */
export default function ScoreDial({ score, calibration, size = 110 }) {
  const [offset, setOffset] = useState(CIRCUMFERENCE);

  useEffect(() => {
    // Start empty, then fill — the single animated moment on the page.
    const id = requestAnimationFrame(() =>
      setOffset(CIRCUMFERENCE * (1 - score / 100))
    );
    return () => cancelAnimationFrame(id);
  }, [score]);

  return (
    <svg
      className="score-dial"
      width={size}
      height={size}
      viewBox="0 0 110 110"
      role="img"
      aria-label={`Fit score ${score} out of 100 (${calibration})`}
    >
      <circle className="ring-bg" cx="55" cy="55" r="45" fill="none" strokeWidth="8" />
      <circle
        className="ring-fill"
        cx="55"
        cy="55"
        r="45"
        fill="none"
        strokeWidth="8"
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={offset}
      />
      <text className="score-number" x="55" y="60" textAnchor="middle" fontSize="30">
        {score}
      </text>
      <text className="score-label" x="55" y="78" textAnchor="middle">
        fit
      </text>
    </svg>
  );
}
