import type { Metadata, Viewport } from "next";

import { MotionProvider } from "@/components/motion/MotionProvider";
import { WebVitalsReporter } from "@/components/telemetry/WebVitalsReporter";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { I18nProvider } from "@/i18n/client";
import { getI18n } from "@/i18n/server";
import { themeColors } from "@/lib/theme";
import { getTheme } from "@/server/theme";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return {
    title: { default: t("common.appName"), template: `%s · ${t("common.appName")}` },
    description: t("common.tagline"),
    robots: { index: false, follow: false },
  };
}

/** The browser's colour around the page follows the theme of the cookie. */
export async function generateViewport(): Promise<Viewport> {
  return {
    width: "device-width",
    initialScale: 1,
    themeColor: themeColors(await getTheme()),
  };
}

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [{ locale, messages }, theme] = await Promise.all([getI18n(), getTheme()]);
  return (
    // data-theme is rendered on the server, so the first paint already has the right colours.
    <html lang={locale} data-theme={theme} className="h-full">
      <body className="min-h-full bg-canvas text-ink antialiased">
        <WebVitalsReporter />
        <I18nProvider locale={locale} messages={messages}>
          <ThemeProvider initialTheme={theme}>
            <MotionProvider>
              <ToastProvider>{children}</ToastProvider>
            </MotionProvider>
          </ThemeProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
