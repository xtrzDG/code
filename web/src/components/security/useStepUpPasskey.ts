"use client";

/**
 * "Confirm it is you" with a passkey: the API's options, the device's
 * signed answer, the API's check. On success a session the passkey raised
 * to two factors gets a fresh token (rotateSession.ts), the step-up is
 * settled and the waiting requests run again; a refusal is told in the
 * form.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { signWithPasskey } from "@/lib/security/passkeyCeremony";
import { passkeyProblem } from "@/lib/security/passkeyProblem";

import { rotateSessionIfRaised } from "./rotateSession";

export function useStepUpPasskey(onConfirmed: () => void) {
  const { t } = useI18n();
  const toast = useToast();
  const [isWorking, setWorking] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const confirm = async () => {
    if (isWorking) {
      return;
    }
    setWorking(true);
    setProblem(null);
    try {
      const started = await unwrap(api.POST("/v1/auth/step-up/passkey"));
      const credential = await signWithPasskey(started.options);
      const assurance = await unwrap(
        api.POST("/v1/auth/step-up/passkey/verify", {
          body: { passkey_challenge_id: started.passkey_challenge_id, credential },
        }),
      );
      await rotateSessionIfRaised(assurance);
      onConfirmed();
    } catch (caught) {
      const error = toApiError(caught);
      const key = passkeyProblem(caught, error);
      if (key) {
        setProblem(t(key));
      } else {
        toast.error(error);
      }
      setWorking(false);
    }
  };

  return { confirm, isWorking, problem };
}
