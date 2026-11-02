import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

/**
 * The only files that may hand markup to the browser (INP-02): each was
 * reviewed and builds its markup from constant or escaped parts, never
 * from a customer's, a model's or an owner's text. Everything else renders
 * text through React, which escapes it. src/lib/csp/htmlSinks.test.ts
 * keeps this list and the code in step.
 */
const REVIEWED_HTML_SINK_FILES = [
  // The Trusted Types bootstrap: a constant script with the page's nonce.
  "src/components/csp/TrustedTypesScript.tsx",
  // Structured data for search engines, serialized with every "<" escaped.
  "src/app/_landing/JsonLd.tsx",
  // The hosted chat's empty container, which the widget fills itself.
  "src/app/c/[[]slug]/page.tsx",
  // The printable table card in a frame's srcdoc, built from escaped parts.
  "src/app/b/[[]businessId]/assistant/channels/_components/TableCardPanel.tsx",
];

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "react-hooks/exhaustive-deps": "error",
      "@typescript-eslint/consistent-type-imports": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-console": ["error", { allow: ["warn", "error"] }],
      // Zod without its eval-based JIT (src/lib/zod.ts): the CSP forbids eval.
      "no-restricted-imports": [
        "error",
        { paths: [{ name: "zod", message: 'Import { z } from "@/lib/zod" (no eval under the CSP).' }] },
      ],
    },
  },
  {
    // Many small files that each do a little: at most 300 lines, counting
    // every line (blank lines and comments too). Generated files are exempt.
    files: ["src/**/*.{ts,tsx,mts}", "e2e/**/*.{ts,tsx,mts}"],
    ignores: ["src/**/*.generated.ts"],
    rules: {
      "max-lines": ["error", { max: 300, skipBlankLines: false, skipComments: false }],
    },
  },
  {
    // The landing's 3D scene (react-three-fiber): useFrame callbacks run in the
    // render loop, outside React's render, and move three.js objects in place
    // (positions, uniforms, scene.environment) by design. The React Compiler's
    // immutability check cannot tell those callbacks from render code.
    files: ["src/app/_landing/scene/**/*.{ts,tsx}"],
    rules: { "react-hooks/immutability": "off" },
  },
  {
    // Dates and times in a UI language come from lib/intl (Georgian in every
    // browser) through lib/format.ts with an explicit time zone: a format
    // without one takes the zone of whatever runs it, so the server and the
    // browser write different text and hydration fails (React #418).
    files: ["src/**/*.{ts,tsx,mts}"],
    ignores: ["src/lib/intl/**"],
    rules: {
      "no-restricted-syntax": [
        "error",
        {
          selector: "NewExpression[callee.object.name='Intl'][callee.property.name='DateTimeFormat']",
          message: "Use formatDateTime/formatDate/formatTime (lib/format) with a timeZone, or lib/intl/calendarFields.",
        },
        {
          selector: "CallExpression[callee.object.name='Intl'][callee.property.name='DateTimeFormat']",
          message: "Use formatDateTime/formatDate/formatTime (lib/format) with a timeZone, or lib/intl/calendarFields.",
        },
        {
          selector: "CallExpression[callee.property.name=/^toLocale(Date|Time)?String$/]",
          message: "toLocale*String formats in the zone and language of whatever runs it; use lib/format with a timeZone.",
        },
      ],
    },
  },
  {
    // Untrusted text is rendered as text (INP-02): no raw HTML sink outside
    // the reviewed files. Tests may build markup to render into.
    files: ["src/**/*.{ts,tsx,mts}"],
    ignores: ["src/**/*.test.{ts,tsx}", "src/test/**", ...REVIEWED_HTML_SINK_FILES],
    rules: {
      "react/no-danger": "error",
      "react/forbid-dom-props": ["error", { forbid: [{ propName: "srcDoc", message: "Markup in a frame is a reviewed HTML sink (REVIEWED_HTML_SINK_FILES)." }] }],
      "no-restricted-properties": [
        "error",
        { property: "innerHTML", message: "Render text through React; markup sinks are reviewed (REVIEWED_HTML_SINK_FILES)." },
        { property: "outerHTML", message: "Render text through React; markup sinks are reviewed (REVIEWED_HTML_SINK_FILES)." },
        { property: "insertAdjacentHTML", message: "Render text through React; markup sinks are reviewed (REVIEWED_HTML_SINK_FILES)." },
        { property: "createContextualFragment", message: "Render text through React; markup sinks are reviewed (REVIEWED_HTML_SINK_FILES)." },
        { object: "document", property: "write", message: "document.write is never used." },
        { object: "document", property: "writeln", message: "document.write is never used." },
      ],
    },
  },
  {
    // Playwright fixtures receive a `use` callback that is not React's `use`.
    files: ["e2e/**/*.ts"],
    rules: { "react-hooks/rules-of-hooks": "off" },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "coverage/**",
    "next-env.d.ts",
    // Generated by `npm run gen:api`.
    "src/api/schema.d.ts",
    "e2e/.artifacts/**",
  ]),
]);

export default eslintConfig;
