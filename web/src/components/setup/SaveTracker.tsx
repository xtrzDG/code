"use client";

/**
 * Autosave's voice in the top bar: every screen hands its saves to
 * `track()` and the bar says "Saving…", "Saved" or "Not saved yet". Saves
 * running at once are counted, so the bar says "Saved" only when all of
 * them are done.
 */

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

import type { SaveState } from "./TunnelHeader";

interface SaveTracker {
  state: SaveState;
  /** Follow one save; resolves to whether it succeeded. */
  track: (save: Promise<boolean>) => Promise<boolean>;
}

const SaveTrackerContext = createContext<SaveTracker | null>(null);

export function SaveTrackerProvider({ children }: { children: (state: SaveState) => ReactNode }) {
  const [state, setState] = useState<SaveState>("idle");
  const running = useRef(0);
  const failed = useRef(false);

  const track = useCallback(async (save: Promise<boolean>) => {
    running.current += 1;
    setState("saving");
    let ok = false;
    try {
      ok = await save;
    } finally {
      running.current -= 1;
      failed.current = failed.current || !ok;
      if (running.current === 0) {
        setState(failed.current ? "failed" : "saved");
        failed.current = false;
      }
    }
    return ok;
  }, []);

  const value = useMemo(() => ({ state, track }), [state, track]);
  return <SaveTrackerContext.Provider value={value}>{children(state)}</SaveTrackerContext.Provider>;
}

/** The tracker of the tunnel around (a no-op outside one, e.g. in a test page). */
export function useSaveTracker(): SaveTracker["track"] {
  const tracker = useContext(SaveTrackerContext);
  return tracker?.track ?? ((save) => save);
}
