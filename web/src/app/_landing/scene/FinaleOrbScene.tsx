"use client";

/**
 * The landing hero's orb, its channels' bubbles orbiting it, at the end of
 * the setup tunnel: the assistant that has just gone live. Loaded lazily by
 * the finale (components/setup/finale/FinaleOrb.tsx, its own chunk with
 * three.js, shared with the hero's) only where the hero would get its 3D
 * scene too. No parallax and no scroll: the camera stands still.
 *
 * Rendering stops while the orb is off screen; a slow frame rate, a lost
 * WebGL context or an error while setting up hands over to the still
 * picture (sceneGuards.tsx).
 */

import { Canvas } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";

import { useResolvedScheme } from "@/components/theme/useResolvedScheme";
import { CAMERA_DISTANCE } from "@/lib/heroScene";

import { AssistantOrb } from "./AssistantOrb";
import { ChannelBubbles } from "./ChannelBubbles";
import { SceneAtmosphere } from "./SceneAtmosphere";
import { FrameWatch, SceneBoundary } from "./sceneGuards";
import { SCENE_PALETTES } from "./scenePalette";

export interface FinaleOrbSceneProps {
  /** The first frame is on screen. */
  onReady: () => void;
  /** The scene cannot run well here: show the still picture instead. */
  onFallback: () => void;
  className?: string;
}

export default function FinaleOrbScene({ onReady, onFallback, className }: FinaleOrbSceneProps) {
  const wrapper = useRef<HTMLDivElement>(null);
  const pulse = useRef(0);
  const [isOnScreen, setOnScreen] = useState(true);
  const palette = SCENE_PALETTES[useResolvedScheme()];

  useEffect(() => {
    const element = wrapper.current;
    if (!element) {
      return;
    }
    const observer = new IntersectionObserver((entries) => setOnScreen(entries.some((entry) => entry.isIntersecting)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={wrapper} aria-hidden className={className}>
      <SceneBoundary onError={onFallback}>
        <Canvas
          dpr={[1, 2]}
          flat
          frameloop={isOnScreen ? "always" : "never"}
          camera={{ position: [0, 0, CAMERA_DISTANCE], fov: 34, near: 0.1, far: 80 }}
          gl={{ antialias: true, alpha: true, powerPreference: "default" }}
          style={{ pointerEvents: "none" }}
          onCreated={({ gl }) => {
            gl.domElement.addEventListener(
              "webglcontextlost",
              (event) => {
                event.preventDefault();
                onFallback();
              },
              { once: true },
            );
          }}
        >
          <FrameWatch onReady={onReady} onFallback={onFallback} />
          <SceneAtmosphere palette={palette} />
          <AssistantOrb palette={palette} pulse={pulse} />
          <ChannelBubbles palette={palette} pulse={pulse} />
        </Canvas>
      </SceneBoundary>
    </div>
  );
}
