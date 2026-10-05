"use client";

/**
 * "Check now" for one of the owner's checks: one test conversation with
 * what customers get now (POST …/autotest-cases/{id}/check, 30 an hour
 * per business), its outcome kept on the check in "My checks". A check
 * that passed this way is no longer among the changes customers do not
 * get yet, so those are read again.
 */

import { useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import type { OwnerCheckOutcome } from "@/lib/assistant/ownerChecks";
import type { CheckView } from "@/lib/teaching";

type CheckList = { items?: CheckView[]; limit: number };

/** Why "Check now" could not run: nothing is live yet, too many this hour, or another failure. */
export type CheckNowProblem = "notLive" | "limited" | "failed";

export function checkNowProblem(error: Pick<ApiError, "code">): CheckNowProblem {
  if (error.code === "conflict") {
    return "notLive";
  }
  return error.code === "rate_limited" ? "limited" : "failed";
}

export function useCheckNow(checkId: string) {
  const { business } = useBusiness();
  const { locale } = useI18n();
  const [outcome, setOutcome] = useState<OwnerCheckOutcome | null>(null);
  const [problem, setProblem] = useState<CheckNowProblem | null>(null);

  const probe = useMutation(
    () =>
      api.POST("/v1/businesses/{business_id}/autotest-cases/{case_id}/check", {
        params: { path: { business_id: business.id, case_id: checkId }, query: { language: locale } },
      }),
    { errorToast: false, invalidate: [queryKeys.assistant.pendingAll(business.id)] },
  );

  const run = async () => {
    setProblem(null);
    const result = await probe.run();
    if (!result.ok) {
      setProblem(checkNowProblem(result.error));
      return;
    }
    setOutcome(result.data);
    // "My checks" shows the latest "Check now" at once.
    queryCache.update<CheckList>(queryKeys.assistant.checks(business.id), (data) => ({
      ...data,
      items: (data.items ?? []).map((item) => (item.id === checkId ? { ...item, last_probe: result.data } : item)),
    }));
  };

  return { run, isPending: probe.isPending, outcome, problem };
}
