/**
 * Whether the saves of a screen are done: every save is handed to `track`,
 * saves running at once are counted, and the state becomes "saved" (or
 * "failed" when one of them failed) only when the last of them ends. The
 * tunnel's top bar, the profile editor and the settings forms that save
 * themselves read their "Saving…", "Saved", "Not saved" from it.
 */

export type SaveState = "idle" | "saving" | "saved" | "failed";

export type TrackSave = (save: Promise<boolean>) => Promise<boolean>;

/** A counter of running saves that reports the combined state on every change. */
export function createSaveCounter(onState: (state: SaveState) => void): TrackSave {
  let running = 0;
  let failed = false;
  return async (save) => {
    running += 1;
    onState("saving");
    let ok = false;
    try {
      ok = await save;
    } finally {
      running -= 1;
      failed = failed || !ok;
      if (running === 0) {
        onState(failed ? "failed" : "saved");
        failed = false;
      }
    }
    return ok;
  };
}
