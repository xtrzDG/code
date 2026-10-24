import { Ground, IllustrationFrame, Sparkle, type IllustrationProps } from "./IllustrationFrame";

const SLOTS = [0, 1, 2, 3].flatMap((column) => [0, 1, 2].map((row) => ({ column, row })));

/** An open calendar page with one slot lit and a clock beside it: nothing booked yet. */
export function NoBookingsIllustration({ className }: IllustrationProps) {
  return (
    <IllustrationFrame name="no-bookings" className={className}>
      <Ground />
      <rect x="36" y="31" width="88" height="70" rx="9" className="fill-surface" />
      <path d="M36 40a9 9 0 0 1 9-9h70a9 9 0 0 1 9 9v6H36Z" className="fill-accent-soft" />
      <path d="M36 46h88" className="stroke-line-strong" strokeWidth="1.6" />
      <rect x="36" y="31" width="88" height="70" rx="9" className="fill-none stroke-line-strong" strokeWidth="1.6" />
      <rect x="54" y="24" width="5" height="14" rx="2.5" className="fill-line-strong" />
      <rect x="101" y="24" width="5" height="14" rx="2.5" className="fill-line-strong" />
      {SLOTS.map(({ column, row }) =>
        column === 2 && row === 1 ? null : (
          <rect key={`${column}-${row}`} x={47 + column * 18} y={55 + row * 14} width="12" height="8" rx="2.5" className="fill-surface-muted" />
        ),
      )}
      <g className="aw-beat">
        <rect x="83" y="67" width="14" height="10" rx="3" className="fill-accent-solid" />
        <path d="M90 69.5v5M87.5 72h5" className="stroke-on-accent" strokeWidth="1.6" strokeLinecap="round" />
      </g>
      <g className="aw-float">
        <circle cx="126" cy="92" r="13" className="fill-surface stroke-line-strong" strokeWidth="1.6" />
        <path d="M126 85v7l5 3" className="fill-none stroke-accent-solid" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
      <Sparkle x={28} y={26} />
      <Sparkle x={138} y={30} size={3} className="[animation-delay:-1.6s]" />
    </IllustrationFrame>
  );
}
