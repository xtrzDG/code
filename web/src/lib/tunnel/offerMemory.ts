/**
 * The niche's offer examples the owner already dealt with: replaced by
 * their own line (an example they typed over and saved) or removed. The
 * offer step remembers their keys per business in this browser, so a
 * revisit does not bring back "Chef's special" after the owner renamed it
 * to "Khinkali" or deleted it. Examples are matched by key, never by
 * name (names change with the language); and once any line is saved, no
 * example is offered at all (initialOfferRows), whatever this browser
 * remembers.
 *
 * Storage can be missing or refuse (private windows, quotas): every access
 * is wrapped, and a broken value reads as nothing remembered.
 */

const OFFER_MEMORY_PREFIX = "aw_offer_examples_done:";

/** The prefix of a table row that came from a niche example ("starter-haircut"). */
const EXAMPLE_ROW_PREFIX = "starter-";

export type MemoryStorage = Pick<Storage, "getItem" | "setItem">;

/** The example's key behind a row key, or null for the owner's own lines. */
export function exampleKeyOf(rowKey: string): string | null {
  return rowKey.startsWith(EXAMPLE_ROW_PREFIX) ? rowKey.slice(EXAMPLE_ROW_PREFIX.length) || null : null;
}

export function exampleRowKey(exampleKey: string): string {
  return `${EXAMPLE_ROW_PREFIX}${exampleKey}`;
}

function memoryKey(businessId: string): string {
  return `${OFFER_MEMORY_PREFIX}${businessId}`;
}

export function readDoneExamples(storage: MemoryStorage | null, businessId: string): ReadonlySet<string> {
  try {
    const raw = storage?.getItem(memoryKey(businessId));
    const value: unknown = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []);
  } catch {
    return new Set();
  }
}

/** Remember an example as dealt with; returns the keys remembered now. */
export function rememberDoneExample(storage: MemoryStorage | null, businessId: string, exampleKey: string): ReadonlySet<string> {
  const done = new Set(readDoneExamples(storage, businessId));
  if (done.has(exampleKey)) {
    return done;
  }
  done.add(exampleKey);
  try {
    storage?.setItem(memoryKey(businessId), JSON.stringify([...done]));
  } catch {
    // Not remembered: the next visit still hides examples whose name is saved.
  }
  return done;
}

/** The browser's local storage, or null where it cannot be reached. */
export function browserStorage(): MemoryStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
