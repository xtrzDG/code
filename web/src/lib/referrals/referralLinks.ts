/**
 * Pure helpers of the referral program in the cabinet: a partner's link
 * for one place they share it, the share message, the commission rate in
 * words, payout months, and the "Powered by" line of the printed table
 * card.
 */

/** A `src` tag as the API accepts it (SignupSourceTag). */
const SOURCE_TAG = /^[A-Za-z0-9._-]{1,64}$/;
/** A payout month as the API takes it (CommissionMonth). */
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;
const BASIS_POINTS_IN_PERCENT = 100;

/** Whether `tag` may be a link's `src` (empty means "keep the link's own"). */
export function isSourceTag(tag: string): boolean {
  return SOURCE_TAG.test(tag);
}

/** The link with its `src` set to `tag`; the link as given when `tag` is blank or invalid. */
export function linkWithSource(link: string, tag: string): string {
  const trimmed = tag.trim();
  if (trimmed === "" || !isSourceTag(trimmed)) {
    return link;
  }
  try {
    const url = new URL(link);
    url.searchParams.set("src", trimmed);
    return url.toString();
  } catch {
    return link;
  }
}

/** The text a share sheet or a message carries: the invitation, then the link. */
export function shareMessage(text: string, link: string): string {
  return `${text} ${link}`;
}

/** Basis points as a percent number ("2000" → 20, "1250" → 12.5). */
export function basisPointsToPercent(basisPoints: number): number {
  return basisPoints / BASIS_POINTS_IN_PERCENT;
}

/** A typed percent as basis points, or null unless it is a number from 0 to `maxPercent`. */
export function percentToBasisPoints(value: string, maxPercent = 50): number | null {
  const text = value.trim().replace(",", ".");
  if (!/^\d{1,2}(\.\d{1,2})?$/.test(text)) {
    return null;
  }
  const percent = Number(text);
  return percent >= 0 && percent <= maxPercent ? Math.round(percent * BASIS_POINTS_IN_PERCENT) : null;
}

/** Whether `month` is a payout month (YYYY-MM). */
export function isPayoutMonth(month: string): boolean {
  return MONTH.test(month);
}

/** The UTC month of a moment as YYYY-MM (commissions belong to the month they were earned, in UTC). */
export function utcMonth(moment: Date): string {
  return `${moment.getUTCFullYear()}-${String(moment.getUTCMonth() + 1).padStart(2, "0")}`;
}

/** The month before `month` (YYYY-MM). */
export function previousMonth(month: string): string {
  const [year, number] = month.split("-").map(Number);
  return number === 1 ? `${(year ?? 0) - 1}-12` : `${year}-${String((number ?? 1) - 1).padStart(2, "0")}`;
}

/** The address shown in print: no scheme, so it is short enough to type. */
export function printableLink(link: string): string {
  return link.replace(/^https?:\/\//, "");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * The table card with a small "Powered by" line at its foot (escaped), or
 * the card as it was when there is no link or no `</main>` to put it before.
 */
export function withPoweredByFooter(cardHtml: string, label: string, link: string | null): string {
  const end = cardHtml.lastIndexOf("</main>");
  if (!link || end < 0) {
    return cardHtml;
  }
  const footer =
    '<p class="powered" style="margin:4mm 0 0;font-size:7.5pt;line-height:1.3;color:#6b7280;">' +
    `${escapeHtml(label)} · ${escapeHtml(printableLink(link))}</p>`;
  return `${cardHtml.slice(0, end)}${footer}${cardHtml.slice(end)}`;
}
