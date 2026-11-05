import { Ground, IllustrationFrame, Sparkle, type IllustrationProps } from "./IllustrationFrame";

/** A cloud above a cable whose plug has slipped out of its socket: no connection. */
export function OfflineIllustration({ className }: IllustrationProps) {
  return (
    <IllustrationFrame name="offline" className={className}>
      <Ground width={100} />
      <path
        d="M52 62a16 16 0 0 1 1.6-31.9A22 22 0 0 1 95 25a18 18 0 0 1 17.4 13.4A12 12 0 0 1 112 62Z"
        className="fill-surface stroke-line-strong"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M70 46a14 14 0 0 1 20 0M75 51a7 7 0 0 1 10 0" className="fill-none stroke-ink-subtle" strokeWidth="2" strokeLinecap="round" />
      <circle cx="80" cy="55.5" r="1.8" className="fill-ink-subtle" />
      <path d="M66 38l28 22" className="stroke-accent-solid" strokeWidth="2.2" strokeLinecap="round" />
      {/* The socket, and the plug pulled a little away from it. */}
      <path d="M20 92h30" className="stroke-line-strong" strokeWidth="2.4" strokeLinecap="round" />
      <rect x="50" y="83" width="16" height="18" rx="4" className="fill-surface-muted stroke-line-strong" strokeWidth="1.6" />
      <path d="M58 88v3M58 93v3" className="stroke-line-strong" strokeWidth="1.8" strokeLinecap="round" />
      <g className="aw-drift">
        <path d="M86 89h-6M86 95h-6" className="stroke-ink-subtle" strokeWidth="2" strokeLinecap="round" />
        <rect x="86" y="83" width="18" height="18" rx="4" className="fill-accent-solid" />
        <path d="M104 92h36" className="stroke-line-strong" strokeWidth="2.4" strokeLinecap="round" />
      </g>
      <path d="M72 84l2 3M74 98l2-3M71 91h3" className="aw-twinkle stroke-tone-sand" strokeWidth="1.6" strokeLinecap="round" />
      <Sparkle x={128} y={22} />
      <Sparkle x={30} y={36} size={3} className="[animation-delay:-1.1s]" />
    </IllustrationFrame>
  );
}
