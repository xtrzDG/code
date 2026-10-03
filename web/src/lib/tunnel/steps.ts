/**
 * The "Create an AI assistant" tunnel as data: its eight steps in order,
 * which of them may be skipped, where a reload or a returning owner picks
 * up (from the API's setup progress), and which way a move goes (forward
 * into the tunnel, or back out of it). Pure functions; the screens live in
 * components/setup/.
 *
 * The API's guided setup has seven steps (GET …/setup); the tunnel asks
 * "what" and "where" on two screens, because the country can only be
 * chosen before the business exists.
 */

import type { Schema } from "@/api/types";

export const TUNNEL_STEPS = ["business", "place", "offer", "hours", "people", "channels", "try", "launch"] as const;

export type TunnelStep = (typeof TUNNEL_STEPS)[number];

/** A step, or the finale once the assistant is live. */
export type TunnelPlace = TunnelStep | "done";

export const FINALE = "done" as const;

type SetupView = Schema<"SetupView">;
type SetupStepCode = Schema<"SetupStepCode">;
type SetupStepStatus = Schema<"SetupStepStatus">;

/** The steps whose "Skip for now" the API remembers (PUT …/setup/skipped-steps/{code}). */
export const SKIPPABLE_STEPS: Readonly<Partial<Record<TunnelStep, SetupStepCode>>> = {
  offer: "offer",
  channels: "channels",
  try: "test",
};

/** The two steps answered before the business exists (on /create). */
export const BEFORE_CREATION: ReadonlySet<TunnelStep> = new Set(["business", "place"]);

export function isTunnelPlace(value: string | null | undefined): value is TunnelPlace {
  return value === FINALE || (TUNNEL_STEPS as readonly string[]).includes(value ?? "");
}

export function isSkippable(step: TunnelStep): boolean {
  return SKIPPABLE_STEPS[step] !== undefined;
}

/** 0 for the first step … 7 for the launch, 8 for the finale. */
export function placeIndex(place: TunnelPlace): number {
  return place === FINALE ? TUNNEL_STEPS.length : TUNNEL_STEPS.indexOf(place);
}

/** "Step 3 of 8": the step's number from 1. */
export function stepNumber(step: TunnelStep): number {
  return TUNNEL_STEPS.indexOf(step) + 1;
}

export function nextPlace(step: TunnelStep): TunnelPlace {
  return TUNNEL_STEPS[TUNNEL_STEPS.indexOf(step) + 1] ?? FINALE;
}

export function previousStep(place: TunnelPlace): TunnelStep | null {
  const index = placeIndex(place);
  return index > 0 ? (TUNNEL_STEPS[index - 1] ?? null) : null;
}

/** 1: deeper into the tunnel, -1: back out of it, 0: staying. */
export function direction(from: TunnelPlace, to: TunnelPlace): 1 | -1 | 0 {
  const delta = placeIndex(to) - placeIndex(from);
  return delta > 0 ? 1 : delta < 0 ? -1 : 0;
}

export type RailState = "done" | "skipped" | "todo";

function statusOf(setup: SetupView, code: SetupStepCode): SetupStepStatus | null {
  return setup.steps.find((step) => step.code === code)?.status ?? null;
}

function missingOf(setup: SetupView, code: SetupStepCode): readonly string[] {
  return setup.steps.find((step) => step.code === code)?.missing ?? [];
}

function railStateOf(status: SetupStepStatus | null): RailState {
  return status === "done" ? "done" : status === "skipped" ? "skipped" : "todo";
}

/**
 * How far each tunnel step is, from the API's setup. The API's "business"
 * step also asks for the address, which the tunnel asks on "place": an
 * address alone missing leaves "business" done and "place" to do.
 */
export function stepStates(setup: SetupView): Record<TunnelStep, RailState> {
  const businessMissing = missingOf(setup, "business");
  const businessStatus = statusOf(setup, "business");
  const onlyAddress = businessMissing.length > 0 && businessMissing.every((kind) => kind === "no_address");
  const lacksAddress = businessMissing.includes("no_address");
  return {
    business: onlyAddress ? "done" : railStateOf(businessStatus),
    place: lacksAddress ? railStateOf(businessStatus) : "done",
    offer: railStateOf(statusOf(setup, "offer")),
    hours: railStateOf(statusOf(setup, "hours_and_bookings")),
    people: railStateOf(statusOf(setup, "staff_contact")),
    channels: railStateOf(statusOf(setup, "channels")),
    try: railStateOf(statusOf(setup, "test")),
    launch: setup.is_live ? "done" : "todo",
  };
}

/**
 * Where a returning owner continues: the finale once the assistant is
 * live, else the first step neither done nor skipped (the launch when
 * everything before it is).
 */
export function resumePlace(setup: SetupView): TunnelPlace {
  if (setup.is_live) {
    return FINALE;
  }
  const states = stepStates(setup);
  return TUNNEL_STEPS.find((step) => states[step] === "todo") ?? "launch";
}

/** The profile wizard's steps mapped to the tunnel step that asks the same. */
const PROFILE_STEP_PLACES: Readonly<Record<Schema<"ProfileWizardStep">, TunnelStep>> = {
  niche_and_languages: "business",
  faq_and_handoff: "business",
  channels: "business",
  contacts_and_hours: "hours",
  booking_rules: "hours",
  offer: "offer",
};

/** Where a fix lives: a step of the tunnel, or a cabinet page (billing, the checks under Advanced). */
export type FixPlace = { kind: "step"; step: TunnelStep } | { kind: "billing" } | { kind: "checks" } | { kind: "finale" };

/** The place an API action (a setup step's or a "needs attention" reason's) points to. */
export function fixPlace(action: Schema<"SetupActionView">): FixPlace {
  switch (action.target) {
    case "profile":
      return { kind: "step", step: action.profile_step ? PROFILE_STEP_PLACES[action.profile_step] : "business" };
    case "staff_contacts":
      return { kind: "step", step: "people" };
    case "channels":
      return { kind: "step", step: "channels" };
    case "test_chat":
      return { kind: "step", step: "try" };
    case "agreement":
    case "apply_changes":
      return { kind: "step", step: "launch" };
    case "billing":
      return { kind: "billing" };
    case "checks":
      return { kind: "checks" };
    case "overview":
    case "phone_test":
    case "share":
      return { kind: "finale" };
  }
}

/** The address of a place inside a business's setup (`?step=…`). */
export function placeQuery(place: TunnelPlace): string {
  return `?step=${place}`;
}
