/**
 * The visitor's answer goes to POST /api/consent (src/app/api/consent),
 * which stores it in the `aw_consent` cookie. With an acceptance go the
 * page it was given on and the page before it, so the first touch is
 * kept from the moment of consent (never before it).
 */

export type ConsentChoice = "granted" | "denied";

/** True once the answer is stored. */
export async function saveConsent(choice: ConsentChoice): Promise<boolean> {
  const body =
    choice === "granted"
      ? { choice, page: `${window.location.pathname}${window.location.search}`, referrer: document.referrer || undefined }
      : { choice };
  try {
    const response = await fetch("/api/consent", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    return response.ok;
  } catch {
    return false;
  }
}
