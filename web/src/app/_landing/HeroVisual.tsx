"use client";

/**
 * The hero's picture. Everyone first sees the poster (HeroFallback: the
 * scene's composition in HTML and CSS, rendered on the server, animated with
 * CSS). On a capable device in the wide layout (lib/heroDevice.ts) the 3D
 * scene, a separate chunk with three.js, is fetched only after the page has
 * loaded and painted, once the browser is idle and the hero is on screen,
 * and fades in over the poster after its first frame, in the same box (no
 * layout shift). Turning reduced motion on or narrowing the window to the
 * phone layout goes back to the poster; so does a scene that turns out too
 * slow or fails.
 *
 * `data-scene` says which one is showing ("static" or "3d");
 * `data-scene-reason` why the poster stays (see PosterReason).
 */

import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type RefObject } from "react";

import { heroPlan, type PosterReason } from "@/lib/heroDevice";
import { inSequence } from "@/lib/waits";
import { cn } from "@/lib/cn";

import { HeroFallback } from "./HeroFallback";
import {
  REDUCED_MOTION_QUERY,
  WIDE_LAYOUT_QUERY,
  afterNextPaint,
  afterPageLoad,
  hasWebGl,
  readDeviceSignals,
  whenIdle,
  whenOnScreen,
} from "./heroWaits";

const HeroScene = dynamic(() => import("./scene/HeroScene"), { ssr: false });

type Stage =
  | { kind: "waiting" }
  | { kind: "poster"; reason: PosterReason }
  | { kind: "loading" }
  | { kind: "live" };

/** Runs the loading rules once; `stop` goes back to the poster for good. */
function useSceneStage(box: RefObject<HTMLDivElement | null>) {
  const [stage, setStage] = useState<Stage>({ kind: "waiting" });

  useEffect(() => {
    let cancel: () => void = () => undefined;
    const stop = (reason: PosterReason) => {
      cancel();
      setStage({ kind: "poster", reason });
    };
    // Decided after hydration's first frame: the server cannot know the device.
    cancel = afterNextPaint(() => {
      const plan = heroPlan(readDeviceSignals());
      if (plan.kind === "poster") {
        stop(plan.reason);
        return;
      }
      cancel = inSequence([afterPageLoad, whenIdle, whenOnScreen(box.current)], () => {
        if (hasWebGl()) {
          setStage({ kind: "loading" });
        } else {
          stop("no-webgl");
        }
      });
    });
    const motion = window.matchMedia(REDUCED_MOTION_QUERY);
    const wide = window.matchMedia(WIDE_LAYOUT_QUERY);
    const onChange = () => {
      if (motion.matches) {
        stop("reduced-motion");
      } else if (!wide.matches) {
        stop("narrow-screen");
      }
    };
    motion.addEventListener("change", onChange);
    wide.addEventListener("change", onChange);
    return () => {
      cancel();
      motion.removeEventListener("change", onChange);
      wide.removeEventListener("change", onChange);
    };
  }, [box]);

  return {
    stage,
    onReady: () => setStage((current) => (current.kind === "loading" ? { kind: "live" } : current)),
    onFallback: () => setStage({ kind: "poster", reason: "gave-up" }),
  };
}

export function HeroVisual({ label, className }: { label: string; className?: string }) {
  const box = useRef<HTMLDivElement>(null);
  const { stage, onReady, onFallback } = useSceneStage(box);
  const isLive = stage.kind === "live";

  return (
    <div
      ref={box}
      role="img"
      aria-label={label}
      data-scene={isLive ? "3d" : "static"}
      data-scene-reason={stage.kind === "poster" ? stage.reason : undefined}
      className={cn("relative aspect-square w-full", className)}
    >
      <HeroFallback className={cn("transition-[opacity,visibility] duration-700 ease-out", isLive && "invisible opacity-0")} />
      {stage.kind === "loading" || isLive ? (
        <HeroScene
          className={cn(
            "pointer-events-none absolute -inset-[30%] transition-opacity duration-1000 ease-out",
            isLive ? "opacity-100" : "opacity-0",
          )}
          onReady={onReady}
          onFallback={onFallback}
        />
      ) : null}
    </div>
  );
}
