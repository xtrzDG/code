/**
 * The inline custom properties of a reveal (src/styles/siteMotion.css):
 * only those that differ from the stylesheet's defaults, so most reveals
 * carry no style attribute at all.
 */

import type { CSSProperties } from "react";

export function revealStyle(depth: number, delay: number, style?: CSSProperties): CSSProperties | undefined {
  const own: Record<string, string> = {};
  if (depth !== 0) {
    own["--reveal-depth"] = String(depth);
  }
  if (delay !== 0) {
    own["--reveal-delay"] = `${delay}s`;
  }
  return Object.keys(own).length > 0 || style ? { ...own, ...style } : undefined;
}
