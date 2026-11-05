"use client";

/**
 * The floating action button of a phone page: the page's one main action
 * ("New booking", "Apply changes") within the thumb's reach, above the tab
 * bar. Extended (icon and label) while the page rests or scrolls up; while
 * the person scrolls down through a list it folds to its icon so it covers
 * less, and its name stays for screen readers. Rendered by the shell's tab
 * bar from what the page registers (usePhoneFab), not by pages.
 */

import { useEffect, useState, type ComponentType } from "react";

import { cn } from "@/lib/cn";

import type { IconProps } from "../icons";

/** Scrolling this far down in one go folds the label; any scroll up unfolds it. */
const FOLD_AFTER_PX = 48;

function useScrolledDown(): boolean {
  const [isDown, setDown] = useState(false);
  useEffect(() => {
    let anchor = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      if (y < anchor) {
        setDown(false);
        anchor = y;
      } else if (y - anchor > FOLD_AFTER_PX) {
        setDown(y > FOLD_AFTER_PX);
        anchor = y;
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return isDown;
}

export function Fab({
  label,
  icon: Icon,
  onClick,
  opensDialog = false,
  className,
}: {
  label: string;
  icon: ComponentType<IconProps>;
  onClick: () => void;
  opensDialog?: boolean;
  className?: string;
}) {
  const isFolded = useScrolledDown();
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-haspopup={opensDialog ? "dialog" : undefined}
      data-folded={isFolded || undefined}
      className={cn(
        "motion-press pointer-events-auto inline-flex h-14 min-w-14 cursor-pointer items-center justify-center rounded-2xl bg-accent-solid px-4 text-[0.9375rem] font-semibold text-on-accent",
        "shadow-[0_12px_32px_-12px_color-mix(in_oklab,var(--accent-solid)_80%,transparent),0_4px_12px_-4px_rgb(0_0_0/0.35)]",
        "animate-settle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
        className,
      )}
    >
      <Icon className="size-6 shrink-0" aria-hidden />
      <span
        aria-hidden
        className={cn(
          "overflow-hidden whitespace-nowrap transition-[max-width,opacity,margin] duration-(--motion-base) ease-(--ease-emphasized)",
          isFolded ? "ms-0 max-w-0 opacity-0" : "ms-2 max-w-56 opacity-100",
        )}
      >
        {label}
      </span>
    </button>
  );
}
