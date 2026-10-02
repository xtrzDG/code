"use client";

/**
 * The picture beside "On this device": a small screen tilting in 3D under
 * the pointer, with a notification that floats above it while this device
 * is on (it slides in when turned on) and a muted bell while it is off.
 */

import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { IconBell } from "@/components/icons";
import { TiltCard, TiltLayer } from "@/components/motion";
import { springTransition } from "@/lib/motion";
import { cn } from "@/lib/cn";

export function DeviceVisual({ isOn, title }: { isOn: boolean; title: string }) {
  return (
    <TiltCard className="mx-auto h-32 w-44 shrink-0 rounded-[1.4rem]" glare={isOn}>
      <div
        aria-hidden
        className={cn(
          "absolute inset-0 rounded-[inherit] border bg-surface-muted shadow-[0_24px_48px_-28px_rgb(0_0_0/0.45)] transition-colors duration-(--motion-base)",
          isOn ? "border-accent/40" : "border-line",
        )}
      >
        <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-line" />
        <div className="mt-12 space-y-1.5 px-4">
          <div className="h-1.5 w-3/4 rounded-full bg-line" />
          <div className="h-1.5 w-1/2 rounded-full bg-line" />
        </div>
      </div>
      <TiltLayer depth={34} className="absolute inset-x-3 top-5">
        <AnimatePresence initial={false} mode="wait">
          {isOn ? (
            <m.div
              key="on"
              aria-hidden
              initial={{ opacity: 0, y: -14, scale: 0.94 }}
              animate={{ opacity: 1, y: 0, scale: 1, transition: springTransition("bouncy") }}
              exit={{ opacity: 0, y: -10, transition: { duration: 0.12 } }}
              className="flex items-center gap-2 rounded-xl border border-line bg-surface px-2.5 py-2 shadow-[0_14px_30px_-14px_var(--accent-solid)]"
            >
              <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-accent-solid text-white">
                <IconBell className="size-3.5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[0.625rem] leading-3 font-semibold text-ink">{title}</span>
                <span className="mt-1 block h-1 w-2/3 rounded-full bg-line" />
              </span>
            </m.div>
          ) : (
            <m.div
              key="off"
              aria-hidden
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex justify-center pt-1"
            >
              <span className="relative flex size-9 items-center justify-center rounded-full border border-line bg-surface text-ink-subtle">
                <IconBell className="size-4" />
                <span className="absolute h-0.5 w-6 rotate-45 rounded-full bg-ink-subtle" />
              </span>
            </m.div>
          )}
        </AnimatePresence>
      </TiltLayer>
    </TiltCard>
  );
}
