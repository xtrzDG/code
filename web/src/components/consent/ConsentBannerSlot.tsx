import "server-only";

import { cookies } from "next/headers";

import { NoncedStyle } from "@/components/csp/NoncedStyle";
import { getI18n } from "@/i18n/server";
import { legalPath } from "@/lib/publicSite/paths";
import { readConsent } from "@/server/consentCookie";

import { ConsentBanner } from "./ConsentBanner";

/**
 * Without scripts no answer can be given (and nothing is kept that needs
 * one): the box is hidden rather than left over the foot of the page.
 */
const NO_SCRIPT_STYLE = "[data-cookie-consent]{display:none}";

/**
 * The cookie banner of a public site page (the landing page, the pages of
 * each kind of business, the legal pages), with its texts in the page's
 * language: open while the visitor has not answered (`aw_consent`). The
 * cabinet, the hosted chat (/c/), the booking page (/r/) and the website
 * chat never render it: they set no cookie that needs consent.
 */
export async function ConsentBannerSlot() {
  const [{ t, locale }, cookieStore] = await Promise.all([getI18n(), cookies()]);
  const isUnanswered = readConsent(cookieStore) === null;
  return (
    <>
      {isUnanswered ? (
        <noscript>
          <NoncedStyle css={NO_SCRIPT_STYLE} />
        </noscript>
      ) : null}
      <ConsentBanner
        initiallyOpen={isUnanswered}
        texts={{
          title: t("cookieConsent.title"),
          text: t("cookieConsent.text"),
          statementLink: t("cookieConsent.statementLink"),
          statementHref: legalPath(locale, "cookies"),
          accept: t("cookieConsent.accept"),
          reject: t("cookieConsent.reject"),
          close: t("cookieConsent.close"),
          failed: t("cookieConsent.failed"),
        }}
      />
    </>
  );
}
