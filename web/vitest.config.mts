import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // Next.js resolves this marker itself; tests import server modules directly.
      "server-only": fileURLToPath(new URL("./node_modules/next/dist/compiled/server-only/empty.js", import.meta.url)),
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    // `npm run test:coverage` (CI): the pure logic of the cabinet, src/lib
    // and every route's _lib, keeps these floors. React hooks (use*.ts) run
    // in the browser and are covered by the Playwright suite (e2e/).
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
