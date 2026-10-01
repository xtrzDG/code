"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { Locale } from "./config";
import { createTranslator, type MessageTree, type Translator } from "./translate";

const I18nContext = createContext<Translator | null>(null);

/** Provided once by the root layout with the request's language. */
export function I18nProvider({
  locale,
  messages,
  children,
}: {
  locale: Locale;
  messages: MessageTree;
  children: ReactNode;
}) {
  const translator = useMemo(() => createTranslator(locale, messages), [locale, messages]);
  return <I18nContext.Provider value={translator}>{children}</I18nContext.Provider>;
}

/**
 * Translator for Client Components:
 *
 *     const { t, tp, locale } = useI18n();
 */
export function useI18n(): Translator {
  const translator = useContext(I18nContext);
  if (!translator) {
    throw new Error("useI18n() must be used inside <I18nProvider>.");
  }
  return translator;
}
