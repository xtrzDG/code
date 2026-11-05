/**
 * What every screen of an existing business's tunnel gets from the flow:
 * the business, what the tunnel read (loaded before any screen shows) and
 * the moves (on, back, to a step, skip). Screens save their own answers,
 * then move.
 */

import type { ProfileWizardView, Schema } from "@/api/types";
import type { TunnelPlace, TunnelStep } from "@/lib/tunnel/steps";

export interface StepContext {
  businessId: string;
  setup: Schema<"SetupView">;
  starters: Schema<"StarterAnswersView">;
  wizard: ProfileWizardView;
  /** After a screen saved something: the rail and the next screens read it again. */
  refresh: () => void;
  /** On to the next place (after saving). */
  next: () => void;
  back: () => void;
  goTo: (place: TunnelPlace) => void;
  /** "Skip for now": remembered by the API for optional steps, then on. */
  skip: (step: TunnelStep) => Promise<void>;
}
