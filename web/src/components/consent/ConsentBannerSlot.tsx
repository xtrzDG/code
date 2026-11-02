import "server-only";

import { cookies } from "next/headers";

import { getI18n } from "@/i18n/server";
import { legalPath } from "@/lib/publicSite/paths";
import { readConsent } from "@/server/consentCookie";

import { ConsentBanner } from "./ConsentBanner";

/**
 * The cookie banner of a public site page (the landing page, the pages of
 * each kind of business, the legal pages), with its texts in the page's
 * language: open while the visitor has not answered (`aw_consent`). The
 * cabinet, the hosted chat (/c/), the booking page (/r/) and the website
 * chat never render it: they set no cookie that needs consent.
 */
export async function ConsentBannerSlot() {
  const [{ t, locale }, cookieStore] = await Promise.all([getI18n(), cookies()]);
  return (
    <ConsentBanner
      initiallyOpen={readConsent(cookieStore) === null}
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
  );
}
