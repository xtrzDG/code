/**
 * The customer channels' marks, drawn in the cabinet's outline style (not
 * the official logos): SVG path data on a 24×24 grid and each brand's two
 * colours, softened to sit with the cabinet's quiet palette. The icon components (components/icons/brands.tsx) and the
 * landing's 3D bubbles (drawn on a canvas with Path2D) use the same paths.
 */

/** The channels with a mark, in the order the hero shows them. */
export const CHANNEL_MARK_KEYS = ["whatsapp", "telegram", "instagram", "messenger", "web_chat", "phone"] as const;

export type ChannelMarkKey = (typeof CHANNEL_MARK_KEYS)[number];

export interface ChannelMark {
  /** Outline paths, stroked with round caps and joins (stroke width 1.75 at 24 px). */
  paths: readonly string[];
  /** Gradient from the first colour (top left) to the second (bottom right). */
  colors: readonly [string, string];
}

export const CHANNEL_MARKS: Record<ChannelMarkKey, ChannelMark> = {
  whatsapp: {
    paths: [
      "M4 20l1.3-4A8.5 8.5 0 1112 20.5a8.4 8.4 0 01-4-1z",
      "M9 8.5c0 3.2 2.3 6 5.5 6.5l1-1.5-1.8-1-1 .8a4.5 4.5 0 01-2.5-2.5l.8-1-1-1.8z",
    ],
    colors: ["#8cc29b", "#3f7d57"],
  },
  telegram: {
    paths: ["M21 4.5 3.6 11.3c-.7.3-.7 1.2 0 1.5l4.4 1.6 1.7 5.1c.2.6.9.7 1.3.3l2.6-2.5 4.5 3.3c.5.4 1.3.1 1.4-.6L22 5.6c.2-.8-.5-1.4-1-1.1z", "M8 14.4l9.3-6.1-6.4 7.1"],
    colors: ["#8fbcdc", "#3f78a4"],
  },
  instagram: {
    paths: [
      "M8.5 3.5h7a5 5 0 015 5v7a5 5 0 01-5 5h-7a5 5 0 01-5-5v-7a5 5 0 015-5z",
      "M15.8 12a3.8 3.8 0 11-7.6 0 3.8 3.8 0 017.6 0z",
      "M17 7h.01",
    ],
    colors: ["#dba26f", "#a65a6e"],
  },
  messenger: {
    paths: [
      "M12 3.5c-4.8 0-8.5 3.5-8.5 8 0 2.5 1.1 4.6 3 6v3l2.8-1.5c.9.3 1.8.4 2.7.4 4.8 0 8.5-3.5 8.5-8s-3.7-7.9-8.5-7.9z",
      "M7.5 13.5l3-3 2.5 2 3.5-3",
    ],
    colors: ["#93b3d6", "#5f6fa6"],
  },
  web_chat: {
    paths: [
      "M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
      "M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z",
    ],
    colors: ["#d9a86c", "#ad5732"],
  },
  phone: {
    paths: ["M5 4h3.5l1.8 4.5-2.3 1.4a11 11 0 005.1 5.1l1.4-2.3L19 14.5V18a2 2 0 01-2 2A14 14 0 013 6a2 2 0 012-2z"],
    colors: ["#b5c3cf", "#5b7186"],
  },
};
