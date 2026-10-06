/**
 * Interface languages of the cabinet and how the current one is chosen.
 *
 * Order: the `aw_locale` cookie (set at sign-in from the user's account
 * language and by the language switcher), then the browser's
 * Accept-Language, then English.
 */

/** Every language the cabinet has a dictionary for (messages/index.ts). */
export const LOCALES = ["ka", "ru", "en", "he", "de"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

/**
 * The languages owners can choose: those whose dictionary is complete (the
 * completeness test in i18n.test.ts fails otherwise). A new language joins
 * LOCALES while it is being translated and joins this list when every text
 * is there. The backend keeps the same list
 * (app/schemas/constants/localization.py, CABINET_LANGUAGES).
 */
export const CABINET_LANGUAGES: readonly Locale[] = ["ka", "ru", "en"];

/**
 * Languages whose cabinet texts are drafts awaiting a native speaker's
 * review (drafted by the team, not yet read by a native reviewer). They are
 * complete and offered; the list only says whose eyes they still need.
 */
export const NEEDS_REVIEW_LOCALES: readonly Locale[] = ["he", "de"];

export type LocaleDirection = "ltr" | "rtl";

/** The writing direction of each language: the `<html dir>` of its pages. */
export const LOCALE_DIRECTION: Record<Locale, LocaleDirection> = {
  ka: "ltr",
  ru: "ltr",
  en: "ltr",
  he: "rtl",
  de: "ltr",
};

export const LOCALE_COOKIE = "aw_locale";

/** One year: the language is a preference, not a session. */
export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** Each language named in itself, for the language switcher. */
export const LOCALE_NATIVE_NAMES: Record<Locale, string> = {
  ka: "ქართული",
  ru: "Русский",
  en: "English",
  he: "עברית",
  de: "Deutsch",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/** A language owners can choose (CABINET_LANGUAGES). */
export function isCabinetLanguage(value: unknown): value is Locale {
  return isLocale(value) && CABINET_LANGUAGES.includes(value);
}

/** "he" -> "rtl"; every other language of the cabinet reads left to right. */
export function localeDirection(locale: Locale): LocaleDirection {
  return LOCALE_DIRECTION[locale];
}

/**
 * The interface language of a BCP 47 tag, among the languages owners can
 * choose: "ru-RU" -> "ru", "ka" -> "ka", "fr-FR" -> null.
 */
export function matchLocale(tag: string | null | undefined): Locale | null {
  if (!tag) {
    return null;
  }

  const normalized = tag.trim().toLowerCase().replace("_", "-");
  if (isCabinetLanguage(normalized)) {
    return normalized;
  }

  // "iw" is Hebrew's old code, still sent by some Android browsers.
  const base = normalized.split("-")[0] === "iw" ? "he" : normalized.split("-")[0];
  return isCabinetLanguage(base) ? base : null;
}

/**
 * The best supported language of an Accept-Language header, honouring
 * q-values: "fr-FR,ru;q=0.8,en;q=0.5" -> "ru".
 */
export function negotiateLocale(acceptLanguage: string | null | undefined): Locale | null {
  if (!acceptLanguage) {
    return null;
  }

  const ranked = acceptLanguage
    .split(",")
    .map((part, index) => {
      const [rawTag = "", ...parameters] = part.trim().split(";");
      const qualityParameter = parameters
        .map((parameter) => parameter.trim())
        .find((parameter) => parameter.startsWith("q="));
      const quality = qualityParameter ? Number(qualityParameter.slice(2)) : 1;
      return {
        tag: rawTag.trim(),
        quality: Number.isFinite(quality) ? quality : 0,
        index,
      };
    })
    .filter((entry) => entry.tag !== "" && entry.tag !== "*" && entry.quality > 0)
    .sort((left, right) => right.quality - left.quality || left.index - right.index);

  for (const entry of ranked) {
    const locale = matchLocale(entry.tag);
    if (locale) {
      return locale;
    }
  }

  return null;
}

/** Cookie first, then Accept-Language, then the default language. */
export function resolveLocale(options: {
  cookieValue?: string | null;
  acceptLanguage?: string | null;
}): Locale {
  return (
    matchLocale(options.cookieValue) ??
    negotiateLocale(options.acceptLanguage) ??
    DEFAULT_LOCALE
  );
}
