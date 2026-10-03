/**
 * The tunnel behind the steps: an aurora, a glowing vanishing point and
 * rings receding into the screen. `depth` is how far the owner has come
 * (the step's index); a step forward glides every ring one place closer
 * and the passed one fades behind the viewer, a step back the other way.
 * `burst` sends rings of light out of the tunnel (the finale).
 *
 * Pure CSS 3D (src/styles/tunnel.css): no WebGL and no script per frame,
 * so it costs nothing on a phone and stands still with reduced motion.
 */

import type { CSSProperties } from "react";

import { ringsAt } from "@/lib/tunnel/depth";

export function TunnelBackdrop({ depth, burst = false }: { depth: number; burst?: boolean }) {
  return (
    <div aria-hidden data-tunnel-backdrop className="tunnel-depth">
      <div className="landing-aurora">
        <span />
        <span />
        <span />
      </div>
      <div className="tunnel-glow" style={{ transform: "translate(-50%, -50%)" }} />
      <div className="tunnel-rings">
        {ringsAt(depth).map((ring) => (
          <span
            key={ring.key}
            className="tunnel-ring"
            style={{ "--ring-z": `${ring.z}px`, "--ring-opacity": ring.opacity } as CSSProperties}
          />
        ))}
      </div>
      <div className="landing-floor">
        <div className="landing-floor-plane">
          <span />
        </div>
      </div>
      {burst ? (
        <div className="tunnel-burst">
          <span />
          <span />
          <span />
        </div>
      ) : null}
    </div>
  );
}
