/**
 * How the inbox list moves while it is live (InboxList, InboxRowItem): a
 * conversation that arrives slides in from above, one that leaves (resolved,
 * moved to another view) fades out of the column at once while the rows
 * below glide up into its place, and a row that moves to the top glides
 * there. Nothing moves when the view or the filters change (the list is a
 * new one then: `presenceKey`) or with reduced motion (the device's or
 * the cabinet's own), where rows simply appear and go.
 */

import type { Transition } from "motion/react";

import { springTransition, tweenTransition } from "@/lib/motion";

const ENTER = { opacity: 0, y: -10, scale: 0.985 } as const;
const PRESENT = { opacity: 1, y: 0, scale: 1 } as const;
const EXIT = { opacity: 0, scale: 0.98, transition: tweenTransition("fast", "exit") } as const;

export const ROW_LAYOUT_TRANSITION: Transition = { layout: springTransition("layout"), default: springTransition("snappy") };

export interface RowMotionProps {
  initial: typeof ENTER | false;
  animate: typeof PRESENT;
  exit: typeof EXIT | undefined;
  layout: "position" | false;
  transition: Transition;
}

/** The motion props of a row: none of them move anything when the person asked for calm. */
export function rowMotion(isCalm: boolean): RowMotionProps {
  return isCalm
    ? { initial: false, animate: PRESENT, exit: undefined, layout: false, transition: ROW_LAYOUT_TRANSITION }
    : { initial: ENTER, animate: PRESENT, exit: EXIT, layout: "position", transition: ROW_LAYOUT_TRANSITION };
}

/**
 * Which list the rows on screen belong to: the filters' query once their
 * own rows arrived. While another view loads, the old rows stay (dimmed)
 * under the old key, so they do not animate out; when the new rows come,
 * the key changes and they appear without animating in.
 */
export function nextPresenceKey(shown: string, requested: string, isPlaceholder: boolean): string {
  return isPlaceholder ? shown : requested;
}
