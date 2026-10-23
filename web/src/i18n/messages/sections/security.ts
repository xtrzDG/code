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
import { adminAuditDe } from "./security/adminAudit.de";
import { adminAuditEn } from "./security/adminAudit.en";
import { adminAuditHe } from "./security/adminAudit.he";
import { adminAuditKa } from "./security/adminAudit.ka";
import { adminAuditRu } from "./security/adminAudit.ru";
import { auditChainDe } from "./security/auditChain.de";
import { auditChainEn } from "./security/auditChain.en";
import { auditChainHe } from "./security/auditChain.he";
import { auditChainKa } from "./security/auditChain.ka";
import { auditChainRu } from "./security/auditChain.ru";
import { devicesEn } from "./security/devices.en";
import { devicesKa } from "./security/devices.ka";
import { devicesRu } from "./security/devices.ru";
import { legalConsentEn } from "./security/legalConsent.en";
import { legalConsentKa } from "./security/legalConsent.ka";
import { legalConsentRu } from "./security/legalConsent.ru";
import { mfaEn } from "./security/mfa.en";
import { mfaKa } from "./security/mfa.ka";
import { mfaRu } from "./security/mfa.ru";
import { securityEn } from "./security/security.en";
import { securityKa } from "./security/security.ka";
import { securityRu } from "./security/security.ru";
import { supportAccessEn } from "./security/supportAccess.en";
import { supportAccessKa } from "./security/supportAccess.ka";
import { supportAccessRu } from "./security/supportAccess.ru";
import { devicesHe } from "./security/devices.he";
import { devicesDe } from "./security/devices.de";
import { legalConsentHe } from "./security/legalConsent.he";
import { legalConsentDe } from "./security/legalConsent.de";
import { mfaHe } from "./security/mfa.he";
import { mfaDe } from "./security/mfa.de";
import { securityHe } from "./security/security.he";
import { securityDe } from "./security/security.de";
import { supportAccessHe } from "./security/supportAccess.he";
import { supportAccessDe } from "./security/supportAccess.de";
import { passkeysEn } from "./security/passkeys.en";
import { passkeysRu } from "./security/passkeys.ru";
import { passkeysKa } from "./security/passkeys.ka";
import { passkeysHe } from "./security/passkeys.he";
import { passkeysDe } from "./security/passkeys.de";
import { securityNudgeEn } from "./security/securityNudge.en";
import { securityNudgeRu } from "./security/securityNudge.ru";
import { securityNudgeKa } from "./security/securityNudge.ka";
import { securityNudgeHe } from "./security/securityNudge.he";
import { securityNudgeDe } from "./security/securityNudge.de";

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

export const securityFlowRu: Translation<typeof securityFlowEn> = {
  mfa: mfaRu,
  security: securityRu,
  devices: devicesRu,
  supportAccess: supportAccessRu,
  legalConsent: legalConsentRu,
  auditChain: auditChainRu,
  adminAudit: adminAuditRu,
  passkeys: passkeysRu,
  securityNudge: securityNudgeRu,
};

export const securityFlowKa: Translation<typeof securityFlowEn> = {
  mfa: mfaKa,
  security: securityKa,
  devices: devicesKa,
  supportAccess: supportAccessKa,
  legalConsent: legalConsentKa,
  auditChain: auditChainKa,
  adminAudit: adminAuditKa,
  passkeys: passkeysKa,
  securityNudge: securityNudgeKa,
};

export const securityFlowHe: Translation<typeof securityFlowEn> = {
  mfa: mfaHe,
  security: securityHe,
  devices: devicesHe,
  supportAccess: supportAccessHe,
  legalConsent: legalConsentHe,
  auditChain: auditChainHe,
  adminAudit: adminAuditHe,
  passkeys: passkeysHe,
  securityNudge: securityNudgeHe,
};

export const securityFlowDe: Translation<typeof securityFlowEn> = {
  mfa: mfaDe,
  security: securityDe,
  devices: devicesDe,
  supportAccess: supportAccessDe,
  legalConsent: legalConsentDe,
  auditChain: auditChainDe,
  adminAudit: adminAuditDe,
  passkeys: passkeysDe,
  securityNudge: securityNudgeDe,
};
