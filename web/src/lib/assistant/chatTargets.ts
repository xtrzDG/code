/**
 * Who the owner's test chat talks to, in daily words: "What customers get
 * now" (the live version) or "With your changes" (the newest state: the
 * API prepares a draft from the latest edits when the first message has
 * no version). An update opened from Advanced → History is a third choice
 * only then; version numbers stay out of the daily picker.
 */

import type { AssistantVersionSummary } from "./versions";

export type ChatTarget = "live" | "changes" | "history";

export const CHAT_TARGETS: readonly ChatTarget[] = ["live", "changes", "history"];

type VersionRef = Pick<AssistantVersionSummary, "id" | "status" | "version_number">;

export interface ChatChoice {
  target: ChatTarget;
  /** The version the first message names; null lets the API pick the newest state. */
  versionId: string | null;
  /** The update's number, for a choice from History only. */
  versionNumber: number | null;
}

function liveOf<T extends VersionRef>(versions: readonly T[]): T | undefined {
  return versions.find((version) => version.status === "published");
}

/** The picker's choices: what customers get now (once live), with your changes, and the update from History. */
export function chatChoices(versions: readonly VersionRef[], historyVersionId: string | null): ChatChoice[] {
  const live = liveOf(versions);
  const chosen = historyVersionId && historyVersionId !== live?.id ? versions.find((version) => version.id === historyVersionId) : undefined;
  return [
    ...(live ? [{ target: "live" as const, versionId: live.id, versionNumber: null }] : []),
    { target: "changes", versionId: null, versionNumber: null },
    ...(chosen ? [{ target: "history" as const, versionId: chosen.id, versionNumber: chosen.version_number }] : []),
  ];
}

/** The choice a page opened with: `?version=` (the live one, or one from History), else "With your changes". */
export function initialTarget(versions: readonly VersionRef[], requestedVersionId: string | null): ChatTarget {
  if (requestedVersionId && versions.some((version) => version.id === requestedVersionId)) {
    return liveOf(versions)?.id === requestedVersionId ? "live" : "history";
  }
  return "changes";
}

/**
 * The target of a conversation kept from an earlier visit (before targets
 * were stored: the live version's conversation is "live", any other one
 * "changes").
 */
export function storedTarget(versions: readonly VersionRef[], stored: { target?: ChatTarget | null; versionId: string | null }): ChatTarget {
  if (stored.target) {
    return stored.target;
  }
  return stored.versionId !== null && liveOf(versions)?.id === stored.versionId ? "live" : "changes";
}

/** Which choice answered a line: the live version, the update from History, or the owner's changes. */
export function answeredTarget(versions: readonly VersionRef[], versionId: string | null, historyVersionId: string | null): ChatTarget {
  if (versionId !== null && liveOf(versions)?.id === versionId) {
    return "live";
  }
  if (versionId !== null && versionId === historyVersionId) {
    return "history";
  }
  return "changes";
}
