import { Ground, IllustrationFrame, Sparkle, type IllustrationProps } from "./IllustrationFrame";

/** An empty tray with a check floating over it: nothing waits in the inbox. */
export function InboxCalmIllustration({ className }: IllustrationProps) {
  return (
    <IllustrationFrame name="inbox-calm" className={className}>
      <Ground />
      {/* Two quiet conversations drifting on either side. */}
      <g className="aw-drift">
        <rect x="14" y="40" width="26" height="16" rx="8" className="fill-accent-soft stroke-accent/40" strokeWidth="1.2" />
        <path d="M22 55.5 19 61l7-5.5" className="fill-accent-soft stroke-accent/40" strokeWidth="1.2" strokeLinejoin="round" />
        <circle cx="22" cy="48" r="1.6" className="fill-accent" />
        <circle cx="27" cy="48" r="1.6" className="fill-accent" />
        <circle cx="32" cy="48" r="1.6" className="fill-accent" />
      </g>
      <g className="aw-drift [animation-delay:-3s]">
        <rect x="122" y="50" width="24" height="14" rx="7" className="fill-surface-muted stroke-line-strong" strokeWidth="1.2" />
        <path d="M138 63.5 141 69l-7-5.5" className="fill-surface-muted stroke-line-strong" strokeWidth="1.2" strokeLinejoin="round" />
        <rect x="128" y="56" width="12" height="2.4" rx="1.2" className="fill-line-strong" />
      </g>
      {/* The tray. */}
      <path d="M38 66 50 46h60l12 20v28a7 7 0 0 1-7 7H45a7 7 0 0 1-7-7Z" className="fill-surface stroke-line-strong" strokeWidth="1.6" strokeLinejoin="round" />
      <path
        d="M38 66h22a4 4 0 0 1 4 4v1a6 6 0 0 0 6 6h20a6 6 0 0 0 6-6v-1a4 4 0 0 1 4-4h22v28a7 7 0 0 1-7 7H45a7 7 0 0 1-7-7Z"
        className="fill-surface-muted stroke-line-strong"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M54 54h52M50 60h60" className="stroke-line" strokeWidth="1.6" strokeLinecap="round" />
      {/* All caught up. */}
      <g className="aw-float">
        <circle cx="80" cy="27" r="14" className="fill-accent-solid" />
        <path d="m73.5 27.2 4.6 4.5 8.4-9" className="fill-none stroke-on-accent" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <Sparkle x={56} y={20} />
      <Sparkle x={106} y={14} size={3} className="[animation-delay:-1.4s]" />
    </IllustrationFrame>
  );
}
