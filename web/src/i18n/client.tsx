"use client";

import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

import { pathLocale } from "@/lib/publicSite/paths";

import type { Locale } from "./config";
import type { TextScope } from "./publicScope";
import { createTranslator, type MessageTree, type Translator } from "./translate";

const I18nContext = createContext<Translator | null>(null);

/**
 * Provided once by the root layout with the request's language. On the
 * public site (`scope="public"`) it holds only the texts of the public
 * pages' client components (./publicScope.ts); the root layout stays
 * mounted when a link leads on to a cabinet page, so that page is loaded in
 * full instead, with its whole dictionary.
 */
export function I18nProvider({
  locale,
  messages,
  scope = "full",
  children,
}: {
  locale: Locale;
  messages: MessageTree;
  scope?: TextScope;
  children: ReactNode;
}) {
  const translator = useMemo(() => createTranslator(locale, messages), [locale, messages]);
  return (
    <I18nContext.Provider value={translator}>
      {scope === "public" ? <PublicSiteOnly>{children}</PublicSiteOnly> : children}
    </I18nContext.Provider>
  );
}

/** Renders the public site's pages; any other page is loaded again in full, rather than shown without its texts. */
function PublicSiteOnly({ children }: { children: ReactNode }) {
  const isPublicPage = pathLocale(usePathname() ?? "") !== null;
  useEffect(() => {
    if (!isPublicPage) {
      window.location.reload();
    }
  }, [isPublicPage]);
  return isPublicPage ? children : null;
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
