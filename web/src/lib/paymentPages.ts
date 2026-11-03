/**
 * The cabinet pages that send a payer to a payment provider's page (PAY-02,
 * PCI DSS SAQ A): the billing page, which opens Flitt's or Stripe's
 * checkout and card pages. Their documents get the cabinet's policy without
 * any third-party host (no Cloudflare Turnstile, which only the sign-in page
 * uses): first-party scripts with the page's nonce and what they load
 * (server/contentSecurityPolicy.ts). The weekly integrity check hashes the
 * scripts these pages and the hosted chat page (which shows a deposit's
 * payment link) load against payment-page-scripts.json
 * (scripts/payment-page-integrity.mjs, .github/workflows/payment-page-integrity.yml).
 *
 * A page reached by in-app navigation keeps the policy of the document it
 * was loaded as; the sign-in page is always opened as a document of its own
 * (window.location.assign, redirects), so Turnstile is never needed here.
 */

/** The App Router route of each payment page, as the build names it. */
export const PAYMENT_PAGE_ROUTES = ["/b/[businessId]/settings/billing"] as const;

const PAYMENT_PAGE = /^\/b\/[^/]+\/settings\/billing\/?$/;

/** Whether a page path (no query) sends a payer to a payment page. */
export function isPaymentPage(pathname: string): boolean {
  return PAYMENT_PAGE.test(pathname);
}
