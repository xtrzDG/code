/**
 * The launch at the end of the tunnel, as data: "Apply changes" builds the
 * assistant, tries it on test conversations and switches it on. These
 * helpers turn the API's progress (GET …/assistant/apply) into the three
 * stages the owner watches, the share done, and when to ask again.
 */

import type { Schema } from "@/api/types";

type ApplyChangesView = Schema<"ApplyChangesView">;

export const LAUNCH_STAGES = ["building", "checking", "publishing"] as const;

export type LaunchStage = (typeof LAUNCH_STAGES)[number];

export type StageState = "done" | "active" | "todo" | "stopped";

/** What the owner sees of the launch right now. */
export type LaunchPhase = "idle" | "running" | "live" | "attention";

export function launchPhase(view: ApplyChangesView | null | undefined): LaunchPhase {
  if (!view?.stage) {
    return "idle";
  }
  if (view.stage === "live") {
    return "live";
  }
  if (view.stage === "needs_attention") {
    return "attention";
  }
  return "running";
}

/**
 * Each stage done, under way, still ahead or where it stopped. A stop is
 * shown on the stage that was under way: a build that failed stops
 * "building", failed or stopped checks stop "checking", a refused
 * publication (or a missing agreement or payment) stops "publishing".
 */
export function stageStates(view: ApplyChangesView | null | undefined): Record<LaunchStage, StageState> {
  const stage = view?.stage ?? null;
  if (stage === "live") {
    return { building: "done", checking: "done", publishing: "done" };
  }
  if (stage === "needs_attention") {
    const stoppedAt = stoppedStage(view?.attention ?? []);
    const reached = LAUNCH_STAGES.indexOf(stoppedAt);
    return {
      building: reached > 0 ? "done" : "stopped",
      checking: reached > 1 ? "done" : reached === 1 ? "stopped" : "todo",
      publishing: reached === 2 ? "stopped" : "todo",
    };
  }
  const current = stage === null ? -1 : LAUNCH_STAGES.indexOf(stage);
  return {
    building: stateAt(0, current),
    checking: stateAt(1, current),
    publishing: stateAt(2, current),
  };
}

function stateAt(index: number, current: number): StageState {
  return index < current ? "done" : index === current ? "active" : "todo";
}

function stoppedStage(attention: readonly Schema<"ApplyAttentionView">[]): LaunchStage {
  const codes = new Set(attention.map((reason) => reason.code));
  if (codes.has("build_failed") || codes.has("profile_incomplete") || codes.has("staff_contact_missing")) {
    return "building";
  }
  if (codes.has("checks_failed") || codes.has("checks_stopped")) {
    return "checking";
  }
  return "publishing";
}

/**
 * How much of the launch is behind (0…1): building is the first fifth,
 * the checks the next three fifths (as they run), publishing the rest.
 */
export function launchProgress(view: ApplyChangesView | null | undefined): number {
  switch (view?.stage) {
    case "building":
      return 0.08;
    case "checking": {
      const total = view.checks_total ?? 0;
      const done = Math.min(view.checks_done ?? 0, total);
      return 0.2 + (total > 0 ? (done / total) * 0.6 : 0);
    }
    case "publishing":
      return 0.9;
    case "live":
      return 1;
    default:
      return 0;
  }
}

/** Poll every 1.5 s while the launch runs; nothing to ask otherwise. */
export const LAUNCH_POLL_MS = 1_500;

export function shouldPoll(view: ApplyChangesView | null | undefined): boolean {
  return launchPhase(view) === "running";
}
