"use client";

/**
 * One end of a shared-element morph: an element that, when the page
 * changes, flies from where it was on the old page to where it is on the
 * new one (React's <ViewTransition>, the browser's View Transitions API;
 * styles/viewTransitions.css). Two SharedMorphs with the same `name` pair
 * up when one of them leaves the page and the other arrives in the same
 * navigation, as an inbox row's customer becomes the open conversation's
 * header.
 *
 *     <SharedMorph name={morphName("conversation-name", id)} active={!isOpen}>
 *       <span>{name}</span>
 *     </SharedMorph>
 *
 * Feature-detected: where the browser has no View Transitions API, and
 * with reduced motion (the device's or the cabinet's own), nothing is
 * named and pages swap at once. `active={false}` takes the name away (the
 * row of the conversation that is open, so the open header holds it alone).
 */

import { ViewTransition, useSyncExternalStore, type ReactNode } from "react";

import { useMotionPreference } from "./MotionPreference";

const subscribeNothing = () => () => undefined;

/** Whether this browser can morph between pages (false on the server and in the first render). */
function useViewTransitionsSupported(): boolean {
  return useSyncExternalStore(
    subscribeNothing,
    () => typeof document !== "undefined" && typeof document.startViewTransition === "function",
    () => false,
  );
}

/** A view-transition name for one thing (`conversation-name`) of one record: a CSS identifier. */
export function morphName(part: string, id: string): string {
  return `aw-${part}-${id.replace(/[^A-Za-z0-9_-]/g, "_")}`;
}

export function SharedMorph({ name, active = true, children }: { name: string; active?: boolean; children: ReactNode }) {
  const { isCalm } = useMotionPreference();
  const isSupported = useViewTransitionsSupported();
  if (!active || isCalm || !isSupported) {
    return children;
  }
  return (
    <ViewTransition name={name} share="morph" default="none">
      {children}
    </ViewTransition>
  );
}
