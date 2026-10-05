/**
 * Filters of the customer list: the search box, a tag and which customers
 * (everyone, VIPs, blocked ones), kept in the URL (`?q=nino&tag=regular&show=vip`)
 * and sent to GET …/contacts.
 */

export const CUSTOMER_LIST_FILTERS = ["all", "vip", "blocked"] as const;
export type CustomerListFilter = (typeof CUSTOMER_LIST_FILTERS)[number];

/** The API's longest search and tag. */
export const MAX_SEARCH_LENGTH = 100;
export const MAX_TAG_LENGTH = 32;

export interface CustomerFilters {
  /** What the search box holds (trimmed only when sent). */
  search: string;
  tag: string | null;
  show: CustomerListFilter;
}

export const NO_CUSTOMER_FILTERS: CustomerFilters = { search: "", tag: null, show: "all" };

type SearchParams = Record<string, string | string[] | undefined>;

function single(params: SearchParams, key: string): string | null {
  const value = params[key];
  return typeof value === "string" ? value : null;
}

function isListFilter(value: string | null): value is CustomerListFilter {
  return (CUSTOMER_LIST_FILTERS as readonly string[]).includes(value ?? "");
}

/** The search as sent: trimmed, at most 100 characters, nothing for an empty box. */
export function searchParam(text: string): string | undefined {
  const trimmed = text.trim().slice(0, MAX_SEARCH_LENGTH).trim();
  return trimmed === "" ? undefined : trimmed;
}

/** A tag as sent: trimmed, at most 32 characters, nothing when empty. */
export function tagParam(text: string | null): string | undefined {
  const trimmed = (text ?? "").trim().slice(0, MAX_TAG_LENGTH).trim();
  return trimmed === "" ? undefined : trimmed;
}

/** Filters from the page URL; anything unknown falls back to everyone. */
export function parseCustomerFilters(params: SearchParams): CustomerFilters {
  const show = single(params, "show");
  return {
    search: (single(params, "q") ?? "").slice(0, MAX_SEARCH_LENGTH),
    tag: tagParam(single(params, "tag")) ?? null,
    show: isListFilter(show) ? show : "all",
  };
}

/** The URL query of the filters ("" for none), in a fixed order. */
export function customerFiltersQuery(filters: CustomerFilters): string {
  const query = new URLSearchParams();
  const search = searchParam(filters.search);
  const tag = tagParam(filters.tag);
  if (search) {
    query.set("q", search);
  }
  if (tag) {
    query.set("tag", tag);
  }
  if (filters.show !== "all") {
    query.set("show", filters.show);
  }
  return query.toString();
}

/** The list query of GET …/contacts (unset ones left out). */
export function customerListQuery(filters: CustomerFilters): { search?: string; tag?: string; filter?: CustomerListFilter } {
  const search = searchParam(filters.search);
  const tag = tagParam(filters.tag);
  return {
    ...(search ? { search } : {}),
    ...(tag ? { tag } : {}),
    ...(filters.show !== "all" ? { filter: filters.show } : {}),
  };
}

/** Whether anything narrows the list (the empty state then offers "Show everyone"). */
export function hasCustomerFilters(filters: CustomerFilters): boolean {
  return customerFiltersQuery(filters) !== "";
}
