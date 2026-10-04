/**
 * Asking the API how the person confirms a sensitive action (step-up).
 * Without an authenticator app, each ask sends a login code, and an
 * address gets a code at most every 30 seconds: so one ask is shared by
 * everyone waiting on it, and a code sent moments ago is offered again
 * (until shortly before it expires) instead of sending another. "Send a
 * new code" asks afresh; a used code is forgotten.
 */

import type { StepUpChallengeView } from "@/api/types";

/** A reused code keeps this much of its life, so it is not typed as it expires. */
const REUSE_MARGIN_MS = 30_000;

export interface StepUpAsker {
  ask: (options?: { fresh?: boolean }) => Promise<StepUpChallengeView>;
  /** The login code was used (or refused for good): the next ask sends a new one. */
  forget: () => void;
}

export function createStepUpAsker(
  request: () => Promise<StepUpChallengeView>,
  now: () => number = Date.now,
): StepUpAsker {
  let inFlight: Promise<StepUpChallengeView> | null = null;
  let reusable: { view: StepUpChallengeView; until: number } | null = null;

  return {
    ask({ fresh = false } = {}) {
      if (!fresh && reusable && now() < reusable.until) {
        return Promise.resolve(reusable.view);
      }
      if (inFlight) {
        return inFlight;
      }
      const asking = request().then((view) => {
        reusable = view.login_code
          ? { view, until: now() + view.login_code.expires_in_seconds * 1_000 - REUSE_MARGIN_MS }
          : null;
        return view;
      });
      inFlight = asking;
      const clear = () => {
        if (inFlight === asking) {
          inFlight = null;
        }
      };
      asking.then(clear, clear);
      return asking;
    },
    forget() {
      reusable = null;
    },
  };
}
