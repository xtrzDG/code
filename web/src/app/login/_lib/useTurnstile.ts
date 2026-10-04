"use client";

/**
 * Renders a Cloudflare Turnstile check into a container and reports its
 * token. The script is loaded once, on first use (the page's CSP allows
 * it through the trusted bundle), and the widget is removed on unmount.
 */

import { useEffect, useRef, useState, type RefObject } from "react";

import type { Theme } from "@/lib/theme";

import {
  LOGIN_ACTION,
  TURNSTILE_SCRIPT_URL,
  turnstileLanguage,
  turnstileTheme,
} from "./botCheck";

interface TurnstileOptions {
  sitekey: string;
  action: string;
  theme: "light" | "dark" | "auto";
  language: string;
  size: "flexible";
  callback: (token: string) => void;
  "error-callback": () => boolean;
  "expired-callback": () => void;
}

interface TurnstileApi {
  render: (
    container: HTMLElement,
    options: TurnstileOptions,
  ) => string | undefined;
  reset: (widgetId: string) => void;
  remove: (widgetId: string) => void;
}

declare global {
  interface Window {
    turnstile?: TurnstileApi;
  }
}

let scriptLoad: Promise<TurnstileApi> | null = null;

function loadTurnstile(): Promise<TurnstileApi> {
  if (window.turnstile) {
    return Promise.resolve(window.turnstile);
  }
  scriptLoad ??= new Promise<TurnstileApi>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = TURNSTILE_SCRIPT_URL;
    script.async = true;
    script.onload = () =>
      window.turnstile
        ? resolve(window.turnstile)
        : reject(new Error("Turnstile missing"));
    script.onerror = () => {
      scriptLoad = null;
      script.remove();
      reject(new Error("Turnstile could not load"));
    };
    document.head.append(script);
  });
  return scriptLoad;
}

export type TurnstileStatus = "loading" | "ready" | "unavailable";

export function useTurnstile(
  container: RefObject<HTMLDivElement | null>,
  options: {
    siteKey: string;
    theme: Theme;
    locale: string;
    onToken: (token: string) => void;
  },
): TurnstileStatus {
  const [status, setStatus] = useState<TurnstileStatus>("loading");
  const onToken = useRef(options.onToken);
  useEffect(() => {
    onToken.current = options.onToken;
  });
  const { siteKey, theme, locale } = options;

  useEffect(() => {
    let widgetId: string | undefined;
    let isCancelled = false;
    loadTurnstile()
      .then((turnstile) => {
        if (isCancelled || !container.current) {
          return;
        }
        widgetId = turnstile.render(container.current, {
          sitekey: siteKey,
          action: LOGIN_ACTION,
          theme: turnstileTheme(theme),
          language: turnstileLanguage(locale),
          size: "flexible",
          callback: (token) => onToken.current(token),
          // Turnstile retries by itself; the page only says so.
          "error-callback": () => {
            setStatus("unavailable");
            return true;
          },
          "expired-callback": () => {
            if (widgetId) {
              turnstile.reset(widgetId);
            }
          },
        });
        setStatus("ready");
      })
      .catch(() => {
        if (!isCancelled) {
          setStatus("unavailable");
        }
      });
    return () => {
      isCancelled = true;
      if (widgetId) {
        window.turnstile?.remove(widgetId);
      }
    };
  }, [container, siteKey, theme, locale]);

  return status;
}
