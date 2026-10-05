/**
 * Rendering a component the way the root layout does: in an interface
 * language (its real dictionary) with the toasts mounted.
 *
 *     const view = renderInLocale(<Modal … />, { locale: "ru" });
 *     view.rerender(<Modal … />);   // same language and providers
 */

import { render, type RenderOptions, type RenderResult } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

import { ToastProvider } from "@/components/ui/Toast";
import { I18nProvider } from "@/i18n/client";
import type { Locale } from "@/i18n/config";
import { getMessages } from "@/i18n/messages";
import { createTranslator, type Translator } from "@/i18n/translate";

export function Providers({ locale = "en", children }: { locale?: Locale; children: ReactNode }) {
  return (
    <I18nProvider locale={locale} messages={getMessages(locale)}>
      <ToastProvider>{children}</ToastProvider>
    </I18nProvider>
  );
}

export function renderInLocale(
  ui: ReactElement,
  { locale = "en", ...options }: { locale?: Locale } & Omit<RenderOptions, "wrapper"> = {},
): RenderResult {
  return render(ui, {
    ...options,
    wrapper: ({ children }: { children: ReactNode }) => <Providers locale={locale}>{children}</Providers>,
  });
}

/** The interface texts of a language, to name what a test looks for: `textsIn("ru").t("common.close")`. */
export function textsIn(locale: Locale): Translator {
  return createTranslator(locale, getMessages(locale));
}
