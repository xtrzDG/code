/**
 * Keyset paging of the cabinet lists: the API answers `{items, next_cursor}`
 * and takes `?limit=N&cursor=…` (cursor = the previous page's next_cursor).
 * A paged list is cached as one entry (`PagedData`): the first page's answer
 * (totals, status counts), every item shown so far and where "show more"
 * continues.
 */

/** Items asked for per "show more". */
export const PAGE_SIZE = 50;
/** The largest page the API serves. */
export const MAX_PAGE_SIZE = 200;

export interface PageShape<Item> {
  items?: Item[];
  next_cursor?: string | null;
}

export interface PageRequest {
  /** The previous page's `next_cursor`; null for the first page. */
  cursor: string | null;
  limit: number;
}

/** A paged list as the cache holds it. */
export interface PagedData<Item, Page> {
  /** The latest first-page answer (totals and status counts live there). */
  page: Page;
  /** Every item loaded so far: the first page(s) plus "show more" pages. */
  items: Item[];
  /** Where "show more" continues; null at the end of the list. */
  nextCursor: string | null;
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
export function appendPage<Item>(
  shown: readonly Item[],
  next: readonly Item[],
  itemKey: (item: Item) => string = (item) => (item as { id: string }).id,
): Item[] {
  const seen = new Set(shown.map(itemKey));
  return [...shown, ...next.filter((item) => !seen.has(itemKey(item)))];
}

/** A first-page answer as cached data. */
export function fromFirstPage<Item, Page extends PageShape<Item>>(page: Page): PagedData<Item, Page> {
  return { page, items: page.items ?? [], nextCursor: page.next_cursor ?? null };
}

/**
 * The cached list after a "show more" page arrived. A list that was
 * reloaded meanwhile (its cursor moved on) is left as it is: the page
 * continues a list that is no longer shown.
 */
export function withNextPage<Item, Page>(
  data: PagedData<Item, Page> | undefined,
  requestedCursor: string,
  next: PageShape<Item>,
  itemKey?: (item: Item) => string,
): PagedData<Item, Page> | undefined {
  if (!data || data.nextCursor !== requestedCursor) {
    return data;
  }
  return { ...data, items: appendPage(data.items, next.items ?? [], itemKey), nextCursor: next.next_cursor ?? null };
}
