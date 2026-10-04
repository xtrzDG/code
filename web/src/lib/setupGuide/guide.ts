/**
 * The Overview's setup guide as data (GET …/setup → `guide`): which rows
 * it shows and where each one leads, whether the card, the progress ring
 * or nothing is shown, and which milestones still wait for their
 * celebration. Pure functions; the components live in
 * app/b/[businessId]/overview/_components/ and components/shell/.
 */

import type { Schema } from "@/api/types";
import { fixPath } from "@/lib/assistant/applyFixes";
import { businessPath, setupPath } from "@/lib/navigation";
import { fixPlace } from "@/lib/tunnel/steps";

type SetupView = Schema<"SetupView">;
type SetupStepView = Schema<"SetupStepView">;
type StepCode = Schema<"SetupStepCode">;
type Milestone = Schema<"ActivationMilestoneView">;
type MilestoneKind = Schema<"ActivationEventKind">;

/** Where a row's button goes: a page, the tunnel at a step, or the QR code in place. */
export type GuideRowKind = "page" | "tunnel" | "phone";

export interface GuideRow {
  step: SetupStepView;
  kind: GuideRowKind;
  /** Null for the phone check (it opens in the card) and for finished rows. */
  href: string | null;
  /** An optional step not done yet may be skipped (and a skipped one brought back). */
  canSkip: boolean;
  /** A step after the launch, before it: shown for what comes, without a button. */
  isWaiting: boolean;
}

/** The steps after the launch, in order. */
export const AFTER_LAUNCH: readonly StepCode[] = ["phone_test", "second_channel", "share"];

function rowOf(step: SetupStepView, businessId: string, isLive: boolean): GuideRow {
  const isDone = step.status === "done";
  const canSkip = !step.is_required && !isDone;
  const isAfterLaunch = AFTER_LAUNCH.includes(step.code);
  if (isAfterLaunch && !isLive) {
    // Nothing to test or share yet: customers get answers once it is live.
    return { step, kind: "page", href: null, canSkip: false, isWaiting: !isDone };
  }
  if (step.code === "phone_test") {
    return { step, kind: "phone", href: null, canSkip, isWaiting: false };
  }
  if (step.code === "share") {
    const href = isDone ? null : `${businessPath(businessId, "assistant/channels")}#share`;
    return { step, kind: "page", href, canSkip, isWaiting: false };
  }
  if (isAfterLaunch || isLive) {
    return { step, kind: "page", href: isDone ? null : fixPath(businessId, step.action, null), canSkip, isWaiting: false };
  }
  const place = fixPlace(step.action);
  const href = setupPath(businessId, place.kind === "step" ? place.step : undefined);
  return { step, kind: "tunnel", href: isDone ? null : href, canSkip, isWaiting: false };
}

/**
 * The rows of the card. Before the launch: the seven setup steps (each
 * opens the tunnel at its screen), then the three after it, waiting
 * (no button and no "Skip" until the assistant answers customers). Once
 * live: the three after the launch, and a setup step only when the guide
 * needs it again (a required answer that went missing).
 */
export function guideRows(setup: SetupView, businessId: string): GuideRow[] {
  const after = setup.guide.steps_after_launch ?? [];
  if (!setup.is_live) {
    return [...setup.steps, ...after].map((step) => rowOf(step, businessId, false));
  }
  const again = setup.steps.filter((step) => step.code === setup.guide.next_step);
  return [...again, ...after].map((step) => rowOf(step, businessId, true));
}

export type GuideCard = "hidden" | "guide" | "finished";

/**
 * What the Overview shows: the guide while there is something to do, a
 * short "all set" card once it is finished, nothing once the owner put
 * it away. Staff do not set the business up: they see none of it.
 */
export function guideCard(setup: SetupView | undefined, isOwner: boolean): GuideCard {
  if (!setup || !isOwner || setup.guide.is_dismissed) {
    return "hidden";
  }
  return setup.guide.is_complete ? "finished" : "guide";
}

/** The progress ring in the bar: owners, until the guide is finished. */
export function showsRing(setup: SetupView | undefined, isOwner: boolean): boolean {
  return guideCard(setup, isOwner) === "guide";
}

/** The milestones the cabinet celebrates with a toast (going live has the finale). */
export const CELEBRATED: readonly MilestoneKind[] = ["first_conversation", "first_booking", "first_after_hours_booking"];

/** Older than this, a milestone is old news: acknowledged without a toast. */
export const CELEBRATE_WITHIN_MS = 7 * 24 * 60 * 60 * 1000;

export interface Celebrations {
  /** Toasts to show, oldest first. */
  show: Milestone[];
  /** Acknowledged without a toast. */
  quiet: Milestone[];
}

/**
 * The milestones not celebrated yet: recent ones get a toast; old ones (a
 * business that reached them before celebrations existed) and the owner's
 * own test from a phone (no customer) are acknowledged quietly.
 */
export function pendingCelebrations(setup: SetupView | undefined, nowMs: number): Celebrations {
  const pending = (setup?.milestones ?? [])
    .filter((milestone) => CELEBRATED.includes(milestone.kind) && milestone.celebrated_at == null)
    .sort((left, right) => left.occurred_at - right.occurred_at);
  const testedAt = setup?.guide.phone_tested_at ?? null;
  const show: Milestone[] = [];
  const quiet: Milestone[] = [];
  for (const milestone of pending) {
    const isOld = nowMs - milestone.occurred_at / 1000 > CELEBRATE_WITHIN_MS;
    const isOwnersTest = milestone.kind === "first_conversation" && milestone.occurred_at === testedAt;
    (isOld || isOwnersTest ? quiet : show).push(milestone);
  }
  return { show, quiet };
}

/** The wins the card lists once live: what was reached, newest last. */
export function reachedWins(setup: SetupView): Milestone[] {
  return (setup.milestones ?? [])
    .filter((milestone) => CELEBRATED.includes(milestone.kind))
    .sort((left, right) => left.occurred_at - right.occurred_at);
}
