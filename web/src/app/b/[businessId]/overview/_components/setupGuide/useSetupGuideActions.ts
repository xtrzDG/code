"use client";

/**
 * What the owner does in the setup guide: skip a step (or bring it back;
 * the second-factor step is put away with the owner's reminder),
 * open the phone check, put the finished guide away. Every change answers
 * with the setup as it stands, which replaces the cached one.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { Schema } from "@/api/types";

type StepCode = Schema<"SetupStepCode">;

export function useSetupGuideActions(businessId: string) {
  const setupKeys = [queryKeys.setup.all(businessId)];
  const path = { business_id: businessId };

  const skipStep = useMutation(
    (step: StepCode, isSkipped: boolean) =>
      isSkipped
        ? api.PUT("/v1/businesses/{business_id}/setup/skipped-steps/{setup_step}", {
            params: { path: { ...path, setup_step: step } },
          })
        : api.DELETE("/v1/businesses/{business_id}/setup/skipped-steps/{setup_step}", {
            params: { path: { ...path, setup_step: step } },
          }),
    { invalidate: setupKeys },
  );
  // Skipping the second-factor step puts the owner's reminder away.
  const putReminderAway = useMutation(
    () => api.PUT("/v1/businesses/{business_id}/security-nudge/dismissal", { params: { path } }),
    { invalidate: [...setupKeys, queryKeys.securityNudge.detail(businessId)] },
  );
  const skip = {
    run: (step: StepCode, isSkipped: boolean) =>
      step === "protect_data" ? putReminderAway.run() : skipStep.run(step, isSkipped),
    isPending: skipStep.isPending || putReminderAway.isPending,
  };
  const startPhoneCheck = useMutation(
    () => api.POST("/v1/businesses/{business_id}/setup/phone-check", { params: { path } }),
    { invalidate: setupKeys, errorToast: false },
  );
  const dismiss = useMutation(
    () => api.PUT("/v1/businesses/{business_id}/setup/guide-dismissal", { params: { path } }),
    { invalidate: setupKeys },
  );
  return { skip, startPhoneCheck, dismiss };
}
