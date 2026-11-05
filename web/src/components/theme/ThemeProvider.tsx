"use client";

/**
 * The colour theme on the client. The root layout renders
 * <html data-theme="…"> from the `aw_theme` cookie and passes the same value
 * here; switching rewrites the attribute, the cookie and the browser's
 * theme colour at once, without a reload or a server round trip.
 *
 *     const { theme, setTheme } = useTheme();
 */

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { themeColors, themeCookie, type Theme } from "@/lib/theme";

interface ThemeApi {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeApi | null>(null);

function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  root.dataset.theme = theme;
  document.cookie = themeCookie(theme, window.location.protocol === "https:");
  const colors = themeColors(theme);
  for (const meta of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) {
    const entry = colors.find((color) => color.media === meta.media);
    if (entry) {
      meta.content = entry.color;
    }
  }
}

export function ThemeProvider({ initialTheme, children }: { initialTheme: Theme; children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(initialTheme);

  const setTheme = useCallback((next: Theme) => {
    applyTheme(next);
    setThemeState(next);
  }, []);

  const api = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={api}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeApi {
  const api = useContext(ThemeContext);
  if (!api) {
    throw new Error("useTheme() must be used inside <ThemeProvider>.");
  }
  return api;
}
