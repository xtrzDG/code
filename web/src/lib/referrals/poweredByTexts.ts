/**
 * "Powered by Assistant Workshop" in the languages a customer reads the
 * chat page and the printed table card in (the widget script has the same
 * texts); English for any other language.
 */

const POWERED_BY: Readonly<Record<string, string>> = {
  en: "Powered by Assistant Workshop",
  de: "Bereitgestellt von Assistant Workshop",
  fr: "Propulsé par Assistant Workshop",
  es: "Con la tecnología de Assistant Workshop",
  it: "Realizzato con Assistant Workshop",
  pt: "Desenvolvido com Assistant Workshop",
  pl: "Działa dzięki Assistant Workshop",
  lt: "Veikia su Assistant Workshop",
  lv: "Darbina Assistant Workshop",
  et: "Teenust pakub Assistant Workshop",
  fi: "Palvelun tarjoaa Assistant Workshop",
  nb: "Levert av Assistant Workshop",
  ru: "Работает на Assistant Workshop",
  uk: "Працює на Assistant Workshop",
  kk: "Assistant Workshop негізінде жұмыс істейді",
  ka: "მუშაობს Assistant Workshop-ზე",
  hy: "Աշխատում է Assistant Workshop-ով",
  az: "Assistant Workshop ilə işləyir",
  tr: "Assistant Workshop ile çalışır",
  uz: "Assistant Workshop asosida ishlaydi",
  he: "מופעל על ידי Assistant Workshop",
  ar: "مدعوم من Assistant Workshop",
  fa: "با پشتیبانی Assistant Workshop",
  ur: "Assistant Workshop کی مدد سے",
  hi: "Assistant Workshop द्वारा संचालित",
  zh: "由 Assistant Workshop 提供支持",
  ja: "Assistant Workshop で作成",
  ko: "Assistant Workshop 제공",
  vi: "Được hỗ trợ bởi Assistant Workshop",
};

/** The "Powered by" line in a language tag's base language ("pt-BR" → pt), else English. */
export function poweredByText(language: string): string {
  const base = language.toLowerCase().split(/[-_]/)[0] ?? "en";
  return POWERED_BY[base] ?? POWERED_BY.en ?? "Powered by Assistant Workshop";
}
