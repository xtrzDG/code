/**
 * Which hero picture a visitor's device gets. Everyone first sees the poster
 * (server-rendered HTML and CSS, animated unless motion is reduced); the 3D
 * scene (three.js, about 240 KB) is fetched only after the page has loaded
 * and the browser is idle, and only where it is wanted and will run
 * smoothly. Pure: HeroVisual reads the signals from the browser.
 */

/** What the browser tells about itself, read once on the landing page. */
export interface DeviceSignals {
  prefersReducedMotion: boolean;
  /** The wide layout, where the scene stands beside the headline (min-width: 64rem). */
  isWideLayout: boolean;
  /** The primary pointer is a finger (pointer: coarse): a phone or a tablet. */
  isCoarsePointer: boolean;
  /** navigator.hardwareConcurrency (logical cores); undefined when the browser hides it. */
  cores?: number;
  /** navigator.deviceMemory in GB (Chromium only). */
  memoryGb?: number;
  /** The visitor asked for less data (navigator.connection.saveData). */
  saveData?: boolean;
  /** navigator.connection.effectiveType: "slow-2g", "2g", "3g" or "4g" (Chromium only). */
  effectiveType?: string;
}

/** Why a device keeps the poster ("no-webgl" and "gave-up" are found out later, by HeroVisual). */
export type PosterReason =
  | "reduced-motion"
  | "save-data"
  | "narrow-screen"
  | "slow-network"
  | "low-power"
  | "no-webgl"
  | "gave-up";

export type HeroPlan = { kind: "scene" } | { kind: "poster"; reason: PosterReason };

/** Below these any device keeps the poster. */
const MIN_CORES = 4;
const MIN_MEMORY_GB = 4;
/** A touch device runs the page, the browser and the scene on a phone-class chip: it needs more. */
const MIN_TOUCH_CORES = 6;
const MIN_TOUCH_MEMORY_GB = 6;
const SLOW_NETWORKS: ReadonlySet<string> = new Set(["slow-2g", "2g", "3g"]);

function isBelow(value: number | undefined, minimum: number): boolean {
  return value !== undefined && value < minimum;
}

function isLowPower(signals: DeviceSignals): boolean {
  if (isBelow(signals.cores, MIN_CORES) || isBelow(signals.memoryGb, MIN_MEMORY_GB)) {
    return true;
  }
  return signals.isCoarsePointer && (isBelow(signals.cores, MIN_TOUCH_CORES) || isBelow(signals.memoryGb, MIN_TOUCH_MEMORY_GB));
}

/**
 * The scene is fetched only without reduced motion, data saver or a slow
 * connection, in the wide layout (phones get the animated CSS poster), and
 * not on a weak device: fewer than 4 cores or under 4 GB of memory, or a
 * touch device with fewer than 6 of either. WebGL itself is probed later,
 * just before the scene loads (creating a context costs time).
 */
export function heroPlan(signals: DeviceSignals): HeroPlan {
  if (signals.prefersReducedMotion) {
    return { kind: "poster", reason: "reduced-motion" };
  }
  if (signals.saveData) {
    return { kind: "poster", reason: "save-data" };
  }
  if (!signals.isWideLayout) {
    return { kind: "poster", reason: "narrow-screen" };
  }
  if (signals.effectiveType !== undefined && SLOW_NETWORKS.has(signals.effectiveType)) {
    return { kind: "poster", reason: "slow-network" };
  }
  if (isLowPower(signals)) {
    return { kind: "poster", reason: "low-power" };
  }
  return { kind: "scene" };
}
