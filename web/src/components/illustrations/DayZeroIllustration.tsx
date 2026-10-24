import { Ground, IllustrationFrame, Sparkle, type IllustrationProps } from "./IllustrationFrame";

/** A fresh dashboard with a sunrise behind it and the first line starting to climb: day 0. */
export function DayZeroIllustration({ className }: IllustrationProps) {
  return (
    <IllustrationFrame name="day-zero" className={className}>
      <Ground width={104} />
      {/* The sun rising behind the card. */}
      <g className="aw-float">
        <circle cx="118" cy="32" r="15" className="fill-tone-sand/70" />
        <path d="M118 8v5M138 18l-3.5 3.5M98 18l3.5 3.5M143 36h-5" className="stroke-tone-sand" strokeWidth="2" strokeLinecap="round" />
      </g>
      <rect x="26" y="34" width="108" height="68" rx="10" className="fill-surface stroke-line-strong" strokeWidth="1.6" />
      <rect x="38" y="45" width="30" height="5" rx="2.5" className="fill-line-strong" />
      <rect x="38" y="54" width="18" height="4" rx="2" className="fill-line" />
      {/* Quiet bars and the first line climbing. */}
      <path d="M38 90h84" className="stroke-line" strokeWidth="1.6" strokeDasharray="2 4" strokeLinecap="round" />
      <rect x="44" y="82" width="8" height="8" rx="2" className="fill-surface-muted" />
      <rect x="60" y="78" width="8" height="12" rx="2" className="fill-surface-muted" />
      <rect x="76" y="80" width="8" height="10" rx="2" className="fill-surface-muted" />
      <path d="M40 86c14 0 18-6 30-8s20-4 28-12 14-6 18-8" className="fill-none stroke-accent-solid" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="116" cy="58" r="7" className="aw-beat fill-accent-soft" />
      <circle cx="116" cy="58" r="3.6" className="fill-accent-solid" />
      <Sparkle x={30} y={22} />
      <Sparkle x={90} y={18} size={3} className="[animation-delay:-1.2s]" />
    </IllustrationFrame>
  );
}
