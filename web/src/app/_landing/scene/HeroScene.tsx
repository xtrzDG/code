"use client";

/**
 * The landing hero's 3D scene (react-three-fiber): the assistant's orb with
 * the channels' message bubbles orbiting it. Loaded lazily by HeroVisual
 * (its own chunk, with three.js) only on devices that get the 3D hero.
 *
 * - The camera leans towards the mouse (parallax) and pulls back and rises
 *   while the hero scrolls away; the scene fades with it.
 * - Rendering stops while the scene is off screen.
 * - A frame-rate watch lowers the resolution if frames are slow, and hands
 *   over to the still picture if they stay slow, as does a lost WebGL
 *   context or any error while setting up.
 */

import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState, type RefObject } from "react";

import { useResolvedScheme } from "@/components/theme/useResolvedScheme";
import { CAMERA_DISTANCE, cameraForScroll, pointerToParallax } from "@/lib/heroScene";
import { approach, clamp } from "@/lib/motionMath";

import { AssistantOrb } from "./AssistantOrb";
import { ChannelBubbles } from "./ChannelBubbles";
import { SceneAtmosphere } from "./SceneAtmosphere";
import { FrameWatch, SceneBoundary } from "./sceneGuards";
import { SCENE_PALETTES } from "./scenePalette";

export interface HeroSceneProps {
  /** The first frame is on screen. */
  onReady: () => void;
  /** The scene cannot run well here: show the still picture instead. */
  onFallback: () => void;
  className?: string;
}

interface Pointer {
  x: number;
  y: number;
}

function CameraRig({ pointer, scroll, fadeTarget }: { pointer: RefObject<Pointer>; scroll: RefObject<number>; fadeTarget: RefObject<HTMLDivElement | null> }) {
  const shownFade = useRef(1);
  useFrame((state, delta) => {
    const view = cameraForScroll(scroll.current);
    const camera = state.camera;
    camera.position.x = approach(camera.position.x, pointer.current.x * 0.9, 2.4, delta);
    camera.position.y = approach(camera.position.y, pointer.current.y * 0.6 + view.y, 2.4, delta);
    camera.position.z = approach(camera.position.z, view.z, 3, delta);
    camera.lookAt(0, view.y * 0.35, 0);
    const element = fadeTarget.current;
    if (element && Math.abs(shownFade.current - view.fade) > 0.004) {
      shownFade.current = view.fade;
      element.style.opacity = String(view.fade);
    }
  });
  return null;
}

export default function HeroScene({ onReady, onFallback, className }: HeroSceneProps) {
  const wrapper = useRef<HTMLDivElement>(null);
  const fadeTarget = useRef<HTMLDivElement>(null);
  const pointer = useRef<Pointer>({ x: 0, y: 0 });
  const scroll = useRef(0);
  const pulse = useRef(0);
  const [isOnScreen, setOnScreen] = useState(true);
  const palette = SCENE_PALETTES[useResolvedScheme()];

  useEffect(() => {
    const element = wrapper.current;
    if (!element) {
      return;
    }
    const onPointerMove = (event: PointerEvent) => {
      pointer.current = pointerToParallax(event.clientX, event.clientY, window.innerWidth, window.innerHeight);
    };
    const onScroll = () => {
      const box = element.getBoundingClientRect();
      scroll.current = clamp(-box.top / Math.max(box.height, 1), 0, 1);
    };
    onScroll();
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    const observer = new IntersectionObserver((entries) => setOnScreen(entries.some((entry) => entry.isIntersecting)));
    observer.observe(element);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("scroll", onScroll);
      observer.disconnect();
    };
  }, []);

  return (
    <div ref={wrapper} aria-hidden className={className}>
      <div ref={fadeTarget} className="size-full">
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
            <CameraRig pointer={pointer} scroll={scroll} fadeTarget={fadeTarget} />
            <FrameWatch onReady={onReady} onFallback={onFallback} />
            {/* A little right of centre: the outer bubbles keep clear of the headline beside the scene. */}
            <group position={[0.3, 0, 0]}>
              <SceneAtmosphere palette={palette} />
              <AssistantOrb palette={palette} pulse={pulse} />
              <ChannelBubbles palette={palette} pulse={pulse} />
            </group>
          </Canvas>
        </SceneBoundary>
      </div>
    </div>
  );
}
