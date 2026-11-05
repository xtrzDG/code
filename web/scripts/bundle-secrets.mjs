/**
 * What must never ship in the cabinet's build (WEB-05): a key, a token or a
 * private key written into a browser or server bundle, and the value of a
 * secret variable a build read into the code. `scan-bundle-secrets.mjs`
 * walks `.next/static` (the browser's files) and `.next/server` with these
 * rules after every CI build (job "web-build") and fails on a hit.
 *
 * Two kinds of rules:
 *  - key shapes: the prefixes and formats of the platform's providers
 *    (Stripe, ElevenLabs, the platform's own API keys, Sentry, the model
 *    providers) and of common cloud credentials, in every scanned file;
 *  - variable values: every secret-looking variable of the cabinet's and
 *    the API's `.env.example` that the scanning environment has a value for
 *    (a build machine with real values) must not appear in the browser's
 *    files: `.next/static` and the pages the build prerendered, which the
 *    server sends as they are (`isBrowserFile`). CI's build has none, so
 *    there the key shapes decide.
 *
 * Pure: the scanning script reads the files and passes their text in.
 */

/** Key shapes, each with the name a finding reports. */
export const SECRET_RULES = [
  { name: "Stripe secret or restricted key", pattern: /\b[rs]k_(?:live|test)_[0-9A-Za-z]{10,}/g },
  { name: "webhook signing secret (whsec_)", pattern: /\bwhsec_[0-9A-Za-z+/=_-]{16,}/g },
  { name: "ElevenLabs API key", pattern: /\bsk_[0-9a-f]{48}\b/g },
  { name: "ElevenLabs key in an xi-api-key header", pattern: /xi-api-key["'`]?\s*[:=,]\s*["'`][0-9A-Za-z_-]{20,}/gi },
  { name: "AWS access key id", pattern: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g },
  { name: "PEM key or certificate", pattern: /-----BEGIN [A-Z0-9 ]{0,40}-----/g },
  { name: "Anthropic API key", pattern: /\bsk-ant-[0-9A-Za-z_-]{20,}/g },
  { name: "OpenAI API key", pattern: /\bsk-(?!ant-)(?:proj-|svcacct-)?[0-9A-Za-z_-]{40,}/g },
  { name: "Sentry auth token", pattern: /\bsntry[su]_[0-9A-Za-z+/=_-]{20,}/g },
  { name: "Sentry DSN with its key", pattern: /https:\/\/[0-9a-f]{32}@o\d+\.ingest\./g },
  { name: "GitHub token", pattern: /\b(?:gh[oprsu]_[0-9A-Za-z]{36,}|github_pat_[0-9A-Za-z_]{40,})/g },
  { name: "Google API key", pattern: /\bAIza[0-9A-Za-z_-]{35}\b/g },
  { name: "Twilio API key", pattern: /\bSK[0-9a-f]{32}\b/g },
  { name: "Telegram bot token", pattern: /\b\d{8,10}:AA[0-9A-Za-z_-]{33}\b/g },
  { name: "Slack token", pattern: /\bxox[abprs]-[0-9A-Za-z-]{10,}/g },
  { name: "the platform's API key", pattern: /\bawk_[a-z2-7]{8}_[0-9A-Za-z]{20,}/g },
];

/** Variables that hold a secret (or the API's internal address) by their name. */
const SECRET_VARIABLE = /SECRET|TOKEN|PASSWORD|PRIVATE|_KEY|DSN/;
/** Look secret by name but are public or not secret: a site key, public keys, a count, a switch. */
const NOT_SECRET_VARIABLE = /PUBLIC|SITE_KEY|_TOKENS$|REQUIRED$/;
const INTERNAL_ADDRESS_VARIABLES = new Set(["BACKEND_URL"]);
/** Shorter values (a port, "true", a hop count) say nothing and would match anywhere. */
const SHORTEST_VALUE = 16;
const SHOWN_PREFIX = 6;

/** Prerendered pages, their RSC payloads and route bodies, sent to browsers as they are. */
const PRERENDERED_FILE = /^server\/(?:app|pages)\/.*\.(?:html|rsc|body)$/;

/** Whether browsers receive a build file (`path` relative to the build directory, `/`-separated). */
export function isBrowserFile(path) {
  return path.startsWith("static/") || PRERENDERED_FILE.test(path);
}

/** The variable names a `.env.example` documents, set or commented out (`# NAME=`). */
export function documentedVariables(envExample) {
  const names = new Set();
  for (const line of envExample.split("\n")) {
    const match = /^#?\s*([A-Z][A-Z0-9_]*)=/.exec(line.trim());
    if (match?.[1]) {
      names.add(match[1]);
    }
  }
  return [...names];
}

/** Whether a variable's value must never reach the browser. */
export function isSecretVariable(name) {
  return INTERNAL_ADDRESS_VARIABLES.has(name) || (SECRET_VARIABLE.test(name) && !NOT_SECRET_VARIABLE.test(name));
}

/** The secret variables `env` has a value for, long enough to search for. */
export function secretValues(names, env) {
  const found = [];
  for (const name of new Set(names)) {
    const value = env[name]?.trim();
    if (value && value.length >= SHORTEST_VALUE && isSecretVariable(name)) {
      found.push({ name, value });
    }
  }
  return found;
}

/** A hit as a log may show it: never the secret itself. */
export function masked(text) {
  return `${text.slice(0, SHOWN_PREFIX)}… (${text.length} characters)`;
}

/**
 * The key shapes in one file's text, and (for a browser file) the secret
 * variables' values: `{ file, rule, excerpt }` per hit, the excerpt masked.
 */
export function findSecrets(file, text, { values = [], isBrowserFile = false } = {}) {
  const hits = [];
  for (const { name, pattern } of SECRET_RULES) {
    for (const match of text.matchAll(pattern)) {
      hits.push({ file, rule: name, excerpt: masked(match[0]) });
    }
  }
  if (isBrowserFile) {
    for (const { name, value } of values) {
      if (text.includes(value)) {
        hits.push({ file, rule: `the value of ${name}`, excerpt: masked(value) });
      }
    }
  }
  return hits;
}
