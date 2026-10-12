/**
 * The site's typeface: Noto Sans (variable weight, 100–900) for Latin and
 * Cyrillic, with Noto Sans Georgian and Noto Sans Hebrew from the same
 * family, so a page looks the same on every operating system and in every
 * cabinet language (en, de, ru, ka, he). Self-hosted from public/fonts/
 * (SIL Open Font License, public/fonts/OFL.txt; provenance in web/README.md,
 * "Typeface").
 *
 * One file per script, each with its own unicode-range: a page downloads
 * only the scripts it shows. Latin (digits, punctuation, every English and
 * German word) is preloaded; Cyrillic, Georgian, Hebrew and the extended
 * Latin letters and currency signs (ğ, ș, ə, ₾, ₽, ₪…) come when the
 * first such character is on screen.
 *
 * `display: "optional"`: a font that is not there within about 100 ms of
 * being needed is not swapped in later (the next page has it from the
 * cache), so text never jumps: the layout shift stays 0. Meanwhile Arial,
 * resized to Noto Sans's metrics (next/font's size-adjusted fallback),
 * takes its place; where there is no Arial the system font does.
 *
 * Each call is its own family (next/font names them), so globals.css lists
 * them in --font-sans: the scripts first, then Latin with its fallback.
 * next/font needs the options written out as literals.
 */

import localFont from "next/font/local";

const latin = localFont({
  src: "../../public/fonts/noto-sans-latin-wght.woff2",
  weight: "100 900",
  style: "normal",
  display: "optional",
  variable: "--font-brand-latin",
  adjustFontFallback: "Arial",
  declarations: [
    {
      prop: "unicode-range",
      value:
        "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
    },
  ],
});

const latinExtended = localFont({
  src: "../../public/fonts/noto-sans-latin-ext-wght.woff2",
  weight: "100 900",
  style: "normal",
  display: "optional",
  preload: false,
  variable: "--font-brand-latin-ext",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+0100-0130,U+0132-0151,U+0154-017F,U+0218-021B,U+0259,U+1E9E,U+20A0-20AB,U+20AD-20C0" }],
});

const cyrillic = localFont({
  src: "../../public/fonts/noto-sans-cyrillic-wght.woff2",
  weight: "100 900",
  style: "normal",
  display: "optional",
  preload: false,
  variable: "--font-brand-cyrillic",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116" }],
});

const georgian = localFont({
  src: "../../public/fonts/noto-sans-georgian-wght.woff2",
  weight: "100 900",
  style: "normal",
  display: "optional",
  preload: false,
  variable: "--font-brand-georgian",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+10A0-10FF,U+1C90-1CBA,U+1CBD-1CBF,U+2D00-2D2F" }],
});

const hebrew = localFont({
  src: "../../public/fonts/noto-sans-hebrew-wght.woff2",
  weight: "100 900",
  style: "normal",
  display: "optional",
  preload: false,
  variable: "--font-brand-hebrew",
  adjustFontFallback: false,
  declarations: [{ prop: "unicode-range", value: "U+0590-05FF,U+FB1D-FB4F" }],
});

/** The classes that define the --font-brand-* variables, for <html>. */
export const brandFontVariables = [latin, latinExtended, cyrillic, georgian, hebrew].map((font) => font.variable).join(" ");
