/**
 * The tunnel's depth, as numbers: the rings of the background (one per
 * step ahead, the owner moving one ring deeper with every step) and the
 * confetti of the finale. Pure functions; components/setup/ draws them.
 */

/** Rings in view ahead of the owner. */
export const RING_COUNT = 7;
/** Distance between two rings (px of CSS translateZ). */
export const RING_GAP = 260;

export interface Ring {
  /** Stable across steps, so a ring glides forward instead of being redrawn. */
  key: number;
  /** translateZ in px: 0 is the ring around the screen, negative is deeper. */
  z: number;
  /** Fades with depth; the ring the owner just passed is gone. */
  opacity: number;
}

/**
 * The rings around step `index`: the one just passed (behind the viewer,
 * invisible, so moving back brings it in smoothly) and RING_COUNT ahead.
 */
export function ringsAt(index: number, count: number = RING_COUNT): Ring[] {
  const rings: Ring[] = [];
  for (let key = index - 1; key < index + count; key += 1) {
    const depth = key - index;
    rings.push({
      key,
      z: -depth * RING_GAP,
      opacity: depth < 0 ? 0 : Math.round(Math.max(0, 1 - depth / count) * 100) / 100,
    });
  }
  return rings;
}

export interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  rotation: number;
  spin: number;
  size: number;
  color: string;
  /** Seconds left before it is gone. */
  life: number;
}

/** A small deterministic random source (mulberry32), so a burst can be tested. */
export function seededRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

/** A burst of `count` pieces from (x, y), thrown up and out in every direction. */
export function burst(
  count: number,
  origin: { x: number; y: number },
  palette: readonly string[],
  random: () => number = Math.random,
): Particle[] {
  const particles: Particle[] = [];
  for (let index = 0; index < count; index += 1) {
    const angle = random() * Math.PI * 2;
    const speed = 260 + random() * 520;
    particles.push({
      x: origin.x,
      y: origin.y,
      vx: Math.cos(angle) * speed,
      // Biased upwards: a burst rises before it falls.
      vy: Math.sin(angle) * speed - 380,
      rotation: random() * Math.PI,
      spin: (random() - 0.5) * 12,
      size: 5 + random() * 7,
      color: palette[index % Math.max(palette.length, 1)] ?? "#5b5bd6",
      life: 1.8 + random() * 1.4,
    });
  }
  return particles;
}

export const GRAVITY = 900;
const AIR_DRAG = 1.6;

/** One particle `seconds` later: drag, gravity and spin. */
export function advance(particle: Particle, seconds: number): Particle {
  const drag = Math.exp(-AIR_DRAG * seconds);
  return {
    ...particle,
    vx: particle.vx * drag,
    vy: particle.vy * drag + GRAVITY * seconds,
    x: particle.x + particle.vx * seconds,
    y: particle.y + particle.vy * seconds,
    rotation: particle.rotation + particle.spin * seconds,
    life: particle.life - seconds,
  };
}

/** The particles still worth drawing (alive and not far below the screen). */
export function alive(particles: readonly Particle[], height: number): Particle[] {
  return particles.filter((particle) => particle.life > 0 && particle.y < height + 40);
}
