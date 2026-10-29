import "server-only";

import { cookies } from "next/headers";

import { THEME_COOKIE, parseTheme, type Theme } from "@/lib/theme";

/** The colour theme of the current request (the `aw_theme` cookie, else dark). */
export async function getTheme(): Promise<Theme> {
  return parseTheme((await cookies()).get(THEME_COOKIE)?.value);
}
