import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";

import { NonceProvider } from "@/components/csp/NonceProvider";
import { TrustedTypesScript } from "@/components/csp/TrustedTypesScript";

import { CabinetMotion } from "@/components/motion/CabinetMotion";
import { MotionPreferenceProvider } from "@/components/motion/MotionPreference";
import { StepUpDialog } from "@/components/security/StepUpDialog";
import { WebVitalsReporter } from "@/components/telemetry/WebVitalsReporter";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { ViewerTimeZoneProvider } from "@/components/time/ViewerTimeZone";
import { ToastProvider } from "@/components/ui/Toast";
import { I18nProvider } from "@/i18n/client";
import { getClientTexts, getI18n } from "@/i18n/server";
import { BRAND_TYPEFACE_CLASS } from "@/lib/brandFonts";
import { cn } from "@/lib/cn";
import { motionAttribute } from "@/lib/motionPreference";
import { themeColors } from "@/lib/theme";
import { NONCE_HEADER } from "@/server/contentSecurityPolicy";
import { getMotionPreference } from "@/server/motionPreference";
import { preloadBrandFonts } from "@/server/brandFontPreload";
import { getTheme } from "@/server/theme";
import { getViewerTimeZone } from "@/server/viewerTimeZone";

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
  const [{ locale, messages, direction }, theme, motion, viewerTimeZone, requestHeaders] = await Promise.all([
    getI18n(),
    getTheme(),
    getMotionPreference(),
    getViewerTimeZone(),
    headers(),
  ]);
  // The proxy's nonce: the Trusted Types policy runs with it, nonce'd <style> elements use it.
  const nonce = requestHeaders.get(NONCE_HEADER) ?? undefined;
  // A public page's client components get only their own texts (i18n/publicScope.ts).
  const clientTexts = await getClientTexts(messages);
  // The cabinet's pages use the brand typeface and preload its files (styles/typeface.css); the
  // public site keeps the system's fonts and loads none, so its first paint waits for no font.
  // It moves in CSS alone too, so its pages load no motion library (CabinetMotion).
  const isCabinetPage = clientTexts.scope === "full";
  if (isCabinetPage) {
    preloadBrandFonts(locale);
  }
  const page = (
    <ToastProvider>
      {children}
      <StepUpDialog />
    </ToastProvider>
  );
  return (
    // data-theme, data-motion and dir are rendered on the server, so the first
    // paint already has the right colours, stays still for a person who asked
    // for less motion, and reads in the language's direction (Hebrew: right to left).
    // On cabinet pages a class names the brand typeface's families (styles/typeface.css).
    <html
      lang={locale}
      dir={direction}
      data-theme={theme}
      data-motion={motionAttribute(motion)}
      className={cn("h-full", isCabinetPage && BRAND_TYPEFACE_CLASS)}
    >
      <head>
        <TrustedTypesScript nonce={nonce} />
      </head>
      <body className="min-h-full bg-canvas text-ink antialiased">
        <WebVitalsReporter />
        <NonceProvider nonce={nonce}>
          <I18nProvider locale={locale} messages={clientTexts.messages} scope={clientTexts.scope}>
            <ThemeProvider initialTheme={theme}>
              <ViewerTimeZoneProvider initialZone={viewerTimeZone}>
                <MotionPreferenceProvider initialPreference={motion}>
                  {isCabinetPage ? <CabinetMotion>{page}</CabinetMotion> : page}
                </MotionPreferenceProvider>
              </ViewerTimeZoneProvider>
            </ThemeProvider>
          </I18nProvider>
        </NonceProvider>
      </body>
    </html>
  );
}
