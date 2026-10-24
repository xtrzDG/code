"use client";

/**
 * The assistant in the middle of the scene: the flowing orb (orbShader.ts),
 * a thin glass shell that catches reflections, a halo ring turning around
 * it and a soft glow behind. `pulse` (0…1, set by MessagePulses) brightens
 * the core when a message reaches it.
 */

import { useFrame } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type RefObject } from "react";
import { AdditiveBlending, Color, NormalBlending, type Mesh } from "three";

import { ORB_FRAGMENT_SHADER, ORB_VERTEX_SHADER } from "./orbShader";
import type { ScenePalette } from "./scenePalette";
import { glowTexture } from "./sceneTextures";

export function AssistantOrb({ palette, pulse }: { palette: ScenePalette; pulse: RefObject<number> }) {
  const halo = useRef<Mesh>(null);
  const glow = useMemo(() => glowTexture(), []);
  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
      uPulse: { value: 0 },
      uColorA: { value: new Color() },
      uColorB: { value: new Color() },
      uColorC: { value: new Color() },
    }),
    [],
  );

  useEffect(() => {
    uniforms.uColorA.value.set(palette.orbColors[0]);
    uniforms.uColorB.value.set(palette.orbColors[1]);
    uniforms.uColorC.value.set(palette.orbColors[2]);
  }, [palette, uniforms]);

  useEffect(() => () => glow.dispose(), [glow]);

  useFrame((state, delta) => {
    uniforms.uTime.value = state.clock.elapsedTime;
    uniforms.uPulse.value = pulse.current;
    if (halo.current) {
      halo.current.rotation.z += delta * 0.25;
    }
  });

  return (
    <group>
      <sprite scale={4.2} renderOrder={-1}>
        <spriteMaterial
          map={glow}
          color={palette.glow}
          opacity={palette.glowOpacity}
          transparent
          depthWrite={false}
          blending={palette.glowAdditive ? AdditiveBlending : NormalBlending}
        />
      </sprite>
      <mesh>
        <sphereGeometry args={[1, 96, 96]} />
        <shaderMaterial
          uniforms={uniforms}
          vertexShader={ORB_VERTEX_SHADER}
          fragmentShader={ORB_FRAGMENT_SHADER}
        />
      </mesh>
      <mesh scale={1.16}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshPhysicalMaterial
          color="#ffffff"
          roughness={0.06}
          metalness={0}
          clearcoat={1}
          clearcoatRoughness={0.04}
          iridescence={0.7}
          iridescenceIOR={1.3}
          envMapIntensity={1.6}
          transparent
          opacity={palette.shellOpacity}
          depthWrite={false}
        />
      </mesh>
      <mesh ref={halo} rotation={[1.2, 0.3, 0]}>
        <torusGeometry args={[1.5, 0.008, 8, 160]} />
        <meshBasicMaterial color={palette.ring} transparent opacity={palette.ringOpacity * 2} depthWrite={false} />
      </mesh>
    </group>
  );
}
