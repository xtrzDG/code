/**
 * Where a visitor of the hosted chat page came from: the `?src=` of its
 * link or QR code (else `?utm_source=`), as the tag the API records
 * (`AcquisitionSourceTag`: lower case, runs of other characters as one
 * dash, at most 32 characters). The page hands it to the widget
 * (`data-source`), which sends it with the first message.
 */

const MAX_TAG_LENGTH = 32;
const NOT_TAG_CHARACTERS = /[^a-z0-9_-]+/g;
const EDGES = /^[-_]+|[-_]+$/g;

type SearchParams = Record<string, string | string[] | undefined>;

/** A typed source as its tag; null when nothing of it is left. */
export function normalizeVisitSource(text: string | null | undefined): string | null {
  if (!text) {
    return null;
  }
  const tag = text.trim().toLowerCase().replace(NOT_TAG_CHARACTERS, "-").replace(EDGES, "").slice(0, MAX_TAG_LENGTH).replace(EDGES, "");
  return tag || null;
}

/** The page's source: `src`, else `utm_source` (the first of repeated ones). */
export function visitSourceOf(params: SearchParams): string | null {
  return normalizeVisitSource(firstOf(params.src)) ?? normalizeVisitSource(firstOf(params.utm_source));
}

function firstOf(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
