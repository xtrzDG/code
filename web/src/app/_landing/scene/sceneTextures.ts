/**
 * Textures of the hero scene, drawn on 2D canvases at run time (nothing is
 * downloaded): a message bubble per channel (the channel's mark and two
 * lines of "text"), and a soft round glow for the orb, the dust and the
 * message pulses.
 */

import { CanvasTexture, SRGBColorSpace } from "three";

import { CHANNEL_MARKS } from "@/lib/channelMarks";
import type { ChannelMarkKey } from "@/lib/heroScene";

import type { ScenePalette } from "./scenePalette";

/** Bubble texture size; the plane that shows it has the same aspect ratio. */
export const BUBBLE_TEXTURE = { width: 512, height: 320 } as const;

function canvas2d(width: number, height: number): { canvas: HTMLCanvasElement; context: CanvasRenderingContext2D } {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("2D canvas is not available");
  }
  return { canvas, context };
}

function toTexture(canvas: HTMLCanvasElement, srgb = true): CanvasTexture {
  const texture = new CanvasTexture(canvas);
  if (srgb) {
    texture.colorSpace = SRGBColorSpace;
  }
  texture.anisotropy = 4;
  texture.needsUpdate = true;
  return texture;
}

/** The outline of a speech bubble with its tail at the bottom left. */
function bubblePath(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number): void {
  const radius = 76;
  context.beginPath();
  context.moveTo(x + radius, y);
  context.lineTo(x + width - radius, y);
  context.arcTo(x + width, y, x + width, y + radius, radius);
  context.lineTo(x + width, y + height - radius);
  context.arcTo(x + width, y + height, x + width - radius, y + height, radius);
  context.lineTo(x + 150, y + height);
  // The tail.
  context.quadraticCurveTo(x + 80, y + height + 6, x + 34, y + height + 46);
  context.quadraticCurveTo(x + 62, y + height - 6, x + 70, y + height - 4);
  context.arcTo(x, y + height, x, y + height - radius, radius);
  context.lineTo(x, y + radius);
  context.arcTo(x, y, x + radius, y, radius);
  context.closePath();
}

function roundedBar(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, color: string) {
  context.beginPath();
  context.roundRect(x, y, width, height, height / 2);
  context.fillStyle = color;
  context.fill();
}

/** A message bubble of one channel. */
export function bubbleTexture(channel: ChannelMarkKey, palette: ScenePalette): CanvasTexture {
  const { width, height } = BUBBLE_TEXTURE;
  const { canvas, context } = canvas2d(width, height);
  const box = { x: 14, y: 14, width: width - 28, height: height - 76 };

  const body = context.createLinearGradient(0, box.y, 0, box.y + box.height);
  body.addColorStop(0, palette.bubbleTop);
  body.addColorStop(1, palette.bubbleBottom);
  bubblePath(context, box.x, box.y, box.width, box.height);
  context.fillStyle = body;
  context.fill();
  context.lineWidth = 3;
  context.strokeStyle = palette.bubbleBorder;
  context.stroke();

  // The channel's mark: a round badge in its colours with the outline glyph in white.
  const mark = CHANNEL_MARKS[channel];
  const centreX = box.x + 100;
  const centreY = box.y + box.height / 2;
  const badge = context.createLinearGradient(centreX - 60, centreY - 60, centreX + 60, centreY + 60);
  badge.addColorStop(0, mark.colors[0]);
  badge.addColorStop(1, mark.colors[1]);
  context.beginPath();
  context.arc(centreX, centreY, 60, 0, Math.PI * 2);
  context.fillStyle = badge;
  context.fill();
  context.save();
  context.translate(centreX - 39, centreY - 39);
  context.scale(3.25, 3.25);
  context.strokeStyle = "#ffffff";
  context.lineWidth = 1.9;
  context.lineCap = "round";
  context.lineJoin = "round";
  for (const path of mark.paths) {
    context.stroke(new Path2D(path));
  }
  context.restore();

  // Two lines of a message.
  const textX = box.x + 196;
  roundedBar(context, textX, centreY - 40, 232, 26, palette.line);
  roundedBar(context, textX, centreY + 10, 156, 26, palette.lineMuted);
  return toTexture(canvas);
}

/** A white disc fading out to its edge; tinted by the material's colour. */
export function glowTexture(size = 256): CanvasTexture {
  const { canvas, context } = canvas2d(size, size);
  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, "rgba(255, 255, 255, 1)");
  gradient.addColorStop(0.35, "rgba(255, 255, 255, 0.45)");
  gradient.addColorStop(1, "rgba(255, 255, 255, 0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);
  return toTexture(canvas, false);
}
