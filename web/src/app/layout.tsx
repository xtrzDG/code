import type { Metadata, Viewport } from "next";

import { MotionPreferenceProvider } from "@/components/motion/MotionPreference";
import { MotionProvider } from "@/components/motion/MotionProvider";
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
  const [{ locale, messages, direction }, theme, motion, viewerTimeZone] = await Promise.all([
    getI18n(),
    getTheme(),
    getMotionPreference(),
    getViewerTimeZone(),
  ]);
  // A public page's client components get only their own texts (i18n/publicScope.ts).
  const clientTexts = await getClientTexts(messages);
  // The cabinet's pages use the brand typeface and preload its files (styles/typeface.css); the
  // public site keeps the system's fonts and loads none, so its first paint waits for no font.
  const brandTypeface = clientTexts.scope === "full";
  if (brandTypeface) {
    preloadBrandFonts(locale);
  }
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
      className={cn("h-full", brandTypeface && BRAND_TYPEFACE_CLASS)}
    >
      <body className="min-h-full bg-canvas text-ink antialiased">
        <WebVitalsReporter />
        <I18nProvider locale={locale} messages={clientTexts.messages} scope={clientTexts.scope}>
          <ThemeProvider initialTheme={theme}>
            <ViewerTimeZoneProvider initialZone={viewerTimeZone}>
              <MotionPreferenceProvider initialPreference={motion}>
                <MotionProvider animates={clientTexts.scope === "full"}>
                  <ToastProvider>
                    {children}
                    <StepUpDialog />
                  </ToastProvider>
                </MotionProvider>
              </MotionPreferenceProvider>
            </ViewerTimeZoneProvider>
          </ThemeProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
