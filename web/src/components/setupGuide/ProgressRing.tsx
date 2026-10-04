/**
 * How much of the setup guide is done, as a ring with the percent inside
 * (or beside it, when the ring is too small for text). The ring is the
 * accent on the theme's line colour; the number is for everyone, the
 * ring only decorates it.
 */

import { cn } from "@/lib/cn";

export function ProgressRing({
  percent,
  size = 40,
  label,
  showNumber = true,
  className,
}: {
  percent: number;
  size?: number;
  /** What screen readers hear ("Setup: 70 % done"). */
  label: string;
  /** False: only the ring (the number is said nearby). */
  showNumber?: boolean;
  className?: string;
}) {
  const stroke = size >= 32 ? 4 : 3;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const done = Math.min(100, Math.max(0, percent));
  return (
    <span
      role="img"
      aria-label={label}
      className={cn("relative inline-flex shrink-0 items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      <svg viewBox={`0 0 ${size} ${size}`} className="size-full -rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} className="stroke-line" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - done / 100)}
          className="stroke-accent-solid transition-[stroke-dashoffset] duration-(--motion-slow) ease-(--ease-emphasized)"
        />
      </svg>
      {showNumber ? (
        <span aria-hidden className="absolute text-[0.625rem] font-semibold tabular-nums text-ink">
          {done}
        </span>
      ) : null}
    </span>
  );
}
