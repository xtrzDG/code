"use client";

/**
 * Whether this browser can use passkeys, for rendering: unknown (null)
 * while the server renders and the page hydrates, then the browser's
 * answer. So the first paint never claims a passkey cannot be used.
 */

import { useSyncExternalStore } from "react";

import { canUsePasskeys } from "./passkeyCeremony";

const neverChanges = () => () => {};

export function usePasskeySupport(): boolean | null {
  return useSyncExternalStore(neverChanges, canUsePasskeys, () => null);
}
