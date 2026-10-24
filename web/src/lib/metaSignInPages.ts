/**
 * The cabinet pages where an owner may sign in with Facebook (Meta's
 * WhatsApp Embedded Signup and the Messenger / Instagram page picker): the
 * Channels page and the setup tunnel. Only their documents get the
 * exceptions Facebook's JavaScript SDK needs: the Content Security Policy
 * lets it frame and call Facebook (server/contentSecurityPolicy.ts), and
 * the opener policy keeps the handle on Facebook's sign-in window
 * (`same-origin-allow-popups`, next.config.ts). The SDK itself is loaded
 * only when the connect dialog opens.
 *
 * A page reached by in-app navigation keeps the headers of the document it
 * was loaded as, so the dialog checks the document's own address before it
 * opens Facebook (channels/_lib/metaSignIn.ts).
 */

/** next.config.ts `headers()` sources of those pages. */
export const META_SIGN_IN_PAGE_SOURCES = ["/b/:businessId/assistant/channels", "/b/:businessId/setup"] as const;

const META_SIGN_IN_PAGE = /^\/b\/[^/]+\/(?:assistant\/channels|setup)\/?$/;

/** Whether a page path (no query) is one where the owner signs in with Facebook. */
export function isMetaSignInPage(pathname: string): boolean {
  return META_SIGN_IN_PAGE.test(pathname);
}
