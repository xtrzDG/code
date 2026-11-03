/**
 * The secret scan of the cabinet's build (WEB-05, scripts/bundle-secrets.mjs,
 * run by CI after `next build`): every key shape is found, ordinary bundle
 * text is not, a hit never prints the secret, and the values of secret
 * variables are searched in the browser's files only. The fake keys are
 * assembled at run time so that no secret scanner reads one in this file.
 *
 * The code never hands a variable to the browser by itself either: no
 * NEXT_PUBLIC_ variable is read and next.config.ts inlines no `env`.
 */

import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import {
  SECRET_RULES,
  documentedVariables,
  findSecrets,
  isSecretVariable,
  masked,
  secretValues,
} from "../../scripts/bundle-secrets.mjs";

const WEB_DIRECTORY = path.resolve(__dirname, "../..");
const join = (...parts: string[]): string => parts.join("");
const letters = (count: number): string => "aB3dE5gH7jK9mN1pQ2rS4tU6vW8xY0z".repeat(4).slice(0, count);
const hex = (count: number): string => "0123456789abcdef".repeat(8).slice(0, count);

/** One sample of every rule, in the order of SECRET_RULES. */
const SAMPLES: [string, string][] = [
  ["Stripe secret or restricted key", `const key = "${join("rk", "_live_", letters(24))}";`],
  ["webhook signing secret (whsec_)", `secret:"${join("whsec", "_", letters(32))}"`],
  ["ElevenLabs API key", `"${join("sk", "_", hex(48))}"`],
  ["ElevenLabs key in an xi-api-key header", `headers:{"${join("xi-", "api-key")}":"${letters(32)}"}`],
  ["AWS access key id", `id="${join("AK", "IA", "ABCDEFGHIJKLMNOP")}"`],
  ["PEM key or certificate", join("-----", "BEGIN EC PRIVATE KEY-----")],
  ["Anthropic API key", join("sk-", "ant-api03-", letters(40))],
  ["OpenAI API key", join("sk-", "proj-", letters(48))],
  ["Sentry auth token", join("sntrys", "_", letters(40))],
  ["Sentry DSN with its key", `dsn:"https://${hex(32)}@o123456.ingest.de.sentry.io/42"`],
  ["GitHub token", join("gh", "p_", letters(36))],
  ["Google API key", join("AI", "za", letters(35))],
  ["Twilio API key", join("S", "K", hex(32))],
  ["Telegram bot token", `${join("123456789", ":AA")}${letters(33)}`],
  ["Slack token", join("xox", "b-", "1234-5678-", letters(12))],
  ["the platform's API key", join("awk", "_abcd2345_", letters(40))],
];

/** Text every build carries that resembles a key and is none. */
const ORDINARY = [
  'className="mask-image-linear task-list risk-high desk_top"',
  `"static/chunks/${hex(16)}.js" sha384-${letters(40)}`,
  `const id = "${join("sk", "_", hex(40))}"; // too short for a key`,
  'headers.set("xi-api-key", apiKey)',
  "BEGIN:VCALENDAR -----",
  "AKIA lower akiaABCDEFGHIJKLMNOP",
];

describe("the key shapes", () => {
  it("cover every rule with a sample, each found under its own name", () => {
    expect(SAMPLES.map(([rule]) => rule)).toEqual(SECRET_RULES.map((rule) => rule.name));
    for (const [rule, text] of SAMPLES) {
      expect(findSecrets("chunk.js", text).map((hit) => hit.rule), rule).toEqual([rule]);
    }
  });

  it("leave the ordinary text of a bundle alone", () => {
    for (const text of ORDINARY) {
      expect(findSecrets("chunk.js", text), text).toEqual([]);
    }
  });

  it("find every hit of a file, never printing the secret itself", () => {
    const key = join("sk", "_test_", letters(30));
    const hits = findSecrets("static/chunks/a.js", `a="${key}";b="${key}"`);

    expect(hits).toHaveLength(2);
    expect(hits[0]).toEqual({ file: "static/chunks/a.js", rule: "Stripe secret or restricted key", excerpt: masked(key) });
    expect(JSON.stringify(hits)).not.toContain(key.slice(8));
    expect(masked(key)).toBe(`${key.slice(0, 6)}… (${key.length} characters)`);
  });
});

describe("the secret variables' values", () => {
  const ENV_EXAMPLE = [
    "# Base URL of the API.",
    "BACKEND_URL=http://localhost:8000",
    "# SENTRY_AUTH_TOKEN=",
    "#   indented comment = not a variable",
    "TURNSTILE_SITE_KEY=",
    "STRIPE_SECRET_KEY=",
    "WEB_PUSH_VAPID_PUBLIC_KEY=",
    "LLM_MAX_OUTPUT_TOKENS=1024",
    "ADMIN_PASSKEY_REQUIRED=false",
    "SITE_URL=https://app.example.com",
  ].join("\n");

  it("are the documented variables that hold a secret or the API's internal address", () => {
    const names = documentedVariables(ENV_EXAMPLE);

    expect(names).toEqual([
      "BACKEND_URL",
      "SENTRY_AUTH_TOKEN",
      "TURNSTILE_SITE_KEY",
      "STRIPE_SECRET_KEY",
      "WEB_PUSH_VAPID_PUBLIC_KEY",
      "LLM_MAX_OUTPUT_TOKENS",
      "ADMIN_PASSKEY_REQUIRED",
      "SITE_URL",
    ]);
    expect(names.filter(isSecretVariable)).toEqual(["BACKEND_URL", "SENTRY_AUTH_TOKEN", "STRIPE_SECRET_KEY"]);
  });

  it("are searched only when set, and only when long enough to mean something", () => {
    const env = {
      BACKEND_URL: "http://api.internal:8000",
      SENTRY_AUTH_TOKEN: "short",
      STRIPE_SECRET_KEY: undefined,
      SITE_URL: "https://app.example.com",
    };

    expect(secretValues(["BACKEND_URL", "SENTRY_AUTH_TOKEN", "STRIPE_SECRET_KEY", "SITE_URL", "BACKEND_URL"], env)).toEqual([
      { name: "BACKEND_URL", value: "http://api.internal:8000" },
    ]);
  });

  it("must not reach the browser's files; the server's may name them", () => {
    const values = [{ name: "BACKEND_URL", value: "http://api.internal:8000" }];
    const text = 'fetch("http://api.internal:8000/v1/me")';

    expect(findSecrets("static/chunks/a.js", text, { values, isBrowserFile: true })).toEqual([
      { file: "static/chunks/a.js", rule: "the value of BACKEND_URL", excerpt: masked("http://api.internal:8000") },
    ]);
    expect(findSecrets("server/app/page.js", text, { values })).toEqual([]);
  });
});

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return sourceFiles(full);
    }
    return /\.(ts|tsx|mts)$/.test(entry.name) && !entry.name.includes(".test.") ? [full] : [];
  });
}

describe("the cabinet's code", () => {
  it("reads no NEXT_PUBLIC_ variable, which Next.js would write into the browser's files", () => {
    const readers = sourceFiles(path.join(WEB_DIRECTORY, "src")).filter((file) =>
      readFileSync(file, "utf8").includes("NEXT_PUBLIC_"),
    );

    expect(readers).toEqual([]);
  });

  it("inlines no variable through next.config.ts", () => {
    const config = readFileSync(path.join(WEB_DIRECTORY, "next.config.ts"), "utf8");

    expect(config).not.toMatch(/^\s*env\s*:/m);
    expect(config).not.toContain("NEXT_PUBLIC_");
  });
});
