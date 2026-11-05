/** A guest's booking page: `/r/{token}` (the link in their written confirmation). */
const BOOKING_PAGE_PREFIX = "/r/";

/** The page's address and the API's (/v1/public/bookings/{token}…) carry the key. */
const TOKEN_IN_PATH = /(\/r\/|\/v1\/public\/bookings\/)[^/?#\s"']+/g;

export function isBookingPagePath(pathname: string): boolean {
  return pathname.startsWith(BOOKING_PAGE_PREFIX);
}

/** "/r/AbC…/x" -> "/r/[token]/x": a text without a booking link's key, for monitoring. */
export function withoutBookingToken(text: string): string {
  return text.replace(TOKEN_IN_PATH, "$1[token]");
}
