/**
 * Query keys: tuples of plain values, most general first —
 * `["leads", businessId, "list", status, includeTest]` — so a prefix
 * (`["leads", businessId]`) names every query under it. Build them with
 * `queryKeys` (queryKeys.ts), never by hand in a screen.
 */

export type QueryKeyPart = string | number | boolean | null;
export type QueryKey = readonly QueryKeyPart[];

/** The key as a string (Map key); equal tuples give equal strings. */
export function hashKey(key: QueryKey): string {
  return JSON.stringify(key);
}

/** True when `key` begins with every part of `prefix` (a key starts with itself). */
export function startsWithKey(key: QueryKey, prefix: QueryKey): boolean {
  return prefix.length <= key.length && prefix.every((part, index) => Object.is(part, key[index]));
}
