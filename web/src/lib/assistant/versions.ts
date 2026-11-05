/**
 * Pure helpers of the Assistant section (app/b/[businessId]/assistant):
 * version statuses, what can be done with a version, and its order.
 */

import type { Schema } from "@/api/types";

export type AssistantVersionStatus = Schema<"AssistantVersionStatus">;
export type AssistantVersionSummary = Schema<"AssistantVersionSummary">;
export type AssistantVersionDetails = Schema<"AssistantVersionDetails">;
export type AssistantToolName = Schema<"AssistantToolName">;

export type StatusTone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

export const VERSION_STATUS_TONES: Record<AssistantVersionStatus, StatusTone> = {
  draft: "neutral",
  testing: "info",
  ready: "accent",
  tests_failed: "danger",
  published: "success",
  archived: "neutral",
};

/** What an owner (or a platform admin) can do with a version in its status. */
export interface VersionActions {
  publish: boolean;
  /** Publish a version that did not pass its autotests (platform admins only). */
  forcePublish: boolean;
  runAutotests: boolean;
  rollback: boolean;
}

export function versionActions(
  status: AssistantVersionStatus,
  viewer: { isOwner: boolean; isPlatformAdmin: boolean },
): VersionActions {
  const canChange = viewer.isOwner || viewer.isPlatformAdmin;
  const untested = status === "draft" || status === "tests_failed";
  return {
    publish: canChange && status === "ready",
    forcePublish: viewer.isPlatformAdmin && untested,
    runAutotests: canChange && (untested || status === "ready"),
    rollback: canChange && status === "archived",
  };
}

/** Newest first (the API's order, kept stable for local updates). */
export function sortVersions<T extends Pick<AssistantVersionSummary, "version_number">>(versions: readonly T[]): T[] {
  return [...versions].sort((left, right) => right.version_number - left.version_number);
}

export function liveVersion<T extends Pick<AssistantVersionSummary, "status">>(versions: readonly T[]): T | undefined {
  return versions.find((version) => version.status === "published");
}
