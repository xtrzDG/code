/**
 * The landing hero's 3D scene, as numbers: whether this device gets the
 * scene or the still picture, where each channel's message bubble orbits
 * the assistant, how scrolling moves the camera, and the colours of each
 * scheme. Pure functions; the scene (app/_landing/scene/) only draws them.
 */

import { clamp, medianOf, roundTo } from "./motionMath";

export const CHANNEL_MARK_KEYS = ["whatsapp", "telegram", "instagram", "messenger", "web_chat", "phone"] as const;

export type ChannelMarkKey = (typeof CHANNEL_MARK_KEYS)[number];

/** What the browser tells about itself, read once on the landing page. */
export interface DeviceSignals {
  prefersReducedMotion: boolean;
  hasWebGl: boolean;
  /** navigator.hardwareConcurrency (logical cores); undefined when the browser hides it. */
  cores?: number;
  /** navigator.deviceMemory in GB (Chromium only). */
  memoryGb?: number;
  /** The visitor asked for less data (navigator.connection.saveData). */
  saveData?: boolean;
}

export type HeroSceneMode = "3d" | "static";

export type StaticReason = "reduced-motion" | "no-webgl" | "save-data" | "low-power";

/**
 * The 3D scene runs only where it is wanted and will be smooth: no reduced
 * motion, WebGL present, no data saver, and not a weak device (fewer than
 * four cores or under 4 GB of memory). Everyone else sees the still picture.
 */
export function heroSceneMode(signals: DeviceSignals): { mode: HeroSceneMode; reason?: StaticReason } {
  if (signals.prefersReducedMotion) {
    return { mode: "static", reason: "reduced-motion" };
  }
  if (!signals.hasWebGl) {
    return { mode: "static", reason: "no-webgl" };
  }
  if (signals.saveData) {
    return { mode: "static", reason: "save-data" };
  }
  if ((signals.cores !== undefined && signals.cores < 4) || (signals.memoryGb !== undefined && signals.memoryGb < 4)) {
    return { mode: "static", reason: "low-power" };
  }
  return { mode: "3d" };
}

/** One bubble's path: a tilted circle around the orb. */
export interface Orbit {
  channel: ChannelMarkKey;
  /** Distance from the orb's centre (scene units; the orb's radius is 1). */
  radius: number;
  /** Tilt of the orbit's plane around the x axis (radians). */
  tilt: number;
  /** Turn of the orbit's plane around the y axis (radians). */
  yaw: number;
  /** Radians per second (negative: the other way round). */
  speed: number;
  /** Where on the circle the bubble starts (radians). */
  phase: number;
}

/** Six bubbles on three tilted orbits, two per orbit on opposite sides. */
export const ORBITS: readonly Orbit[] = [
  { channel: "whatsapp", radius: 2.05, tilt: 0.32, yaw: 0, speed: 0.22, phase: 0.3 },
  { channel: "instagram", radius: 2.05, tilt: 0.32, yaw: 0, speed: 0.22, phase: 0.3 + Math.PI },
  { channel: "telegram", radius: 2.45, tilt: -0.42, yaw: 0.9, speed: -0.17, phase: 1.6 },
  { channel: "phone", radius: 2.45, tilt: -0.42, yaw: 0.9, speed: -0.17, phase: 1.6 + Math.PI },
  { channel: "messenger", radius: 2.8, tilt: 0.18, yaw: -0.7, speed: 0.13, phase: 2.6 },
  { channel: "web_chat", radius: 2.8, tilt: 0.18, yaw: -0.7, speed: 0.13, phase: 2.6 + Math.PI },
];

export type Vector3 = readonly [number, number, number];

