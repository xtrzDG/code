/**
 * Colours of the hero scene in each scheme. The canvas is transparent and
 * sits on the page's own background, so only the objects change: dark
 * bubbles with light lines on the dark theme, white ones on the light theme.
 * The orb keeps the accent (iris) with a cyan and a violet current in both.
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
    bubbleTop: "#20202a",
    bubbleBottom: "#15151b",
    bubbleBorder: "rgba(255, 255, 255, 0.12)",
    line: "rgba(237, 237, 240, 0.86)",
    lineMuted: "rgba(237, 237, 240, 0.34)",
    ring: "#8c8cf5",
    ringOpacity: 0.26,
    dust: "#c6c6ff",
    dustOpacity: 0.75,
    glow: "#5b5bd6",
    glowOpacity: 0.85,
    glowAdditive: true,
    shellOpacity: 0.1,
    orbColors: ["#5b5bd6", "#3cc6f5", "#d55cf0"],
    pulse: "#c6c6ff",
  },
  light: {
    bubbleTop: "#ffffff",
    bubbleBottom: "#f3f3f7",
    bubbleBorder: "rgba(23, 23, 27, 0.10)",
    line: "rgba(23, 23, 27, 0.72)",
    lineMuted: "rgba(23, 23, 27, 0.24)",
    ring: "#5b5bd6",
    ringOpacity: 0.3,
    dust: "#6b6be0",
    dustOpacity: 0.5,
    glow: "#8c8cf5",
    glowOpacity: 0.5,
    glowAdditive: false,
    shellOpacity: 0.16,
    orbColors: ["#5b5bd6", "#2fb3e8", "#c34fe0"],
    pulse: "#5b5bd6",
  },
};
