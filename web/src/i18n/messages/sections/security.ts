/**
 * Texts of two-factor sign-in: the second step of signing in and the
 * "confirm it is you" dialog (`mfa`), Account → Security and a business's
 * requirement for its team (`security`), the signed-in devices
 * (`devices`), platform support's access to a cabinet (`supportAccess`) and
 * the terms a person accepts by signing in (`legalConsent`), and the
 * audit log's tamper check (`auditChain`) with the platform admin's Audit
 * page (`adminAudit`), passkeys (`passkeys`) and the owner's reminder to
 * turn on a second factor (`securityNudge`).
 *
 * Top-level keys are namespaces, spread into the dictionaries of every
 * locale; the other languages are type-checked against `en`. Each namespace lives in its own
 * file per language under `./security/`.
 */

import type { Translation } from "../../translate";
import { adminAuditIt } from "./security/adminAudit.it";
import { adminAuditEn } from "./security/adminAudit.en";
import { auditChainIt } from "./security/auditChain.it";
import { auditChainEn } from "./security/auditChain.en";
import { devicesEn } from "./security/devices.en";
import { legalConsentEn } from "./security/legalConsent.en";
import { mfaEn } from "./security/mfa.en";
import { securityEn } from "./security/security.en";
import { supportAccessEn } from "./security/supportAccess.en";
import { devicesIt } from "./security/devices.it";
import { legalConsentIt } from "./security/legalConsent.it";
import { mfaIt } from "./security/mfa.it";
import { securityIt } from "./security/security.it";
import { supportAccessIt } from "./security/supportAccess.it";
import { passkeysEn } from "./security/passkeys.en";
import { passkeysIt } from "./security/passkeys.it";
import { securityNudgeEn } from "./security/securityNudge.en";
import { securityNudgeIt } from "./security/securityNudge.it";

export const securityFlowEn = {
  mfa: mfaEn,
  security: securityEn,
  devices: devicesEn,
  supportAccess: supportAccessEn,
  legalConsent: legalConsentEn,
  auditChain: auditChainEn,
  adminAudit: adminAuditEn,
  passkeys: passkeysEn,
  securityNudge: securityNudgeEn,
} as const;

export const securityFlowIt: Translation<typeof securityFlowEn> = {
  mfa: mfaIt,
  security: securityIt,
  devices: devicesIt,
  supportAccess: supportAccessIt,
  legalConsent: legalConsentIt,
  auditChain: auditChainIt,
  adminAudit: adminAuditIt,
  passkeys: passkeysIt,
  securityNudge: securityNudgeIt,
};