/** Where a bubble is `seconds` after the start: on its circle, plus a slow bob. */
export function orbitPosition(orbit: Orbit, seconds: number): Vector3 {
  const angle = orbit.phase + orbit.speed * seconds;
  // A point on a flat circle…
  const flatX = orbit.radius * Math.cos(angle);
  const flatZ = orbit.radius * Math.sin(angle);
  // …tilted around x…
  const tiltedY = flatZ * Math.sin(orbit.tilt);
  const tiltedZ = flatZ * Math.cos(orbit.tilt);
  // …and turned around y.
  const x = flatX * Math.cos(orbit.yaw) + tiltedZ * Math.sin(orbit.yaw);
  const z = -flatX * Math.sin(orbit.yaw) + tiltedZ * Math.cos(orbit.yaw);
  const bob = 0.08 * Math.sin(seconds * 1.1 + orbit.phase * 3);
  return [roundTo(x, 5), roundTo(tiltedY + bob, 5), roundTo(z, 5)];
}

/** One message every 1.1 s, the channels in turn; each takes 0.95 s to reach the orb. */
const MESSAGE_PULSE = { gapSeconds: 1.1, travelSeconds: 0.95 } as const;

/** 0…1 while bubble `index` (of `count`) has a message on its way to the orb at `seconds`, else null. */
export function messagePulseProgress(index: number, seconds: number, count: number): number | null {
  const period = MESSAGE_PULSE.gapSeconds * count;
  const local = (seconds - index * MESSAGE_PULSE.gapSeconds) % period;
  if (local < 0 || local > MESSAGE_PULSE.travelSeconds) {
    return null;
  }
  return local / MESSAGE_PULSE.travelSeconds;
}

/** Bubbles in front are clear, those behind the orb fade (depth): opacity for a z. */
export function depthOpacity(z: number, maxRadius: number): number {
  return roundTo(0.35 + 0.65 * clamp((z + maxRadius) / (2 * maxRadius), 0, 1), 4);
}

/**
 * How far the camera stands from the orb (scene units). With a 34° field of
 * view it sees ±3.7 units: the outer bubbles fit in a canvas 1.6 times the
 * size of the hero's picture box, with the orb about half the box wide.
 */
export const CAMERA_DISTANCE = 12;

/**
 * The camera as the hero scrolls away (0: hero on screen, 1: scrolled past):
 * it pulls back and rises, the scene sinks and fades.
 */
export function cameraForScroll(progress: number): { z: number; y: number; fade: number } {
  const p = clamp(progress, 0, 1);
  return { z: roundTo(CAMERA_DISTANCE + p * 4, 4), y: roundTo(p * 1.8, 4), fade: roundTo(1 - p * 0.85, 4) };
}

/** Pointer position over the window as -1…1 on both axes (up is +1). */
export function pointerToParallax(clientX: number, clientY: number, width: number, height: number): { x: number; y: number } {
  if (width <= 0 || height <= 0) {
    return { x: 0, y: 0 };
  }
  return {
    x: roundTo(clamp((clientX / width) * 2 - 1, -1, 1), 4),
    y: roundTo(clamp(1 - (clientY / height) * 2, -1, 1), 4),
  };
}

/** A repeatable pseudo-random sequence (mulberry32), so the dust looks the same on every visit. */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let t = state;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** `count` specks of dust in a shell between `inner` and `outer` around the orb, as x, y, z triples. */
export function dustPositions(count: number, inner: number, outer: number, seed = 7): Float32Array {
  const random = seededRandom(seed);
  const positions = new Float32Array(count * 3);
  for (let index = 0; index < count; index += 1) {
    const theta = random() * Math.PI * 2;
    const cosPhi = random() * 2 - 1;
    const sinPhi = Math.sqrt(1 - cosPhi * cosPhi);
    const radius = inner + (outer - inner) * Math.cbrt(random());
    positions[index * 3] = radius * sinPhi * Math.cos(theta);
    positions[index * 3 + 1] = radius * cosPhi * 0.7;
    positions[index * 3 + 2] = radius * sinPhi * Math.sin(theta);
  }
  return positions;
}

/** Whether frames take too long: the median of the sampled frame times above `budgetMs`. */
export function isFrameRateLow(frameTimesMs: readonly number[], budgetMs = 1000 / 40, minimumSamples = 60): boolean {
  if (frameTimesMs.length < minimumSamples) {
    return false;
  }
  return medianOf(frameTimesMs) > budgetMs;
}
