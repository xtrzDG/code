/** "русский" -> "Русский" (names used as labels start with a capital). */
export function capitalizeFirst(text: string, locale?: string): string {
  // Georgian (Mkhedruli) has no capitals: uppercasing would give Mtavruli ("Ქართული").
  if (text.length === 0 || /^[\u10D0-\u10FF]/.test(text)) {
    return text;
  }
  return text.charAt(0).toLocaleUpperCase(locale) + text.slice(1);
}
