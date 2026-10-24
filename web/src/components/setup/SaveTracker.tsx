"use client";

/**
 * Autosave's voice in the top bar: every screen hands its saves to
 * `track()` and the bar says "Saving…", "Saved" or "Not saved yet". The
 * counting lives in components/forms/saveTracking (the settings forms that
 * save themselves use it too). `onSaved` hears of every save that went
 * through (the profile editor marks what the assistant knows as changed,
 * so the "not with your customers yet" banner counts it).
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { createSaveCounter, type SaveState, type TrackSave } from "@/components/forms/saveTracking";

interface SaveTracker {
  state: SaveState;
  /** Follow one save; resolves to whether it succeeded. */
  track: TrackSave;
}

const SaveTrackerContext = createContext<SaveTracker | null>(null);

export function SaveTrackerProvider({ children, onSaved }: { children: (state: SaveState) => ReactNode; onSaved?: () => void }) {
  const [state, setState] = useState<SaveState>("idle");
  const savedListener = useRef(onSaved);
  useEffect(() => {
    savedListener.current = onSaved;
  });
  const [counter] = useState(() => createSaveCounter(setState));
  const track = useCallback<TrackSave>(
    async (save) => {
      const ok = await counter(save);
      if (ok) {
        savedListener.current?.();
      }
      return ok;
    },
    [counter],
  );

  const value = useMemo(() => ({ state, track }), [state, track]);
  return <SaveTrackerContext.Provider value={value}>{children(state)}</SaveTrackerContext.Provider>;
}

/** The tracker of the tunnel around (a no-op outside one, e.g. in a test page). */
export function useSaveTracker(): SaveTracker["track"] {
  const tracker = useContext(SaveTrackerContext);
  return tracker?.track ?? ((save) => save);
}
