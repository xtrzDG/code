"use client";

/**
 * The language a date field reads, writes and speaks in. In the cabinet it
 * is the cabinet's own (`useI18n`, the `formFields.date.*` texts); a page
 * for a business's customers speaks the customer's language instead (a
 * guest's booking page in Turkish, Arabic or Hebrew) and gives the field
 * its texts in that language:
 *
 *     <DateFieldLanguage locale="tr" texts={dateTexts}>
 *       <DateField … />
 *     </DateFieldLanguage>
 *
 * The direction comes from the page (`dir` on an ancestor), like any text.
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";

type DateFieldTextKey = "placeholder" | "open" | "calendar" | "previousMonth" | "nextMonth" | "today" | "clear";

/** Everything a date field and its calendar say. */
type DateFieldTexts = Readonly<Record<DateFieldTextKey, string>>;

interface DateFieldSpeech {
  /** BCP 47 tag the dates are read and written in. */
  locale: string;
  text: (key: DateFieldTextKey) => string;
}

const DateFieldLanguageContext = createContext<{ locale: string; texts: DateFieldTexts } | null>(null);

export function DateFieldLanguage({
  locale,
  texts,
  children,
}: {
  locale: string;
  texts: DateFieldTexts;
  children: ReactNode;
}) {
  const value = useMemo(() => ({ locale, texts }), [locale, texts]);
  return <DateFieldLanguageContext.Provider value={value}>{children}</DateFieldLanguageContext.Provider>;
}

/** The page's own language for its date fields, or the cabinet's. */
export function useDateFieldLanguage(): DateFieldSpeech {
  const own = useContext(DateFieldLanguageContext);
  const { t, locale } = useI18n();
  if (own) {
    return { locale: own.locale, text: (key) => own.texts[key] };
  }
  return { locale, text: (key) => t(`formFields.date.${key}`) };
}
