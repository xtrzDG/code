/**
 * The HTML elements a motion primitive can render as (`as="li"`), and the
 * props every primitive passes through to it.
 */

import * as m from "motion/react-m";
import type { CSSProperties, ReactNode } from "react";

export type MotionTag = "div" | "section" | "ul" | "ol" | "li" | "dl" | "span" | "figure" | "header" | "p";

/**
 * One element type for all of them: the primitives only pass the attributes
 * of MotionBlockProps, which every element accepts.
 */
export const MOTION_ELEMENTS: Record<MotionTag, typeof m.div> = {
  div: m.div,
  section: m.section as typeof m.div,
  ul: m.ul as typeof m.div,
  ol: m.ol as typeof m.div,
  li: m.li as typeof m.div,
  dl: m.dl as typeof m.div,
  span: m.span as typeof m.div,
  figure: m.figure as typeof m.div,
  header: m.header as typeof m.div,
  p: m.p as typeof m.div,
};

export interface MotionBlockProps {
  /** The element to render (a `div` unless said otherwise). */
  as?: MotionTag;
  id?: string;
  className?: string;
  style?: CSSProperties;
  role?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
  children?: ReactNode;
}
