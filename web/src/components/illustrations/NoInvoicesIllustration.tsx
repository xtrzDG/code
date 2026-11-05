import { Ground, IllustrationFrame, Sparkle, type IllustrationProps } from "./IllustrationFrame";

/** A blank receipt with a coin rolling beside it: no invoices yet. */
export function NoInvoicesIllustration({ className }: IllustrationProps) {
  return (
    <IllustrationFrame name="no-invoices" className={className}>
      <Ground width={84} />
      <path
        d="M52 18h56a5 5 0 0 1 5 5v77l-6.5-4.5L100 100l-6.5-4.5L87 100l-6.5-4.5L74 100l-6.5-4.5L61 100l-6.5-4.5L48 100V23a4 4 0 0 1 4-5Z"
        className="fill-surface stroke-line-strong"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <rect x="58" y="30" width="26" height="5" rx="2.5" className="fill-line-strong" />
      <rect x="58" y="44" width="44" height="3.6" rx="1.8" className="fill-line" />
      <rect x="58" y="53" width="36" height="3.6" rx="1.8" className="fill-line" />
      <rect x="58" y="62" width="40" height="3.6" rx="1.8" className="fill-line" />
      <path d="M58 76h44" className="stroke-line-strong" strokeWidth="1.4" strokeDasharray="2 3" strokeLinecap="round" />
      <rect x="84" y="81" width="18" height="5" rx="2.5" className="fill-accent-solid" />
      <g className="aw-float [animation-delay:-2s]">
        <circle cx="122" cy="86" r="14" className="fill-tone-sand stroke-line-strong" strokeWidth="1.4" />
        <circle cx="122" cy="86" r="9.5" className="fill-none stroke-surface/70" strokeWidth="1.4" />
        <path d="M118 82.5h8M118 89.5h8" className="stroke-surface/80" strokeWidth="1.6" strokeLinecap="round" />
      </g>
      <Sparkle x={36} y={36} />
      <Sparkle x={130} y={58} size={3} className="[animation-delay:-0.8s]" />
    </IllustrationFrame>
  );
}
