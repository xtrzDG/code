/** The website chat's look: its colour and corner, and the live preview link. */

import type { Schema } from "@/api/types";

import type { ChannelView } from "./channels";

export type WidgetPosition = Schema<"WidgetPosition">;

/** The widget's own accent colour (widget.js DEFAULT_ACCENT). */
export const WIDGET_DEFAULT_COLOR = "#ad5732";

/** Brand colours offered as one-click choices (each readable with white or dark text). */
export const WIDGET_COLOR_PRESETS = ["#ad5732", "#8f7438", "#4e6c88", "#3d5c79", "#8c4a52", "#6b5b4b", "#b0362b", "#1d1c1a"] as const;

export const WIDGET_POSITIONS: readonly WidgetPosition[] = ["right", "left"];

/**
 * "#0F766E", "0f766e" or "#abc" as the API's six-digit form ("#0f766e");
 * null when it is not a hex colour.
 */
export function normalizeHexColor(value: string): string | null {
  const text = value.trim().replace(/^#/, "");
  if (/^[0-9a-fA-F]{6}$/.test(text)) {
    return `#${text.toLowerCase()}`;
  }
  if (/^[0-9a-fA-F]{3}$/.test(text)) {
    return `#${[...text.toLowerCase()].map((digit) => digit + digit).join("")}`;
  }
  return null;
}

/** Text colour that stays readable on the accent (the widget uses the same rule). */
export function readableTextColor(hexColor: string): "#111827" | "#ffffff" {
  const hex = normalizeHexColor(hexColor) ?? WIDGET_DEFAULT_COLOR;
  const [red, green, blue] = [1, 3, 5].map((offset) => {
    const value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
  });
  const luminance = 0.2126 * (red ?? 0) + 0.7152 * (green ?? 0) + 0.0722 * (blue ?? 0);
  // The higher WCAG contrast: with white 1.05/(L+0.05), with #111827 (L≈0.0093) (L+0.05)/0.0593.
  return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.0593 ? "#ffffff" : "#111827";
}

export interface WidgetLook {
  color: string;
  position: WidgetPosition;
}

/** The saved look of the website chat, with the widget's defaults filled in. */
export function savedWidgetLook(channel: Pick<ChannelView, "widget_color" | "widget_position"> | undefined): WidgetLook {
  return {
    color: normalizeHexColor(channel?.widget_color ?? "") ?? WIDGET_DEFAULT_COLOR,
    position: channel?.widget_position ?? "right",
  };
}

export function isSameWidgetLook(left: WidgetLook, right: WidgetLook): boolean {
  return normalizeHexColor(left.color) === normalizeHexColor(right.color) && left.position === right.position;
}

/**
 * The demo page with the chosen (maybe unsaved) colour, corner and the
 * interface language: /widget/demo?business_id=…&color=…&position=…&language=…
 */
export function buildWidgetPreviewUrl(demoUrl: string, look: WidgetLook, language: string): string {
  const url = new URL(demoUrl);
  const color = normalizeHexColor(look.color);
  if (color) {
    url.searchParams.set("color", color);
  }
  url.searchParams.set("position", look.position);
  url.searchParams.set("language", language);
  return url.toString();
}
