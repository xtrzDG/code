"use client";

/**
 * The six channels' message bubbles orbiting the assistant. Every bubble
 * faces the camera, fades when it passes behind the orb, and in turn sends
 * a small light (a message) into the orb, which glows up as it arrives.
 */

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type RefObject } from "react";
import { AdditiveBlending, NormalBlending, type Mesh, type MeshBasicMaterial, type Sprite, type SpriteMaterial } from "three";

import { depthOpacity, messagePulseProgress, ORBITS, orbitPosition } from "@/lib/heroScene";
import { clamp } from "@/lib/motionMath";

import type { ScenePalette } from "./scenePalette";
import { BUBBLE_TEXTURE, bubbleTexture, glowTexture } from "./sceneTextures";

const BUBBLE_WIDTH = 1.05;
const BUBBLE_HEIGHT = (BUBBLE_WIDTH * BUBBLE_TEXTURE.height) / BUBBLE_TEXTURE.width;
const MAX_RADIUS = Math.max(...ORBITS.map((orbit) => orbit.radius));

export function ChannelBubbles({ palette, pulse }: { palette: ScenePalette; pulse: RefObject<number> }) {
  const bubbles = useRef<(Mesh | null)[]>([]);
  const lights = useRef<(Sprite | null)[]>([]);
  const textures = useMemo(() => ORBITS.map((orbit) => bubbleTexture(orbit.channel, palette)), [palette]);
  const glow = useMemo(() => glowTexture(64), []);

  useEffect(() => () => textures.forEach((texture) => texture.dispose()), [textures]);
  useEffect(() => () => glow.dispose(), [glow]);

  useFrame((state, delta) => {
    const seconds = state.clock.elapsedTime;
    let arriving = 0;
    ORBITS.forEach((orbit, index) => {
      const [x, y, z] = orbitPosition(orbit, seconds);
      const bubble = bubbles.current[index];
      const progress = messagePulseProgress(index, seconds, ORBITS.length);
      if (bubble) {
        bubble.position.set(x, y, z);
        bubble.quaternion.copy(state.camera.quaternion);
        // A bubble swells a little as it sends its message.
        const send = progress === null ? 0 : Math.max(0, 1 - progress * 3);
        bubble.scale.setScalar(1 + send * 0.08);
        (bubble.material as MeshBasicMaterial).opacity = depthOpacity(z, MAX_RADIUS);
      }
      const light = lights.current[index];
      if (light) {
        light.visible = progress !== null;
        if (progress !== null) {
          // Accelerates towards the orb.
          const travel = progress * progress * progress;
          light.position.set(x * (1 - travel), y * (1 - travel), z * (1 - travel));
          (light.material as SpriteMaterial).opacity = Math.sin(progress * Math.PI) * 0.95;
          if (progress > 0.85) {
            arriving = Math.max(arriving, (progress - 0.85) / 0.15);
          }
        }
      }
    });
    pulse.current = Math.max(arriving, clamp(pulse.current - delta * 2.2, 0, 1));
  });

  return (
    <group>
      {ORBITS.map((orbit, index) => (
        <mesh
          key={orbit.channel}
          ref={(mesh) => {
            bubbles.current[index] = mesh;
          }}
          renderOrder={2}
        >
          <planeGeometry args={[BUBBLE_WIDTH, BUBBLE_HEIGHT]} />
          <meshBasicMaterial map={textures[index]} transparent depthWrite={false} toneMapped={false} />
        </mesh>
      ))}
      {ORBITS.map((orbit, index) => (
        <sprite
          key={`${orbit.channel}-pulse`}
          ref={(sprite) => {
            lights.current[index] = sprite;
          }}
          scale={0.34}
          visible={false}
          renderOrder={3}
        >
          <spriteMaterial
            map={glow}
            color={palette.pulse}
            transparent
            depthWrite={false}
            blending={palette.glowAdditive ? AdditiveBlending : NormalBlending}
          />
        </sprite>
      ))}
    </group>
  );
}
