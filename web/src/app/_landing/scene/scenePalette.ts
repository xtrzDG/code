/**
 * Colours of the hero scene in each scheme. The canvas is transparent and
 * sits on the page's own background, so only the objects change: dark
 * bubbles with light lines on the dark theme, white ones on the light theme.
 * The orb keeps the accent (clay) with a sand and a rose current in both.
 */

export type SceneScheme = "dark" | "light";

export interface ScenePalette {
  bubbleTop: string;
  bubbleBottom: string;
  bubbleBorder: string;
  line: string;
  lineMuted: string;
  ring: string;
  ringOpacity: number;
  dust: string;
  dustOpacity: number;
  glow: string;
  glowOpacity: number;
  /** Light adds up on a dark page; on a light page it would vanish, so it is painted normally. */
  glowAdditive: boolean;
  shellOpacity: number;
  orbColors: readonly [string, string, string];
  pulse: string;
}

export const SCENE_PALETTES: Record<SceneScheme, ScenePalette> = {
  dark: {
    bubbleTop: "#26241f",
    bubbleBottom: "#1a1916",
    bubbleBorder: "rgba(255, 255, 255, 0.12)",
    line: "rgba(236, 235, 230, 0.86)",
    lineMuted: "rgba(236, 235, 230, 0.34)",
    ring: "#e19a75",
    ringOpacity: 0.24,
    dust: "#f0c9a8",
    dustOpacity: 0.75,
    glow: "#ad5732",
    glowOpacity: 0.8,
    glowAdditive: true,
    shellOpacity: 0.1,
    orbColors: ["#ad5732", "#d9a86c", "#b8796a"],
    pulse: "#f0c9a8",
  },
  light: {
    bubbleTop: "#ffffff",
    bubbleBottom: "#f4f2ed",
    bubbleBorder: "rgba(29, 28, 26, 0.10)",
    line: "rgba(29, 28, 26, 0.72)",
    lineMuted: "rgba(29, 28, 26, 0.24)",
    ring: "#ad5732",
    ringOpacity: 0.28,
    dust: "#c48d4e",
    dustOpacity: 0.5,
    glow: "#e19a75",
    glowOpacity: 0.45,
    glowAdditive: false,
    shellOpacity: 0.16,
    orbColors: ["#ad5732", "#c48d4e", "#a8685a"],
    pulse: "#ad5732",
  },
};
