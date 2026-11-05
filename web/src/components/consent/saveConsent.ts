/**
 * The visitor's answer goes to POST /api/consent (src/app/api/consent),
 * which stores it in the `aw_consent` cookie. With an acceptance go the
 * page this visit began on and the other site before it, so the first
 * touch is kept from the moment of consent (never before it), also when
 * the visitor moved on to another page before answering.
 */

export type ConsentChoice = "granted" | "denied";

/** Where this visit began: its first page (path and query) and the other site's page before it. */
interface Arrival {
  page: string;
  referrer: string | undefined;
}

/** Kept for the page load: client-side navigation keeps it, a full load starts over. */
let arrival: Arrival | null = null;

/** The answer stored during this page load, if any. */
let storedAnswer: ConsentChoice | null = null;

/** The page before this one when it is another site's: the site's own pages say nothing about where a visitor came from. */
function externalReferrer(): string | undefined {
  try {
    return document.referrer !== "" && new URL(document.referrer).origin !== window.location.origin ? document.referrer : undefined;
  } catch {
    return undefined;
  }
}

function currentPage(): Arrival {
  return { page: `${window.location.pathname}${window.location.search}`, referrer: externalReferrer() };
}

/**
 * Remember the page this visit began on, once per page load (the banner
 * calls it when it first appears): a visitor who came with a partner's
 * link (?ref=…) and opened another page before accepting keeps it.
 * Nothing leaves the browser until they accept.
 */
export function rememberArrival(): void {
  arrival ??= currentPage();
}

/**
 * The visitor answered during this page load: a page the router brings
 * back from its cache (the Back button) was rendered before the answer and
 * would otherwise ask again.
 */
export function hasAnsweredHere(): boolean {
  return storedAnswer !== null;
}

/** True once the answer is stored. */
export async function saveConsent(choice: ConsentChoice): Promise<boolean> {
  const body = choice === "granted" ? { choice, ...(arrival ?? currentPage()) } : { choice };
  try {
    const response = await fetch("/api/consent", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    if (response.ok) {
      storedAnswer = choice;
    }
    return response.ok;
  } catch {
    return false;
  }
}
