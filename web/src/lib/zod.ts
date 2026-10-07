/**
 * Zod for the cabinet, without its JIT. Zod compiles object schemas with
 * `new Function` when it may, and the pages' Content Security Policy has
 * no 'unsafe-eval' (src/server/contentSecurityPolicy.ts): even zod's probe
 * for it is reported as a policy violation. Import `z` from here, never
 * from "zod" (ESLint enforces it).
 */

// eslint-disable-next-line no-restricted-imports -- the one place that imports zod itself
import { z } from "zod";

z.config({ jitless: true });

export { z };
