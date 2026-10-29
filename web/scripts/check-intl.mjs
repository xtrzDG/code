#!/usr/bin/env node
/**
 * Fails when this Node cannot format the cabinet's languages: a build with
 * "small ICU" (English only) renders Italian dates, plurals and lists in
 * English, or crashes on them, during server rendering. CI runs it before
 * the build and the cabinet's image before `next build` (`npm run check:intl`).
 */

// The cabinet's languages (src/i18n/config.ts, LOCALES).
const LOCALES = ["en", "it"];
const DATE = new Date(Date.UTC(2026, 9, 16, 12, 0));

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

attempt("Italian month names", () => {
  const month = new Intl.DateTimeFormat("it", { month: "long", timeZone: "UTC" }).format(DATE);
  check(month === "ottobre", `An Italian month name came out as “${month}”.`);
});
attempt("Italian dates", () => {
  const date = new Intl.DateTimeFormat("it", { dateStyle: "medium", timeZone: "UTC" }).format(DATE);
  check(date === "16 ott 2026", `An Italian date came out as “${date}”.`);
});
attempt("Italian numbers", () => {
  // The cabinet groups thousands always (src/lib/intl/formatters.ts).
  const amount = new Intl.NumberFormat("it", { style: "currency", currency: "EUR", useGrouping: "always" }).format(1234.5);
  check(amount.replace(/\s/g, " ") === "1.234,50 €", `An Italian amount came out as “${amount}”.`);
});
attempt("Italian plural rules", () => {
  const rules = new Intl.PluralRules("it");
  check(
    rules.select(1) === "one" && rules.select(5) === "other" && rules.select(1_000_000) === "many",
    "Italian plural rules are not the CLDR ones (1 one, 5 other, 1 000 000 many).",
  );
});
attempt("Italian lists", () => {
  const list = new Intl.ListFormat("it", { type: "conjunction" }).format(["a", "b", "c"]);
  check(list === "a, b e c", `An Italian list came out as “${list}”.`);
});
attempt("Italian relative time", () => {
  const text = new Intl.RelativeTimeFormat("it", { numeric: "auto" }).format(-1, "day");
  check(text === "ieri", `“Yesterday” in Italian came out as “${text}”.`);
});

if (problems.length > 0) {
  console.error(`Intl is not ready for ${LOCALES.join(", ")} (Node ${process.version}, ICU ${process.versions.icu ?? "none"}):`);
  for (const problem of problems) {
    console.error(`  - ${problem}`);
  }
  process.exit(1);
}

process.stdout.write(`Intl is ready for ${LOCALES.join(", ")} (Node ${process.version}, ICU ${process.versions.icu}).\n`);
