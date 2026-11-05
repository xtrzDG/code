/**
 * The cabinet's translations at a glance, the web part of the translation
 * tooling (scripts/translate_catalogs.py at the repository root covers the
 * backend's owner texts):
 *
 *   node --no-warnings scripts/translation-status.mjs              # one line per locale
 *   node --no-warnings scripts/translation-status.mjs --missing he # the English texts he lacks, as JSON
 *   node --no-warnings scripts/translation-status.mjs --check      # exit 1 when the picker and completeness disagree
 *
 * A locale joins LOCALES (src/i18n/config.ts) while it is translated and
 * CABINET_LANGUAGES once every text is there; NEEDS_REVIEW_LOCALES marks
 * drafts no native speaker has read yet. Help articles live in
 * docs/help/<locale>/, a `status: needs_review` line marks a draft.
 *
 * Node reads the TypeScript dictionaries by stripping their types (Node
 * 22.12+); a small resolve hook adds the `.ts` their imports leave out.
 */

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { register } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";

const WEB_DIRECTORY = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const HELP_DIRECTORY = path.join(WEB_DIRECTORY, "..", "docs", "help");

register(
  `data:text/javascript,${encodeURIComponent(`
export async function resolve(specifier, context, next) {
  if (/^\\.{1,2}\\//.test(specifier) && !/\\.[cm]?[jt]sx?$/.test(specifier)) {
    try {
      return await next(specifier + ".ts", context);
    } catch {
      // Not a TypeScript module: resolve it as written.
    }
  }
  return next(specifier, context);
}`)}`,
);

const { CABINET_LANGUAGES, LOCALES, NEEDS_REVIEW_LOCALES } = await import("../src/i18n/config.ts");
const { missingTexts, translationStatus } = await import("../src/i18n/translationStatus.ts");

async function dictionary(locale) {
  const dictionaryModule = await import(`../src/i18n/messages/${locale}.ts`);
  return dictionaryModule[locale];
}

function helpArticles(locale) {
  const folder = path.join(HELP_DIRECTORY, locale);
  if (!existsSync(folder)) {
    return { articles: 0, drafts: 0 };
  }
  const files = readdirSync(folder).filter((name) => name.endsWith(".md"));
  const drafts = files.filter((name) => /^status:\s*needs_review\s*$/m.test(readFileSync(path.join(folder, name), "utf8").split("---")[1] ?? ""));
  return { articles: files.length, drafts: drafts.length };
}

const args = process.argv.slice(2);
const english = await dictionary("en");

if (args[0] === "--missing") {
  const locale = args[1];
  if (!LOCALES.includes(locale)) {
    process.stderr.write(`Unknown locale ${locale ?? "(none)"}: one of ${LOCALES.join(", ")}.\n`);
    process.exit(2);
  }
  process.stdout.write(`${JSON.stringify(missingTexts(english, await dictionary(locale)), null, 2)}\n`);
  process.exit(0);
}

const problems = [];
const rows = [];
for (const locale of LOCALES) {
  const status = translationStatus(english, await dictionary(locale));
  const offered = CABINET_LANGUAGES.includes(locale);
  const help = helpArticles(locale);
  rows.push(
    [
      locale.padEnd(4),
      `${status.percent}%`.padStart(5),
      `${status.total - status.missing.length}/${status.total} texts`.padEnd(18),
      offered ? "in the picker" : "not offered  ",
      NEEDS_REVIEW_LOCALES.includes(locale) ? "needs review" : "reviewed    ",
      `help ${help.articles} (${help.drafts} drafts)`,
    ].join("  "),
  );
  if (offered !== (status.missing.length === 0)) {
    problems.push(`${locale}: ${offered ? "offered with" : "complete but not offered;"} ${status.missing.length} texts missing`);
  }
  if (status.extra.length > 0) {
    problems.push(`${locale}: ${status.extra.length} texts English no longer has (${status.extra.slice(0, 3).join(", ")}…)`);
  }
}
process.stdout.write(`${rows.join("\n")}\n`);
if (problems.length > 0) {
  process.stdout.write(`\n${problems.join("\n")}\n`);
}
if (args.includes("--check") && problems.length > 0) {
  process.exit(1);
}
