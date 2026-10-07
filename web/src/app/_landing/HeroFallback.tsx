/**
 * The hero's poster: the 3D scene's composition in HTML and CSS — the orb,
 * two tilted orbits with a light running along each, and the six channels'
 * bubbles floating around it. It is what everyone sees first
 * (server-rendered, no WebGL, in the scene's own box, so nothing shifts
 * when the scene fades in over it), all a phone shows, and what stays for
 * reduced motion (then still), without WebGL and on weak devices. Styles:
 * `.hero-still*` in src/styles/heroPoster.css.
 */

import type { CSSProperties } from "react";

import { CHANNEL_MARKS } from "@/lib/channelMarks";
import { CHANNEL_MARK_KEYS } from "@/lib/heroScene";
import { roundTo } from "@/lib/motionMath";
import { cn } from "@/lib/cn";

/** Bubbles on an ellipse around the orb (degrees, 0 = right, clockwise). */
const ANGLES = [-148, -62, -8, 38, 122, 168];

function bubblePosition(index: number): CSSProperties {
  const angle = ((ANGLES[index] ?? 0) * Math.PI) / 180;
  return {
    left: `${roundTo(50 + 39 * Math.cos(angle), 2)}%`,
    top: `${roundTo(50 + 33 * Math.sin(angle), 2)}%`,
    animationDelay: `${-index * 0.9}s`,
  };
}

export function HeroFallback({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("hero-still", className)}>
      <div className="hero-still-glow" />
      <div className="hero-still-ring" />
      <div className="hero-still-ring hero-still-ring-wide" />
      <div className="hero-still-orb" />
      {CHANNEL_MARK_KEYS.map((channel, index) => {
        const mark = CHANNEL_MARKS[channel];
        return (
          <div key={channel} className="hero-still-bubble" style={bubblePosition(index)}>
            <span
              className="hero-still-badge"
              style={{ backgroundImage: `linear-gradient(135deg, ${mark.colors[0]}, ${mark.colors[1]})` }}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
                {mark.paths.map((path) => (
                  <path key={path} d={path} />
                ))}
              </svg>
            </span>
            <span className="hero-still-lines">
              <i />
              <i />
            </span>
          </div>
        );
      })}
    </div>
  );
}
