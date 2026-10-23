/**
 * The hero's poster: the 3D scene's composition in HTML and CSS — the orb,
 * two tilted orbits with a light running along each, and the six channels'
 * bubbles floating around it. It is what everyone sees first
 * (server-rendered, no WebGL, in the scene's own box, so nothing shifts
 * when the scene fades in over it), all a phone shows, and what stays for
 * reduced motion (then still), without WebGL and on weak devices. Styles:
 * `.hero-still*` in src/styles/heroPoster.css.
 */

import { CHANNEL_MARK_GRADIENTS, CHANNEL_MARK_KEYS, CHANNEL_MARKS } from "@/lib/channelMarks";
import { cn } from "@/lib/cn";

/**
 * Bubbles on an ellipse around the orb (degrees, 0 = right, clockwise):
 * bubble k sits at 50% + 39%·cos, 50% + 33%·sin and floats 0.9 s behind
 * the one before. heroPoster.css places them (`[data-bubble]`).
 */
export const BUBBLE_ANGLES = [-148, -62, -8, 38, 122, 168] as const;

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
          <div key={channel} data-bubble={index} className="hero-still-bubble">
            <span className={cn("hero-still-badge", CHANNEL_MARK_GRADIENTS[channel])}>
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
