import type { MessageKey } from "@/i18n/translate";
import type { LegalPage } from "@/lib/publicSite/paths";

/** The name of each legal page in the page list, the footer and the title. */
const LABELS: Record<LegalPage, MessageKey> = {
  terms: "legalPages.nav.terms",
  privacy: "legalPages.nav.privacy",
  cookies: "cookieConsent.nav",
  dpa: "legalPages.nav.dpa",
  security: "legalPages.nav.security",
  accessibility: "accessibility.nav",
  contact: "legalPages.nav.contact",
};

/** What each legal page is about, for search engines and link previews. */
const DESCRIPTIONS: Record<LegalPage, MessageKey> = {
  terms: "legalPages.descriptions.terms",
  privacy: "legalPages.descriptions.privacy",
  cookies: "cookieConsent.description",
  dpa: "legalPages.descriptions.dpa",
  security: "legalPages.descriptions.security",
  accessibility: "accessibility.description",
  contact: "legalPages.descriptions.contact",
};

export function legalPageLabel(page: LegalPage): MessageKey {
  return LABELS[page];
}

export function legalPageDescription(page: LegalPage): MessageKey {
  return DESCRIPTIONS[page];
}
