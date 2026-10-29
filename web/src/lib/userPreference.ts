/**
 * Small choices a person makes about how a page looks (the inbox's row
 * density and column width, which Overview blocks stay folded on a phone),
 * remembered in this browser for that person: the key carries the user id,
 * so two people sharing a front-desk tablet keep their own.
 *
 * Storage can be missing or refuse (private windows, blocked site data):
 * every access is wrapped, and nothing remembered means the default. Other
 * tabs follow a change at once (the `storage` event); this tab through the
 * listeners.
 */

const PREFIX = "aw.pref.";

type Listener = () => void;

const listeners = new Set<Listener>();

export type PreferenceStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/** The browser's localStorage, or null where it cannot be used. */
export function browserStorage(): PreferenceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** `aw.pref.{name}:{userId}`. */
export function preferenceKey(name: string, userId: string): string {
  return `${PREFIX}${name}:${userId}`;
}

/** The stored text of a choice (null: nothing remembered or storage refused). */
export function readPreference(storage: PreferenceStorage | null, name: string, userId: string): string | null {
  try {
    return storage?.getItem(preferenceKey(name, userId)) ?? null;
  } catch {
    return null;
  }
}

/** Remembers a choice (null forgets it) and tells this tab's listeners. */
export function writePreference(storage: PreferenceStorage | null, name: string, userId: string, value: string | null): void {
  try {
    if (value === null) {
      storage?.removeItem(preferenceKey(name, userId));
    } else {
      storage?.setItem(preferenceKey(name, userId), value);
    }
  } catch {
    // Not remembered: the choice lasts while the page is open.
  }
  for (const listener of [...listeners]) {
    listener();
  }
}

/** Calls `listener` when any remembered choice changes, here or in another tab. */
export function subscribePreferences(listener: Listener): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === null || event.key.startsWith(PREFIX)) {
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

/** A set of names kept as one comma-separated choice ("stats,topics"). */
export function parseNameSet(stored: string | null): ReadonlySet<string> {
  return new Set((stored ?? "").split(",").filter((name) => /^[a-z][a-z0-9-]*$/.test(name)));
}

/** The set with `name` added or removed, as stored text (null when empty). */
export function toggledNameSet(stored: string | null, name: string, isIn: boolean): string | null {
  const names = new Set(parseNameSet(stored));
  if (isIn) {
    names.add(name);
  } else {
    names.delete(name);
  }
  return names.size === 0 ? null : [...names].sort().join(",");
}
