/**
 * A message that arrives while the conversation is open (the customer
 * writes, the assistant answers, a teammate replies) springs into the
 * transcript from below; the ones that were there when it opened, and
 * earlier ones loaded on request, just stand. Nothing moves when the
 * person asked for calm (the device's setting or the cabinet's own).
 */

import type { Transition } from "motion/react";

import { SPRINGS } from "@/lib/motion";

interface Arrival {
  initial: { opacity: number; y: number; scale: number } | false;
  animate: { opacity: number; y: number; scale: number };
  transition: Transition;
}

const SPRING: Transition = { type: "spring", ...SPRINGS.bouncy, stiffness: 420, damping: 26 };

/** The messages on screen when the transcript opened: their ids and the newest moment among them. */
export interface OpeningMessages {
  ids: ReadonlySet<string>;
  newestAt: number;
}

export function openingMessages(messages: readonly { id: string; created_at: number }[]): OpeningMessages {
  return {
    ids: new Set(messages.map((message) => message.id)),
    newestAt: messages.reduce((newest, message) => Math.max(newest, message.created_at), Number.NEGATIVE_INFINITY),
  };
}

/** Whether a message came after the transcript opened (not an earlier one loaded on request). */
export function isArrival(message: { id: string; created_at: number }, opening: OpeningMessages): boolean {
  return !opening.ids.has(message.id) && message.created_at > opening.newestAt;
}

export function arrivalMotion(arrives: boolean, isCalm: boolean): Arrival {
  return {
    initial: arrives && !isCalm ? { opacity: 0, y: 14, scale: 0.96 } : false,
    animate: { opacity: 1, y: 0, scale: 1 },
    transition: SPRING,
  };
}
