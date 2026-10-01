/**
 * Keyset paging of the cabinet lists: the API answers `{items, next_cursor}`
 * and takes `?limit=N&cursor=…` (cursor = the previous page's next_cursor).
 */

/** Items asked for per "show more". */
export const PAGE_SIZE = 50;
/** The largest page the API serves. */
export const MAX_PAGE_SIZE = 200;

export interface PageShape<Item> {
  items?: Item[];
  next_cursor?: string | null;
}

/**
 * How many items a reload asks for, so a list the user already extended
 * with "show more" keeps its length (at most one API page).
 */
export function reloadLimit(loadedCount: number, pageSize: number = PAGE_SIZE): number {
  const pages = Math.max(1, Math.ceil(loadedCount / pageSize));
  return Math.min(MAX_PAGE_SIZE, pages * pageSize);
}

/** The next page appended, without items that are already shown (a list that moved in between). */
export function appendPage<Item extends { id: string }>(shown: readonly Item[], next: readonly Item[]): Item[] {
  const seen = new Set(shown.map((item) => item.id));
  return [...shown, ...next.filter((item) => !seen.has(item.id))];
}
