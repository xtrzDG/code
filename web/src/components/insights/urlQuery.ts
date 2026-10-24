/**
 * Puts list filters into the page URL without a navigation.
 *
 * The state must be null: Next.js then copies its own history state and
 * updates usePathname/useSearchParams. Passing `window.history.state` (which
 * carries Next's `__NA` marker) makes the router skip that sync.
 */
export function replaceUrlQuery(query: string): void {
  window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}`);
}
