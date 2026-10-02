"use client";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { badgeText } from "@/lib/inboxBadges";

/**
 * How many things wait on a page ("3"), in a small pill that pops in;
 * screen readers hear "3 waiting". Nothing for zero.
 */
export function NavBadge({ count, size = "md", className }: { count: number; size?: "md" | "sm"; className?: string }) {
  const { tp } = useI18n();
  if (count <= 0) {
    return null;
  }
  return (
    <span
      className={cn(
        "inline-flex animate-settle items-center justify-center rounded-full bg-danger-solid leading-none font-semibold text-on-accent tabular-nums",
        size === "md" ? "h-5 min-w-5 px-1.5 text-[0.6875rem]" : "h-4 min-w-4 px-1 text-[0.625rem]",
        className,
      )}
    >
      <span aria-hidden>{badgeText(count)}</span>
      <span className="sr-only">{`, ${tp("navigation.waiting", count)}`}</span>
    </span>
  );
}
