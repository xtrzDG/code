"use client";

/**
 * Inline styles under the Content Security Policy (no 'unsafe-inline' for
 * styles): a `style` attribute in the server's HTML is refused, while the
 * same values set from script go through the CSSOM, which the policy
 * leaves alone. So a value computed per element (a bar's width, a block's
 * position in a calendar, a motion value) is left out of the server's HTML
 * and set once the page has hydrated; a component first rendered in the
 * browser sets it at once. Values that shape the first paint belong in a
 * class or a nonce'd <style> instead (NoncedStyle).
 */

import { useState, useSyncExternalStore, type CSSProperties } from "react";

const neverChanges = () => () => {};

/** True once the page has hydrated, and from the start in a component first rendered in the browser. */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    neverChanges,
    () => true,
    () => false,
  );
}

/** The style to pass to an element: none in the server's HTML, the given one in the browser. */
export function useClientStyle<Style extends CSSProperties>(style: Style | undefined): Style | undefined {
  return useHydrated() ? style : undefined;
}

/**
 * Whether this component came into a page already in the browser (a client
 * navigation, a list that grew) rather than with the server's HTML. Fixed
 * for the component's life. An entrance animation runs only then: one
 * rendered by the server would need its hidden start as a style attribute,
 * and it is already on screen when the page loads anyway.
 */
export function useMountedAfterHydration(): boolean {
  const hydrated = useHydrated();
  const [mountedAfterHydration] = useState(hydrated);
  return mountedAfterHydration;
}
