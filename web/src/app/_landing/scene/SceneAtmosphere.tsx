"use client";

/**
 * What surrounds the orb: the bubbles' orbits drawn as faint rings, a slow
 * cloud of dust specks, and the lights and reflections the glass shell
 * catches (a studio environment generated on the GPU, nothing downloaded).
 */

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import { BufferGeometry, Float32BufferAttribute, PMREMGenerator, type Points } from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

import { dustPositions, ORBITS } from "@/lib/heroScene";

import type { ScenePalette } from "./scenePalette";
import { glowTexture } from "./sceneTextures";

/** The distinct orbits (two bubbles share each). */
const RINGS = ORBITS.filter(
  (orbit, index) => ORBITS.findIndex((other) => other.radius === orbit.radius && other.tilt === orbit.tilt) === index,
);

function OrbitRings({ palette }: { palette: ScenePalette }) {
  return (
    <group>
      {RINGS.map((orbit) => (
        // The ring's plane: x/z circle, tilted around x, then turned around y (as orbitPosition does).
        <group key={orbit.channel} rotation={[0, orbit.yaw, 0]}>
          <mesh rotation={[Math.PI / 2 + orbit.tilt, 0, 0]}>
            <torusGeometry args={[orbit.radius, 0.004, 6, 220]} />
            <meshBasicMaterial color={palette.ring} transparent opacity={palette.ringOpacity} depthWrite={false} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function Dust({ palette }: { palette: ScenePalette }) {
  const points = useRef<Points>(null);
  const geometry = useMemo(() => {
    const dust = new BufferGeometry();
    dust.setAttribute("position", new Float32BufferAttribute(dustPositions(220, 2.2, 5.2), 3));
    return dust;
  }, []);
  const sprite = useMemo(() => glowTexture(32), []);
  useEffect(
    () => () => {
      geometry.dispose();
      sprite.dispose();
    },
    [geometry, sprite],
  );
  useFrame((_, delta) => {
    if (points.current) {
      points.current.rotation.y += delta * 0.02;
    }
  });
  return (
    <points ref={points} geometry={geometry}>
      <pointsMaterial
        map={sprite}
        color={palette.dust}
        size={0.06}
        sizeAttenuation
        transparent
        opacity={palette.dustOpacity}
        depthWrite={false}
      />
    </points>
  );
}

/** Reflections for the glass shell: a neutral studio room, blurred once on the GPU. */
function StudioEnvironment() {
  const gl = useThree((state) => state.gl);
  const scene = useThree((state) => state.scene);
  useEffect(() => {
    const generator = new PMREMGenerator(gl);
    const room = new RoomEnvironment();
    const target = generator.fromScene(room, 0.04);
    scene.environment = target.texture;
    return () => {
      scene.environment = null;
      target.dispose();
      room.dispose();
      generator.dispose();
    };
  }, [gl, scene]);
  return null;
}

export function SceneAtmosphere({ palette }: { palette: ScenePalette }) {
  return (
    <>
      <StudioEnvironment />
      <ambientLight intensity={0.6} />
      <directionalLight position={[3, 4, 5]} intensity={1.6} />
      <pointLight position={[-3, -2, 2.5]} intensity={18} color={palette.orbColors[1]} />
      <OrbitRings palette={palette} />
      <Dust palette={palette} />
    </>
  );
}
