/**
 * Interface languages of the cabinet and how the current one is chosen.
 *
 * Order: the `aw_locale` cookie (set at sign-in from the user's account
 * language and by the language switcher), then the browser's
 * Accept-Language, then English.
 */

export const LOCALES = ["ka", "ru", "en"] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = "en";

export const LOCALE_COOKIE = "aw_locale";

/** One year: the language is a preference, not a session. */
export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** Each language named in itself, for the language switcher. */
export const LOCALE_NATIVE_NAMES: Record<Locale, string> = {
  ka: "ქართული",
  ru: "Русский",
  en: "English",
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/**
 * The supported interface language of a BCP 47 tag: "ru-RU" -> "ru",
 * "ka" -> "ka", "de-DE" -> null.
 */
export function matchLocale(tag: string | null | undefined): Locale | null {
  if (!tag) {
    return null;
  }

  const normalized = tag.trim().toLowerCase().replace("_", "-");
  if (isLocale(normalized)) {
    return normalized;
  }

  const base = normalized.split("-")[0];
  return isLocale(base) ? base : null;
}

/**
 * The best supported language of an Accept-Language header, honouring
 * q-values: "de-DE,ru;q=0.8,en;q=0.5" -> "ru".
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
