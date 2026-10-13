import { IllustrationFrame, Sparkle, type IllustrationProps } from "./IllustrationFrame";

/**
 * The assistant's orb with channel bubbles on its ring: the landing hero's
 * scene drawn flat, for the finale where WebGL is missing or motion is
 * reduced (and while the 3D orb loads). `gradientId` must be unique on
 * the page.
 */
export function AssistantOrbIllustration({ className, gradientId = "aw-orb-gradient" }: IllustrationProps & { gradientId?: string }) {
  return (
    <IllustrationFrame name="assistant-orb" className={className}>
      <defs>
        <radialGradient id={gradientId} cx="38%" cy="32%" r="72%">
          <stop offset="0%" style={{ stopColor: "var(--tone-sand)" }} />
          <stop offset="55%" style={{ stopColor: "var(--accent-solid)" }} />
          <stop offset="100%" style={{ stopColor: "var(--accent-ink)" }} />
        </radialGradient>
      </defs>
      <circle cx="80" cy="60" r="46" className="aw-beat fill-accent-soft" />
      <ellipse cx="80" cy="62" rx="66" ry="17" transform="rotate(-10 80 62)" className="fill-none stroke-line-strong" strokeWidth="1.2" strokeDasharray="3 5" />
      <circle cx="80" cy="60" r="27" fill={`url(#${gradientId})`} />
      <ellipse cx="71" cy="49" rx="9" ry="5.5" transform="rotate(-24 71 49)" className="fill-surface/35" />
      <g className="aw-float">
        <rect x="10" y="62" width="22" height="15" rx="7.5" className="fill-surface stroke-line-strong" strokeWidth="1.2" />
        <circle cx="17" cy="69.5" r="1.5" className="fill-accent" />
        <circle cx="21" cy="69.5" r="1.5" className="fill-accent" />
        <circle cx="25" cy="69.5" r="1.5" className="fill-accent" />
      </g>
      <g className="aw-float [animation-delay:-2.5s]">
        <rect x="124" y="40" width="24" height="15" rx="7.5" className="fill-accent-solid" />
        <rect x="130" y="46.3" width="12" height="2.4" rx="1.2" className="fill-on-accent" />
      </g>
      <g className="aw-drift [animation-delay:-4s]">
        <circle cx="112" cy="90" r="8" className="fill-surface stroke-line-strong" strokeWidth="1.2" />
        <path d="m108.6 90 2.4 2.4 4.4-4.6" className="fill-none stroke-accent-solid" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <Sparkle x={36} y={24} />
      <Sparkle x={128} y={18} size={3} className="[animation-delay:-1.3s]" />
      <Sparkle x={52} y={102} size={2.6} className="[animation-delay:-0.6s]" />
    </IllustrationFrame>
  );
}
