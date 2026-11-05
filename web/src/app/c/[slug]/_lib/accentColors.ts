/**
 * The business's accent on the hosted chat page, readable whatever colour
 * the owner chose: the same rule as the widget the page runs
 * (app/gateways/http/static/widget/colors.js, `accentColors`), so the
 * page's mark and spinner and the widget's header agree.
 *
 * White text when it reaches WCAG AA (4.5:1) on the accent, else the dark
 * scheme's ink, else the accent darkened step by step until white does.
 */

const AA_CONTRAST = 4.5;
const WHITE_TEXT = "#ffffff";
const INK_TEXT = "#1a1816";
/** Each step keeps this much of the accent's channels (toward black). */
const DARKEN_STEP = 0.92;
const HEX_COLOR = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

type Channels = readonly [number, number, number];

export type AccentColors = { accent: string; onAccent: string };

export function accentColors(hexColor: string): AccentColors | null {
  if (!HEX_COLOR.test(hexColor)) {
    return null;
  }
  const channels = hexChannels(hexColor);
  if (contrastRatio(channels, hexChannels(WHITE_TEXT)) >= AA_CONTRAST) {
    return { accent: toHexColor(channels), onAccent: WHITE_TEXT };
  }
  if (contrastRatio(channels, hexChannels(INK_TEXT)) >= AA_CONTRAST) {
    return { accent: toHexColor(channels), onAccent: INK_TEXT };
  }
  let darker: Channels = channels;
  while (contrastRatio(darker, hexChannels(WHITE_TEXT)) < AA_CONTRAST) {
    darker = [Math.floor(darker[0] * DARKEN_STEP), Math.floor(darker[1] * DARKEN_STEP), Math.floor(darker[2] * DARKEN_STEP)];
  }
  return { accent: toHexColor(darker), onAccent: WHITE_TEXT };
}

function hexChannels(hexColor: string): Channels {
  let hex = hexColor.replace(/^#/, "");
  if (hex.length === 3) {
    hex = hex
      .split("")
      .map((digit) => digit + digit)
      .join("");
  }
  return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16)];
}

function toHexColor(channels: Channels): string {
  return `#${channels.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

/** WCAG 2 relative luminance and contrast ratio. */
function relativeLuminance(channels: Channels): number {
  const [red, green, blue] = channels.map((channel) => {
    const value = channel / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

export function contrastRatio(first: Channels | string, second: Channels | string): number {
  const one = relativeLuminance(typeof first === "string" ? hexChannels(first) : first);
  const two = relativeLuminance(typeof second === "string" ? hexChannels(second) : second);
  return (Math.max(one, two) + 0.05) / (Math.min(one, two) + 0.05);
}
