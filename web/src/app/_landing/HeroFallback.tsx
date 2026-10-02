/**
 * The still picture of the hero scene, in CSS: the orb, its orbits and the
 * six channels' bubbles around it, gently floating. It is what everyone
 * sees first (server-rendered, same size as the 3D scene, so nothing
 * shifts), and what stays for reduced motion, without WebGL and on weak
 * devices. Styles: `.hero-still*` in src/styles/landing.css.
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
