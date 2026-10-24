"use client";

/**
 * The assistant above the finale's "Your assistant is live!": everyone
 * first sees the orb drawn flat (AssistantOrbIllustration). Wherever WebGL
 * exists, phones included, the landing's orb itself, three.js in a chunk of
 * its own, is fetched once the browser is idle and fades in over the drawing
 * after its first frame, in the same box (no layout shift). The landing
 * hero's other rules still hold (lib/heroDevice.ts): no reduced motion, no
 * data saver or slow connection, a capable device; only its wide-layout rule
 * does not, since the orb has a box of its own on every screen. Reduced
 * motion (the device's or the cabinet's own), a slow frame rate or a lost
 * WebGL context go back to the drawing.
 *
 * `data-orb` says which one is showing ("static" or "3d"); `data-orb-reason`
 * why the drawing stays.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { afterNextPaint, hasWebGl, readDeviceSignals, whenIdle } from "@/app/_landing/heroWaits";
import { AssistantOrbIllustration } from "@/components/illustrations";
import { useMotionPreference } from "@/components/motion/MotionPreference";
import { cn } from "@/lib/cn";
import { finaleOrbPlan, type PosterReason } from "@/lib/heroDevice";
import { inSequence } from "@/lib/waits";

const FinaleOrbScene = dynamic(() => import("@/app/_landing/scene/FinaleOrbScene"), { ssr: false });

type Stage = { kind: "waiting" } | { kind: "static"; reason: PosterReason } | { kind: "loading" } | { kind: "live" };

function useOrbStage(isCalm: boolean) {
  const [stage, setStage] = useState<Stage>({ kind: "waiting" });

  useEffect(() => {
    if (isCalm) {
      return;
    }
    let cancel: () => void = () => undefined;
    const stop = (reason: PosterReason) => {
      cancel();
      setStage({ kind: "static", reason });
    };
    cancel = afterNextPaint(() => {
      const plan = finaleOrbPlan(readDeviceSignals());
      if (plan.kind === "poster") {
        stop(plan.reason);
        return;
      }
      cancel = inSequence([whenIdle], () => (hasWebGl() ? setStage({ kind: "loading" }) : stop("no-webgl")));
    });
    return () => cancel();
  }, [isCalm]);

  return {
    stage: isCalm ? ({ kind: "static", reason: "reduced-motion" } as const) : stage,
    onReady: () => setStage((current) => (current.kind === "loading" ? { kind: "live" } : current)),
    onFallback: () =>
      setStage((current) => (current.kind === "loading" || current.kind === "live" ? { kind: "static", reason: "gave-up" } : current)),
  };
}

export function FinaleOrb({ className }: { className?: string }) {
  const { isCalm } = useMotionPreference();
  const { stage, onReady, onFallback } = useOrbStage(isCalm);
  const isLive = stage.kind === "live";

  return (
    <div
      aria-hidden
      data-orb={isLive ? "3d" : "static"}
      data-orb-reason={stage.kind === "static" ? stage.reason : undefined}
      className={cn("relative mx-auto aspect-[4/3] w-40 sm:w-48", className)}
    >
      <AssistantOrbIllustration
        gradientId="aw-finale-orb"
        className={cn("transition-[opacity,visibility] duration-700 ease-out", isLive && "invisible opacity-0")}
      />
      {stage.kind === "loading" || isLive ? (
        <FinaleOrbScene
          className={cn(
            "pointer-events-none absolute -inset-[25%] transition-opacity duration-1000 ease-out",
            isLive ? "opacity-100" : "opacity-0",
          )}
          onReady={onReady}
          onFallback={onFallback}
        />
      ) : null}
    </div>
  );
}
