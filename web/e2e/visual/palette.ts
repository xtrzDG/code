/**
 * The palette rule of the review gate, for colours as the browser computed
 * them (tests/platform/test_palette_guard.py holds the same rule for the
 * sources): graphite and paper neutrals, the clay accent, muted olive,
 * ochre, brick and slate states. A colour saturated enough to read as a
 * hue (HSL saturation ≥ 0.22, lightness 0.12–0.93) must not be green
 * (75–165°), cyan (165–200°), indigo (235–265°) or purple (265–320°),
 * unless it is one of the allowed tokens (the "done" sage and the chart
 * series) or a channel mark's own colour.
 */

export type Rgba = readonly [number, number, number, number];

const BANNED_FAMILIES = [
  ["green", 75, 165],
  ["cyan", 165, 200],
  ["indigo", 235, 265],
  ["purple", 265, 320],
] as const;

export type Family = (typeof BANNED_FAMILIES)[number][0];

/** Tokens whose colours may be anything the theme gives them (globals.css). */
export const ALLOWED_TOKENS = ["--success", "--success-soft", "--chart-1", "--chart-2", "--chart-3"] as const;

/** Other companies' marks keep their own hue, softened (src/lib/channelMarks.ts, the palette guard's exceptions). */
export const CHANNEL_MARK_COLOURS: readonly Rgba[] = [
  [0x8c, 0xc2, 0x9b, 1], // WhatsApp, light end
  [0x3f, 0x7d, 0x57, 1], // WhatsApp, dark end
];

/** One computed colour of a page: where it was used, how often, and a sample element. */
export interface SeenColour {
  rgba: Rgba;
  property: string;
  count: number;
  sample: string;
}

/** The banned family of a colour, as colorsys.rgb_to_hls reads it (the palette guard's maths). */
export function hueFamily([red, green, blue]: Rgba): Family | null {
  const [r, g, b] = [red / 255, green / 255, blue / 255];
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const lightness = (max + min) / 2;
  if (max === min) {
    return null;
  }
  const delta = max - min;
  const saturation = lightness <= 0.5 ? delta / (max + min) : delta / (2 - max - min);
  if (saturation < 0.22 || lightness < 0.12 || lightness > 0.93) {
    return null;
  }
  const sector = max === r ? (g - b) / delta : max === g ? 2 + (b - r) / delta : 4 + (r - g) / delta;
  const turn = (((sector / 6) % 1) + 1) % 1;
  const degrees = turn * 360;
  return BANNED_FAMILIES.find(([, start, end]) => degrees >= start && degrees < end)?.[0] ?? null;
}

/** The same colour within rounding (a token rendered through the canvas may move by a unit). */
function isSameColour(a: Rgba, b: Rgba): boolean {
  return [0, 1, 2].every((channel) => Math.abs(a[channel]! - b[channel]!) <= 2);
}

/** "green rgb(52 211 153) on background-color, 3×: div.badge "Done"" for every banned colour not allowed. */
export function offPalette(seen: readonly SeenColour[], allowed: readonly Rgba[]): string[] {
  const permitted = [...allowed, ...CHANNEL_MARK_COLOURS];
  return seen.flatMap(({ rgba, property, count, sample }) => {
    const family = hueFamily(rgba);
    if (family === null || rgba[3] === 0 || permitted.some((colour) => isSameColour(colour, rgba))) {
      return [];
    }
    return [`${family} rgb(${rgba.slice(0, 3).join(" ")}) on ${property}, ${count}×: ${sample}`];
  });
}
