"use client";

import { useEffect, useRef } from "react";

import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { useMotionPreference } from "@/components/motion/MotionPreference";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { badgeText } from "@/lib/inboxBadges";
import { EASINGS } from "@/lib/motion";

/** A badge that grows gives a small beat, so a new arrival catches the eye. */
const BEAT: Keyframe[] = [{ transform: "scale(1)" }, { transform: "scale(1.22)" }, { transform: "scale(1)" }];
const BEAT_TIMING: KeyframeAnimationOptions = { duration: 360, easing: `cubic-bezier(${EASINGS.emphasized.join(",")})` };
const COUNT_MS = 420;

/**
 * How many things wait on a page ("3"), in a small pill that pops in;
 * when the number changes it counts to the new one (AnimatedNumber) and
 * beats once if it grew. Screen readers hear "3 waiting" at once, and with
 * reduced motion the number simply changes. Nothing for zero.
 */
export function NavBadge({ count, size = "md", className }: { count: number; size?: "md" | "sm"; className?: string }) {
  const { tp } = useI18n();
  const { isCalm } = useMotionPreference();
  const pill = useRef<HTMLSpanElement>(null);
  const previous = useRef(count);

  useEffect(() => {
    const before = previous.current;
    previous.current = count;
    if (count > before && before > 0 && !isCalm) {
      pill.current?.animate?.(BEAT, BEAT_TIMING);
    }
  }, [count, isCalm]);

  if (count <= 0) {
    return null;
  }
  return (
    <span
      ref={pill}
      data-badge-count={count}
      className={cn(
        "inline-flex animate-settle items-center justify-center rounded-full bg-danger-solid leading-none font-semibold text-on-accent tabular-nums",
        size === "md" ? "h-5 min-w-5 px-1.5 text-[0.6875rem]" : "h-4 min-w-4 px-1 text-[0.625rem]",
        className,
      )}
    >
      <span aria-hidden>
        <AnimatedNumber value={count} format={badgeText} countIn={false} durationMs={COUNT_MS} />
      </span>
      <span className="sr-only">{`, ${tp("navigation.waiting", count)}`}</span>
    </span>
  );
}
