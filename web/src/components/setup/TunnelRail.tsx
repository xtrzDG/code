"use client";

/**
 * Where the owner is in the tunnel: eight stations on a line that fills as
 * they go deeper. A station they may jump to (one already reached, or done)
 * is a button; the current one is marked `aria-current="step"`. On phones
 * the line stays and only the current step's name shows beside "3 / 8".
 */

import type { CSSProperties } from "react";

import { IconCheck } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { placeIndex, TUNNEL_STEPS, type RailState, type TunnelPlace, type TunnelStep } from "@/lib/tunnel/steps";

export interface TunnelRailProps {
  place: TunnelPlace;
  states: Record<TunnelStep, RailState>;
  /** Steps the owner may open from the rail (null: none, e.g. while saving). */
  canOpen: (step: TunnelStep) => boolean;
  onOpen: (step: TunnelStep) => void;
}

export function TunnelRail({ place, states, canOpen, onOpen }: TunnelRailProps) {
  const { t } = useI18n();
  const current = placeIndex(place);
  const fill = Math.min(current, TUNNEL_STEPS.length - 1) / (TUNNEL_STEPS.length - 1);
  const currentStep = TUNNEL_STEPS[current];

  return (
    <nav aria-label={t("tunnel.railLabel")} className="min-w-0 flex-1">
      <div className="flex items-center gap-3">
        <span className="shrink-0 text-xs font-medium text-ink-muted tabular-nums sm:hidden">
          {Math.min(current + 1, TUNNEL_STEPS.length)} / {TUNNEL_STEPS.length}
        </span>
        <ol className="relative flex flex-1 items-center justify-between">
          <span aria-hidden className="absolute inset-x-1 top-1/2 h-px -translate-y-1/2 bg-line" />
          <span
            aria-hidden
            className="tunnel-rail-fill absolute inset-x-1 top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-gradient-to-r from-accent-solid via-[#3cc6f5] to-accent-solid"
            style={{ transform: `translateY(-50%) scaleX(${fill})` } as CSSProperties}
          />
          {TUNNEL_STEPS.map((step, index) => {
            const isCurrent = index === current;
            const state = isCurrent ? "current" : states[step];
            const label = `${t(`tunnel.steps.${step}`)} (${t(`tunnel.stepState.${state}`)})`;
            const dot = (
              <span
                className={cn(
                  "relative flex size-3 items-center justify-center rounded-full border transition-all duration-(--motion-slow) sm:size-5",
                  isCurrent && "size-4 border-accent bg-accent-solid shadow-[0_0_0_4px_color-mix(in_oklab,var(--accent-solid)_25%,transparent)] sm:size-6",
                  !isCurrent && state === "done" && "border-accent-solid bg-accent-solid text-on-accent",
                  !isCurrent && state === "skipped" && "border-dashed border-line-strong bg-surface",
                  !isCurrent && state === "todo" && "border-line-strong bg-surface",
                )}
              >
                {!isCurrent && state === "done" ? <IconCheck className="hidden size-3 sm:block" aria-hidden /> : null}
              </span>
            );
            return (
              <li key={step} className="relative z-10 flex">
                {canOpen(step) && !isCurrent ? (
                  <button
                    type="button"
                    onClick={() => onOpen(step)}
                    aria-label={label}
                    title={t(`tunnel.steps.${step}`)}
                    className="flex size-7 cursor-pointer items-center justify-center rounded-full transition-transform hover:scale-110 sm:size-8"
                  >
                    {dot}
                  </button>
                ) : (
                  <span
                    role="img"
                    aria-label={label}
                    aria-current={isCurrent ? "step" : undefined}
                    title={t(`tunnel.steps.${step}`)}
                    className="flex size-7 items-center justify-center sm:size-8"
                  >
                    {dot}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </div>
      {currentStep ? (
        <p className="mt-0.5 hidden text-center text-xs font-medium text-ink-muted sm:block" aria-hidden>
          {t(`tunnel.steps.${currentStep}`)}
        </p>
      ) : null}
    </nav>
  );
}
