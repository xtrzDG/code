"use client";

/**
 * The person's motion preference on the client (lib/motionPreference.ts).
 * The root layout renders <html data-motion="reduce"> from the `aw_motion`
 * cookie and passes the same value here; changing it rewrites the
 * attribute and the cookie at once, so the CSS side stops (globals.css)
 * and MotionProvider tells motion to keep still, without a reload.
 *
 *     const { preference, setPreference, isCalm } = useMotionPreference();
 *
 * `isCalm` also follows the device's own setting, live.
 */

import { createContext, useCallback, useContext, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";

import {
  DEFAULT_MOTION_PREFERENCE,
  MOTION_ATTRIBUTE,
  REDUCED_MOTION_QUERY,
  isCalm,
  motionAttribute,
  motionCookie,
  type MotionPreference,
} from "@/lib/motionPreference";

interface MotionPreferenceApi {
  preference: MotionPreference;
  setPreference: (preference: MotionPreference) => void;
  /** Nothing should move: the person's choice or their device's setting. */
  isCalm: boolean;
}

const MotionPreferenceContext = createContext<MotionPreferenceApi | null>(null);

function subscribeDevice(onChange: () => void): () => void {
  const query = window.matchMedia?.(REDUCED_MOTION_QUERY);
  query?.addEventListener("change", onChange);
  return () => query?.removeEventListener("change", onChange);
}

/** The device's "reduce motion" setting, live (false on the server and in the first render). */
export function useDeviceReducesMotion(): boolean {
  return useSyncExternalStore(
    subscribeDevice,
    () => window.matchMedia?.(REDUCED_MOTION_QUERY).matches ?? false,
    () => false,
  );
}

function applyPreference(preference: MotionPreference): void {
  const value = motionAttribute(preference);
  if (value) {
    document.documentElement.setAttribute(MOTION_ATTRIBUTE, value);
  } else {
    document.documentElement.removeAttribute(MOTION_ATTRIBUTE);
  }
  document.cookie = motionCookie(preference, window.location.protocol === "https:");
}

export function MotionPreferenceProvider({
  initialPreference = DEFAULT_MOTION_PREFERENCE,
  children,
}: {
  initialPreference?: MotionPreference;
  children: ReactNode;
}) {
  const [preference, setPreferenceState] = useState<MotionPreference>(initialPreference);
  const deviceReduces = useDeviceReducesMotion();

  const setPreference = useCallback((next: MotionPreference) => {
    applyPreference(next);
    setPreferenceState(next);
  }, []);

  const api = useMemo(
    () => ({ preference, setPreference, isCalm: isCalm(preference, deviceReduces) }),
    [preference, setPreference, deviceReduces],
  );
  return <MotionPreferenceContext.Provider value={api}>{children}</MotionPreferenceContext.Provider>;
}

/** Outside a provider (a component test) the device decides alone. */
const DEVICE_ONLY: Omit<MotionPreferenceApi, "isCalm"> = {
  preference: DEFAULT_MOTION_PREFERENCE,
  setPreference: () => undefined,
};

export function useMotionPreference(): MotionPreferenceApi {
  const api = useContext(MotionPreferenceContext);
  const deviceReduces = useDeviceReducesMotion();
  return api ?? { ...DEVICE_ONLY, isCalm: deviceReduces };
}
