"use client";

/**
 * Registers the cabinet's service worker (public/sw.js) on signed-in
 * pages of a production build, so the cabinet can be installed as an app
 * and shows its offline page without a connection. After a change of
 * language or theme it asks the worker to keep the offline page again, so
 * that page speaks the same language and wears the same theme.
 */

import { useEffect } from "react";

import { useI18n } from "@/i18n/client";

import { useTheme } from "../theme/ThemeProvider";

/** What the kept offline page was rendered with (per browser). */
const OFFLINE_PAGE_KEY = "aw_offline_page";

const isEnabled = () => process.env.NODE_ENV === "production" && typeof navigator !== "undefined" && "serviceWorker" in navigator;

export function ServiceWorker() {
  const { locale } = useI18n();
  const { theme } = useTheme();

  useEffect(() => {
    if (isEnabled()) {
      navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    if (!isEnabled()) {
      return;
    }
    const rendering = `${locale}:${theme}`;
    let kept: string | null = null;
    try {
      kept = window.localStorage.getItem(OFFLINE_PAGE_KEY);
    } catch {
      // Storage may be blocked: the page is then kept again on every load.
    }
    if (kept === rendering) {
      return;
    }
    void navigator.serviceWorker.ready.then((registration) => {
      registration.active?.postMessage({ type: "refresh-offline-page" });
      try {
        window.localStorage.setItem(OFFLINE_PAGE_KEY, rendering);
      } catch {
        // Nothing to remember it in; harmless.
      }
    });
  }, [locale, theme]);

  return null;
}
