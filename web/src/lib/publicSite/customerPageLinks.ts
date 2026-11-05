/**
 * The two links at the foot of the pages customers see (the hosted chat
 * page /c/{address} and the booking page /r/{token}): the business's
 * privacy notice and the platform's accessibility statement. Their names
 * come in every language of those pages (the website chat widget's), a
 * language without them falls back to English; the statement itself is in
 * the cabinet's languages, else English.
 */

import { DEFAULT_LOCALE, isCabinetLanguage } from "@/i18n/config";
import { primaryLanguage } from "@/lib/hostedChat/language";

import { legalPath } from "./paths";

interface LinkNames {
  privacy: string;
  accessibility: string;
}

const NAMES: Readonly<Record<string, LinkNames>> = {
  en: { privacy: "Privacy notice", accessibility: "Accessibility" },
  it: { privacy: "Informativa privacy", accessibility: "Accessibilità" },
  de: { privacy: "Datenschutzhinweis", accessibility: "Barrierefreiheit" },
  fr: { privacy: "Confidentialité", accessibility: "Accessibilité" },
  es: { privacy: "Aviso de privacidad", accessibility: "Accesibilidad" },
  pt: { privacy: "Aviso de privacidade", accessibility: "Acessibilidade" },
  pl: { privacy: "Informacja o prywatności", accessibility: "Dostępność" },
  lt: { privacy: "Privatumo pranešimas", accessibility: "Prieinamumas" },
  lv: { privacy: "Privātuma paziņojums", accessibility: "Piekļūstamība" },
  et: { privacy: "Privaatsusteave", accessibility: "Ligipääsetavus" },
  fi: { privacy: "Tietosuojaseloste", accessibility: "Saavutettavuus" },
  nb: { privacy: "Personvernerklæring", accessibility: "Tilgjengelighet" },
  ru: { privacy: "Конфиденциальность", accessibility: "Доступность" },
  uk: { privacy: "Конфіденційність", accessibility: "Доступність" },
  kk: { privacy: "Құпиялылық", accessibility: "Қолжетімділік" },
  ka: { privacy: "კონფიდენციალურობა", accessibility: "ხელმისაწვდომობა" },
  hy: { privacy: "Գաղտնիություն", accessibility: "Մատչելիություն" },
  az: { privacy: "Məxfilik", accessibility: "Əlçatanlıq" },
  tr: { privacy: "Gizlilik bildirimi", accessibility: "Erişilebilirlik" },
  uz: { privacy: "Maxfiylik", accessibility: "Foydalanish qulayligi" },
  he: { privacy: "פרטיות", accessibility: "נגישות" },
  ar: { privacy: "الخصوصية", accessibility: "إمكانية الوصول" },
  fa: { privacy: "حریم خصوصی", accessibility: "دسترس‌پذیری" },
  ur: { privacy: "رازداری", accessibility: "رسائی" },
  hi: { privacy: "गोपनीयता", accessibility: "सुलभता" },
  zh: { privacy: "隐私声明", accessibility: "无障碍" },
  ja: { privacy: "プライバシー", accessibility: "アクセシビリティ" },
  ko: { privacy: "개인정보 처리방침", accessibility: "접근성" },
  vi: { privacy: "Quyền riêng tư", accessibility: "Khả năng tiếp cận" },
};

export interface CustomerPageLinkNames extends LinkNames {
  /** The language the names are in (the links' `lang`). */
  language: string;
}

/** The links' names in a page language ("pt-BR" reads "pt"); English when there are none. */
export function customerPageLinkNames(tag: string): CustomerPageLinkNames {
  const language = primaryLanguage(tag);
  const names = NAMES[language];
  return names ? { ...names, language } : { ...(NAMES.en as LinkNames), language: "en" };
}

/** The languages the names are written in (for the tests). */
export const CUSTOMER_PAGE_LINK_LANGUAGES: readonly string[] = Object.keys(NAMES);

/** The accessibility statement in the page's language when the site has it, else English. */
export function accessibilityStatementPath(tag: string): string {
  const language = primaryLanguage(tag);
  return legalPath(isCabinetLanguage(language) ? language : DEFAULT_LOCALE, "accessibility");
}

export interface PrivacyLink {
  href: string;
  /** A notice on another site: it opens in a new tab, the customer's page stays. */
  isExternal: boolean;
}

/**
 * The privacy link at a page's foot. A notice on this site (the platform's
 * default notice of a business's chat, which the API names by its full
 * address under CABINET_BASE_URL) becomes a path and opens in place like
 * the page's other links; a business's own notice elsewhere opens in a new
 * tab. `siteOrigin` is the origin the page is served from (null: unknown,
 * so only a path counts as this site).
 */
export function privacyLinkOf(href: string, siteOrigin: string | null): PrivacyLink {
  if (href.startsWith("/") && !href.startsWith("//")) {
    return { href, isExternal: false };
  }
  try {
    const url = new URL(href);
    if (siteOrigin !== null && url.origin === siteOrigin) {
      return { href: `${url.pathname}${url.search}${url.hash}`, isExternal: false };
    }
  } catch {
    // Not an address of its own: left as the API wrote it.
  }
  return { href, isExternal: true };
}

/** A business's chat link on the cabinet's host ("https://…/c/cafe") gives its privacy notice ("…/c/cafe/privacy"). */
export function privacyNoticeOfChat(chatUrl: string): string | null {
  try {
    const url = new URL(chatUrl);
    return /^\/c\/[^/]+$/.test(url.pathname) && (url.protocol === "https:" || url.protocol === "http:")
      ? `${url.origin}${url.pathname}/privacy`
      : null;
  } catch {
    return null;
  }
}
