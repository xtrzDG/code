/**
 * Texts of two-factor sign-in: the second step of signing in and the
 * "confirm it is you" dialog (`mfa`), Account → Security and a business's
 * requirement for its team (`security`).
 *
 * Top-level keys are namespaces, spread into en.ts, ru.ts and ka.ts; `ru`
 * and `ka` are type-checked against `en`. Each namespace lives in its own
 * file per language under `./security/`.
 */

import type { Translation } from "../../translate";
import { mfaEn } from "./security/mfa.en";
import { mfaKa } from "./security/mfa.ka";
import { mfaRu } from "./security/mfa.ru";
import { securityEn } from "./security/security.en";
import { securityKa } from "./security/security.ka";
import { securityRu } from "./security/security.ru";

export const securityFlowEn = { mfa: mfaEn, security: securityEn } as const;

export const securityFlowRu: Translation<typeof securityFlowEn> = {
  mfa: mfaRu,
  security: securityRu,
};

export const securityFlowKa: Translation<typeof securityFlowEn> = {
  mfa: mfaKa,
  security: securityKa,
};
