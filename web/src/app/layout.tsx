import type { Metadata, Viewport } from "next";

import { ToastProvider } from "@/components/ui/Toast";
import { I18nProvider } from "@/i18n/client";
import { getI18n } from "@/i18n/server";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return {
    title: { default: t("common.appName"), template: `%s · ${t("common.appName")}` },
    description: t("common.tagline"),
    robots: { index: false, follow: false },
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f6f8" },
    { media: "(prefers-color-scheme: dark)", color: "#0b0d12" },
  ],
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const { locale, messages } = await getI18n();
  return (
    <html lang={locale} className="h-full">
      <body className="min-h-full bg-canvas text-ink antialiased">
        <I18nProvider locale={locale} messages={messages}>
          <ToastProvider>{children}</ToastProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
