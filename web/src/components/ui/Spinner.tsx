import { cn } from "@/lib/cn";

const SIZES = { sm: "size-4", md: "size-5", lg: "size-8" } as const;

/**
 * Loading indicator. Pass `label` when the spinner is the only sign of
 * loading (it is announced to screen readers); omit it inside a button
 * that already says what is happening.
 */
export function Spinner({
  size = "md",
  label,
  className,
}: {
  size?: keyof typeof SIZES;
  label?: string;
  className?: string;
}) {
  return (
    <span role={label ? "status" : undefined} className={cn("inline-flex items-center", className)}>
      <svg
        className={cn("animate-spin text-current", SIZES[size])}
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
        <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      </svg>
      {label ? <span className="sr-only">{label}</span> : null}
    </span>
  );
}

/** A centered spinner for a loading page or card. */
export function LoadingBlock({ label, className }: { label: string; className?: string }) {
  return (
    <div className={cn("flex min-h-40 items-center justify-center gap-3 text-ink-muted", className)}>
      <Spinner size="md" />
      <span className="text-sm" role="status">
        {label}
      </span>
    </div>
  );
}
