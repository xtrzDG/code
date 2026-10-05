/**
 * Unused files, exports and dependencies of the cabinet: `npm run knip`,
 * run by CI. The Next.js, Vitest, Playwright and ESLint plugins find their
 * own entry points; the e2e specs, reporters and scripts are entries too.
 * An export only its own file uses is not exported: drop the `export`.
 */

import type { KnipConfig } from "knip";

const config: KnipConfig = {
  entry: ["e2e/**/*.ts", "scripts/**/*.{mjs,ts}"],
  project: ["src/**/*.{ts,tsx}", "e2e/**/*.ts", "scripts/**/*.{mjs,ts}"],
  // Tailwind is loaded by `@import "tailwindcss"` in CSS; the gen:* scripts call the backend's `uv`.
  ignoreDependencies: ["tailwindcss"],
  ignoreBinaries: ["uv"],
  ignoreIssues: {
    // The typed facade of the API description: its names follow the schema.
    "src/api/types.ts": ["types"],
    // Files other wave-14 packages change (admin actions, the spend guard, booking
    // confirmation): their unused exports go when those packages are merged and
    // knip runs again at the integration; then these lines go too.
    "src/app/admin/_lib/*.ts": ["exports", "types"],
    "src/app/admin/_components/system/useSystemFormat.ts": ["types"],
    "src/app/b/[[]businessId]/assistant/channels/_lib/*.ts": ["exports", "types"],
    "src/app/c/[[]slug]/privacy/_texts/noticeTypes.ts": ["types"],
  },
};

export default config;
