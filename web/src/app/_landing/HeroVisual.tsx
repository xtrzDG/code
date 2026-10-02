"use client";

/**
 * The hero's picture: the still one (HeroFallback) right away, and on a
 * capable device the 3D scene, loaded once the page is idle and faded in
 * over it once its first frame is drawn. Reduced motion (also switched on
 * while the page is open), no WebGL, data saver or a weak device keep the
 * still picture; so does a scene that turns out too slow or fails.
 *
 * `data-scene` says which one is showing ("static" or "3d").
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import { heroSceneMode, type DeviceSignals } from "@/lib/heroScene";
import { cn } from "@/lib/cn";

import { HeroFallback } from "./HeroFallback";

const HeroScene = dynamic(() => import("./scene/HeroScene"), { ssr: false });

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function hasWebGl(): boolean {
  try {
    const probe = document.createElement("canvas");
    const context = probe.getContext("webgl2") ?? probe.getContext("webgl");
    context?.getExtension("WEBGL_lose_context")?.loseContext();
    return context !== null;
  } catch {
    return false;
  }
}

function readSignals(): DeviceSignals {
  const browser = navigator as Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };
  return {
    prefersReducedMotion: window.matchMedia(REDUCED_MOTION_QUERY).matches,
    hasWebGl: hasWebGl(),
    cores: browser.hardwareConcurrency || undefined,
    memoryGb: browser.deviceMemory,
    saveData: browser.connection?.saveData,
  };
}

/** Runs `task` when the browser is idle (or soon, where it cannot tell). */
function whenIdle(task: () => void): () => void {
  if ("requestIdleCallback" in window) {
    const handle = window.requestIdleCallback(task, { timeout: 2000 });
    return () => window.cancelIdleCallback(handle);
  }
  const timer = globalThis.setTimeout(task, 300);
  return () => globalThis.clearTimeout(timer);
}

export function HeroVisual({ label, className }: { label: string; className?: string }) {
  const [wantsScene, setWantsScene] = useState(false);
  const [isSceneLive, setSceneLive] = useState(false);
  const [hasGivenUp, setGivenUp] = useState(false);

  useEffect(() => {
    if (hasGivenUp || heroSceneMode(readSignals()).mode !== "3d") {
      return;
    }
    const cancel = whenIdle(() => setWantsScene(true));
    const media = window.matchMedia(REDUCED_MOTION_QUERY);
    const onMotionChange = () => {
      if (media.matches) {
        setWantsScene(false);
        setSceneLive(false);
      }
    };
    media.addEventListener("change", onMotionChange);
    return () => {
      cancel();
      media.removeEventListener("change", onMotionChange);
    };
  }, [hasGivenUp]);

  const showScene = wantsScene && !hasGivenUp;
  const isLive = showScene && isSceneLive;

  return (
    <div role="img" aria-label={label} data-scene={isLive ? "3d" : "static"} className={cn("relative aspect-square w-full", className)}>
      <HeroFallback
        className={cn("transition-[opacity,visibility] duration-700 ease-out", isLive && "invisible opacity-0")}
      />
      {showScene ? (
        <HeroScene
          className={cn(
            "pointer-events-none absolute -inset-[30%] transition-opacity duration-1000 ease-out",
            isLive ? "opacity-100" : "opacity-0",
          )}
          onReady={() => setSceneLive(true)}
          onFallback={() => {
            setGivenUp(true);
            setSceneLive(false);
          }}
        />
      ) : null}
    </div>
  );
}
