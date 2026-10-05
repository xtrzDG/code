import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const alias = {
  "@": fileURLToPath(new URL("./src", import.meta.url)),
  // Next.js resolves this marker itself; tests import server modules directly.
  "server-only": fileURLToPath(new URL("./node_modules/next/dist/compiled/server-only/empty.js", import.meta.url)),
};

/**
 * Two projects, one run (`npm test`):
 *
 * - unit: the pure logic (src/**\/*.test.ts) and the e2e suite's own helpers
 *   (shard plan, flaky-test reporter: e2e/**\/*.test.ts), in Node;
 * - components: React components (src/**\/*.test.tsx) rendered in jsdom with
 *   Testing Library and user-event, in the server's zone (TZ=UTC) unless a
 *   test moves it. src/test/ holds their setup and render helpers.
 */
export default defineConfig({
  resolve: { alias },
  test: {
    projects: [
      {
        extends: true,
        test: {
          name: "unit",
          environment: "node",
          include: ["src/**/*.test.ts", "e2e/**/*.test.ts"],
        },
      },
      {
        extends: true,
        test: {
          name: "components",
          environment: "jsdom",
          include: ["src/**/*.test.tsx"],
          setupFiles: ["src/test/setupComponents.ts"],
          env: { TZ: "UTC" },
        },
      },
    ],
    // `npm run test:coverage` (CI): the pure logic of the cabinet, src/lib
    // and every route's _lib, keeps these floors. React hooks (use*.ts) run
    // in the browser and are covered by the Playwright suite (e2e/) and the
    // component tests.
    coverage: {
      provider: "v8",
      include: ["src/lib/**/*.ts", "src/**/_lib/**/*.ts"],
      exclude: ["**/*.test.ts", "**/*.generated.ts", "**/use*.ts", "**/*Fixtures.ts"],
      reporter: ["text-summary", "json-summary"],
      reportsDirectory: "coverage",
      thresholds: {
        "src/lib/**": { statements: 96, branches: 90, functions: 96, lines: 96 },
        "src/**/_lib/**": { statements: 90, branches: 85, functions: 88, lines: 90 },
      },
    },
  },
});
