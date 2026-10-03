/**
 * Colour theme of the site: dark (the default), light, or the system's
 * setting. The choice lives in the `aw_theme` cookie, so the server renders
 * <html data-theme="…"> right away and the page never flashes the other
 * theme; "system" follows prefers-color-scheme live through CSS
 * (`color-scheme: light dark`, see globals.css).
 */

export const THEMES = ["dark", "light", "system"] as const;

export type Theme = (typeof THEMES)[number];

export const DEFAULT_THEME: Theme = "dark";

export const THEME_COOKIE = "aw_theme";

/** One year: the theme is a preference, not a session. */
export const THEME_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/** The page background of each scheme, for the browser's <meta name="theme-color">. */
export const SCHEME_BACKGROUNDS = { dark: "#141311", light: "#f6f5f2" } as const;

export function isTheme(value: unknown): value is Theme {
  return typeof value === "string" && (THEMES as readonly string[]).includes(value);
}

/** The theme of a cookie value; anything unknown is the default (dark). */
export function parseTheme(value: string | null | undefined): Theme {
  return isTheme(value) ? value : DEFAULT_THEME;
}

/**
 * The two <meta name="theme-color"> entries (light and dark system
 * preference). A fixed theme gives both the same colour, so switching the
 * theme only rewrites their content and never adds or removes tags.
 */
export function themeColors(theme: Theme): { media: string; color: string }[] {
  const forScheme = (scheme: "light" | "dark") =>
    SCHEME_BACKGROUNDS[theme === "system" ? scheme : theme];
  return [
    { media: "(prefers-color-scheme: light)", color: forScheme("light") },
    { media: "(prefers-color-scheme: dark)", color: forScheme("dark") },
  ];
}

/** `document.cookie` assignment that stores the theme for a year on the whole site. */
export function themeCookie(theme: Theme, secure: boolean): string {
  return [
    `${THEME_COOKIE}=${theme}`,
    "path=/",
    `max-age=${THEME_COOKIE_MAX_AGE_SECONDS}`,
    "samesite=lax",
    ...(secure ? ["secure"] : []),
  ].join("; ");
}
