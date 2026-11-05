// The load dataset `workshop seed-load` stored, as the k6 scenarios use it:
// the owners with their bearer tokens, the website-widget visitors and the
// businesses with a Telegram bot. MANIFEST names the manifest file (the
// compose service mounts perf/ at /perf); without it perf/manifest.json is
// read next to this repository's k6 folder.
const manifest = JSON.parse(open(__ENV.MANIFEST || "../../manifest.json"));

export const API_URL = (__ENV.API_URL || "http://localhost:8000").replace(/\/+$/, "");

export const businesses = manifest.businesses;

if (!businesses || businesses.length === 0) {
  throw new Error("The manifest names no businesses: run `workshop seed-load` first.");
}

// Each visitor knows its business, so a scenario can address its widget.
export const visitors = businesses.flatMap((business) =>
  business.visitors.map((visitor) => ({ ...visitor, business_id: business.business_id })),
);

export const telegramBusinesses = businesses.filter(
  (business) => business.telegram_channel_id && business.telegram_webhook_secret,
);

const businessNumbers = new Map(businesses.map((business, index) => [business.business_id, index + 1]));

// The item at `index`, wrapping around the list (indexes may be any
// integer: virtual user numbers, iterations, sequences).
export function pick(items, index) {
  if (!items || items.length === 0) {
    throw new Error("The manifest has none of these: seed more data or skip this scenario.");
  }
  return items[((index % items.length) + items.length) % items.length];
}

// A client network of its own for each number, in 10.0.0.0/8. The load
// stack trusts X-Forwarded-For, so per-network rate limits see many
// visitors instead of the one k6 container.
export function clientAddress(number) {
  const host = ((number % 16777216) + 16777216) % 16777216;
  return `10.${(host >> 16) & 255}.${(host >> 8) & 255}.${host & 255}`;
}

// The owner of `business` signed in from the owner's own network.
export function ownerHeaders(business) {
  return {
    Authorization: `Bearer ${business.owner_access_token}`,
    "X-Forwarded-For": clientAddress(100000 + businessNumbers.get(business.business_id)),
  };
}

// The calendar date `days` from today (UTC), as the API's date parameters
// take it: YYYY-MM-DD.
export function dayFromToday(days) {
  return new Date(Date.now() + days * 86400000).toISOString().slice(0, 10);
}
