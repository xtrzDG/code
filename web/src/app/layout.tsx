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
import { cn } from "@/lib/cn";
import { motionAttribute } from "@/lib/motionPreference";
import { themeColors } from "@/lib/theme";
import { getMotionPreference } from "@/server/motionPreference";
import { getTheme } from "@/server/theme";
import { getViewerTimeZone } from "@/server/viewerTimeZone";

import { brandFontVariables } from "./fonts";
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
  return (
    // data-theme, data-motion and dir are rendered on the server, so the first
    // paint already has the right colours, stays still for a person who asked
    // for less motion, and reads in the language's direction (Hebrew: right to left).
    // The brand typeface's families come as CSS variables (fonts.ts, globals.css).
    <html
      lang={locale}
      dir={direction}
      data-theme={theme}
      data-motion={motionAttribute(motion)}
      className={cn("h-full", brandFontVariables)}
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
