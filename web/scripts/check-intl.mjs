#!/usr/bin/env node
/**
 * Fails when this Node cannot format the cabinet's languages: a build with
 * "small ICU" (English only) or without Georgian data renders Georgian and
 * Russian dates, plurals and lists in English, or crashes on them, during
 * server rendering. CI runs it before the build and the cabinet's image
 * before `next build` (`npm run check:intl`).
 */

const LOCALES = ["ka", "ru", "en"];
const DATE = new Date(Date.UTC(2026, 9, 16, 12, 0));
const GEORGIAN_LETTER = /[ა-ჿ]/;
const CYRILLIC_LETTER = /[Ѐ-ӿ]/;

const problems = [];

function check(condition, message) {
  if (!condition) {
    problems.push(message);
  }
}

function attempt(label, run) {
  try {
    run();
  } catch (error) {
    problems.push(`${label} failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}

check(Boolean(process.versions.icu), "Node was built without ICU (process.versions.icu is empty).");

for (const [name, api] of Object.entries({
  DateTimeFormat: Intl.DateTimeFormat,
  NumberFormat: Intl.NumberFormat,
  PluralRules: Intl.PluralRules,
  RelativeTimeFormat: Intl.RelativeTimeFormat,
  ListFormat: Intl.ListFormat,
})) {
  const supported = api.supportedLocalesOf(LOCALES);
  check(
    LOCALES.every((locale) => supported.includes(locale)),
    `Intl.${name} supports only ${JSON.stringify(supported)} of ${JSON.stringify(LOCALES)}: install a Node with full ICU.`,
  );
}

attempt("Georgian month names", () => {
  const month = new Intl.DateTimeFormat("ka", { month: "long", timeZone: "UTC" }).format(DATE);
  check(GEORGIAN_LETTER.test(month), `A Georgian month name came out as “${month}”.`);
});
attempt("Russian dates", () => {
  const date = new Intl.DateTimeFormat("ru", { dateStyle: "medium", timeZone: "UTC" }).format(DATE);
  check(CYRILLIC_LETTER.test(date), `A Russian date came out as “${date}”.`);
});
attempt("Russian plural rules", () => {
  const rules = new Intl.PluralRules("ru");
  check(
    rules.select(1) === "one" && rules.select(3) === "few" && rules.select(5) === "many",
    "Russian plural rules are not the CLDR ones (1 one, 3 few, 5 many).",
  );
});
attempt("Georgian relative time", () => {
  const text = new Intl.RelativeTimeFormat("ka", { numeric: "auto" }).format(-1, "day");
  check(GEORGIAN_LETTER.test(text), `“Yesterday” in Georgian came out as “${text}”.`);
});

if (problems.length > 0) {
  console.error(`Intl is not ready for ${LOCALES.join(", ")} (Node ${process.version}, ICU ${process.versions.icu ?? "none"}):`);
  for (const problem of problems) {
    console.error(`  - ${problem}`);
  }
  process.exit(1);
}

process.stdout.write(`Intl is ready for ${LOCALES.join(", ")} (Node ${process.version}, ICU ${process.versions.icu}).\n`);
