"use client";

/**
 * The second step of signing in: an authenticator code or a recovery code
 * for people who have an app, and, for a platform admin without one,
 * setting it up first (then saving the recovery codes). A session opens
 * only here; `next` then loads in full.
 */

import { useState } from "react";

import {
  startSignInEnrollment,
  verifySecondStep,
  type SecondStepRequired,
} from "@/api/auth";
import { toApiError } from "@/api/errors";
import type { TotpEnrollmentView } from "@/api/types";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  isCompleteOneTimeCode,
  secondFactorProblem,
} from "@/lib/security/secondFactor";

export function useSecondStep(step: SecondStepRequired, next: string) {
  const { t } = useI18n();
  const toast = useToast();
  const challengeId = step.mfa_challenge.mfa_challenge_id;
  const [useRecovery, setUseRecovery] = useState(false);
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [isChecking, setChecking] = useState(false);
  const [isStartingSetup, setStartingSetup] = useState(false);
  const [enrollment, setEnrollment] = useState<TotpEnrollmentView | null>(null);
  const [newCodes, setNewCodes] = useState<string[] | null>(null);

  const finish = () => window.location.assign(next);

  async function check(body: { code?: string; recovery_code?: string }) {
    setChecking(true);
    setProblem(null);
    try {
      const session = await verifySecondStep({
        mfa_challenge_id: challengeId,
        ...body,
      });
      if (session.recovery_codes.length > 0) {
        // A new authenticator: its recovery codes are shown once before going on.
        setNewCodes(session.recovery_codes);
        setChecking(false);
        return;
      }
      finish();
    } catch (caught) {
      const error = toApiError(caught);
      const key = secondFactorProblem(error);
      if (key) {
        setProblem(t(key));
      } else {
        toast.error(error);
      }
      setChecking(false);
    }
  }

  async function submit(candidate: string = code) {
    if (isChecking) {
      return;
    }
    if (useRecovery) {
      await check({ recovery_code: recoveryCode });
      return;
    }
    if (!isCompleteOneTimeCode(candidate)) {
      setProblem(t("mfa.errors.codeFormat"));
      return;
    }
    await check({ code: candidate });
  }

  async function startSetup() {
    setStartingSetup(true);
    try {
      setEnrollment(await startSignInEnrollment(challengeId));
    } catch (caught) {
      const error = toApiError(caught);
      const key = secondFactorProblem(error);
      if (key) {
        setProblem(t(key));
      } else {
        toast.error(error);
      }
    } finally {
      setStartingSetup(false);
    }
  }

  return {
    requiresEnrollment: step.mfa_challenge.requires_enrollment,
    useRecovery,
    toggleRecovery: () => {
      setUseRecovery((value) => !value);
      setProblem(null);
    },
    code,
    typeCode: (digits: string) => {
      setCode(digits);
      setProblem(null);
    },
    recoveryCode,
    setRecoveryCode,
    problem,
    isChecking,
    submit,
    confirmSetup: (digits: string) => void check({ code: digits }),
    enrollment,
    isStartingSetup,
    startSetup,
    newCodes,
    finish,
  };
}
