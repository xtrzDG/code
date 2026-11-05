/**
 * The key ring and its re-encryption runs (GET and POST
 * /v1/admin/security/encryption-keys): what the latest run means for the
 * platform admin. Pure functions, so the page and the tests share them.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type EncryptionKeys = Schema<"EncryptionKeysView">;
export type KeyRotation = Schema<"KeyRotationView">;
export type KeyRotationStatus = KeyRotation["status"];

/** While a run is queued or running and no live event says so, look again this often. */
export const KEY_ROTATION_POLL_MS = 3_000;

export const ROTATION_STATUS_TONES: Readonly<Record<KeyRotationStatus, BadgeTone>> = {
  queued: "info",
  running: "info",
  done: "success",
  failed: "danger",
};

/** A run the worker has yet to finish: the start button waits, the page polls. */
export function isRotationRunning(rotation: KeyRotation | null | undefined): boolean {
  return rotation?.status === "queued" || rotation?.status === "running";
}

/** One thing the latest run tells the admin, most urgent first. */
export type RotationFinding =
  | { kind: "working" }
  | { kind: "failed"; error: string }
  | { kind: "unreadable"; count: number }
  | { kind: "webhooks"; count: number }
  | { kind: "keysChanged"; then: number; now: number }
  | { kind: "clean"; isSingleKey: boolean };

/**
 * What the latest run means now that the ring holds `keyCount` keys. A run
 * is clean when every token opened and every webhook was registered again,
 * and no key was added since (a ring that shrank after a clean run is the
 * runbook's last step, not a reason to run again).
 */
export function rotationFindings(rotation: KeyRotation, keyCount: number): RotationFinding[] {
  if (isRotationRunning(rotation)) {
    return [{ kind: "working" }];
  }
  if (rotation.status === "failed") {
    return [{ kind: "failed", error: rotation.last_error ?? "" }];
  }

  const findings: RotationFinding[] = [];
  if (rotation.secrets_unreadable > 0) {
    findings.push({ kind: "unreadable", count: rotation.secrets_unreadable });
  }
  if (rotation.webhooks_failed > 0) {
    findings.push({ kind: "webhooks", count: rotation.webhooks_failed });
  }
  if (keyCount > rotation.key_count) {
    findings.push({ kind: "keysChanged", then: rotation.key_count, now: keyCount });
  }
  return findings.length > 0 ? findings : [{ kind: "clean", isSingleKey: keyCount === 1 }];
}

/** The rotation's tone for an Alert: the worst finding decides. */
export function findingTone(finding: RotationFinding): "info" | "success" | "warning" | "danger" {
  switch (finding.kind) {
    case "working":
      return "info";
    case "clean":
      return "success";
    case "failed":
      return "danger";
    default:
      return "warning";
  }
}
