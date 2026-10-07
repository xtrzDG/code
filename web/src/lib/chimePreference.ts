/**
 * Whether this device plays a short chime when a customer needs a person
 * (off unless the person turns it on in the account menu). A choice of
 * this browser, kept in localStorage; other tabs follow it at once.
 */

export const CHIME_STORAGE_KEY = "aw.chime.needsPerson";

type Listener = () => void;

const listeners = new Set<Listener>();

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function readChimePreference(): boolean {
  try {
    return storage()?.getItem(CHIME_STORAGE_KEY) === "on";
  } catch {
    return false;
  }
}

export function writeChimePreference(isOn: boolean): void {
  try {
    if (isOn) {
      storage()?.setItem(CHIME_STORAGE_KEY, "on");
    } else {
      storage()?.removeItem(CHIME_STORAGE_KEY);
    }
  } catch {
    // Storage refused (private mode): the choice lasts for this page only.
  }
  for (const listener of [...listeners]) {
    listener();
  }
}

/** Calls `listener` when the choice changes here or in another tab. */
export function subscribeChimePreference(listener: Listener): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === CHIME_STORAGE_KEY) {
      listener();
    }
  };
  if (typeof window !== "undefined") {
    window.addEventListener("storage", onStorage);
  }
  return () => {
    listeners.delete(listener);
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", onStorage);
    }
  };
}
