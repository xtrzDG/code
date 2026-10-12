"use client";

/**
 * The assistant above the finale's "Your assistant is live!": everyone
 * first sees the orb drawn flat (AssistantOrbIllustration). Where the
 * landing hero would get its 3D scene (the same rules, lib/heroDevice.ts:
 * no reduced motion, the wide layout, a capable device, WebGL) the landing's
 * orb itself, three.js in a chunk of its own, is fetched once the browser is
 * idle and fades in over the drawing after its first frame, in the same box
 * (no layout shift). Reduced motion (the device's or the cabinet's own),
 * a narrower window, a slow frame rate or a lost WebGL context go back to
 * the drawing.
 *
 * `data-orb` says which one is showing ("static" or "3d"); `data-orb-reason`
 * why the drawing stays.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { WIDE_LAYOUT_QUERY, afterNextPaint, hasWebGl, readDeviceSignals, whenIdle } from "@/app/_landing/heroWaits";
import { AssistantOrbIllustration } from "@/components/illustrations";
import { useMotionPreference } from "@/components/motion/MotionPreference";
import { cn } from "@/lib/cn";
import { heroPlan, type PosterReason } from "@/lib/heroDevice";
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
      const plan = heroPlan(readDeviceSignals());
      if (plan.kind === "poster") {
        stop(plan.reason);
        return;
      }
      cancel = inSequence([whenIdle], () => (hasWebGl() ? setStage({ kind: "loading" }) : stop("no-webgl")));
    });
    const wide = window.matchMedia(WIDE_LAYOUT_QUERY);
    const onChange = () => {
      if (!wide.matches) {
        stop("narrow-screen");
      }
    };
    wide.addEventListener("change", onChange);
    return () => {
      cancel();
      wide.removeEventListener("change", onChange);
    };
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
