"use client";

/**
 * The passkey half of the sign-in's second step: answering it with a
 * passkey (offered first when the person has one), and, for a platform
 * admin without a second factor, adding a passkey right there. A session
 * opens on success; a first passkey's recovery codes come back once.
 */

import { useState } from "react";

import type { SecondStepRequired, SignedInSession } from "@/api/auth";
import { toApiError } from "@/api/errors";
import {
  finishPasskeyEnrollment,
  finishPasskeySignIn,
  startPasskeyEnrollment,
  startPasskeySignIn,
} from "@/api/passkeyAuth";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { canUsePasskeys, createPasskey, signWithPasskey } from "@/lib/security/passkeyCeremony";
import { passkeyProblem } from "@/lib/security/passkeyProblem";

export function usePasskeyStep(
  step: SecondStepRequired,
  onSignedIn: (session: SignedInSession) => void,
) {
  const { t } = useI18n();
  const toast = useToast();
  const challengeId = step.mfa_challenge.mfa_challenge_id;
  const methods = step.mfa_challenge.methods ?? [];
  const enrollmentMethods = step.mfa_challenge.enrollment_methods ?? [];
  const isSupported = canUsePasskeys();
  const [isWorking, setWorking] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function run(action: () => Promise<SignedInSession>) {
    setWorking(true);
    setProblem(null);
    try {
      onSignedIn(await action());
    } catch (caught) {
      const key = passkeyProblem(caught, toApiError(caught));
      if (key) {
        setProblem(t(key));
      } else {
        toast.error(toApiError(caught));
      }
      setWorking(false);
    }
  }

  const signIn = () =>
    run(async () => {
      const started = await startPasskeySignIn(challengeId);
      const credential = await signWithPasskey(started.options);
      return finishPasskeySignIn({
        mfa_challenge_id: challengeId,
        passkey_challenge_id: started.passkey_challenge_id,
        credential,
      });
    });

  const enroll = () =>
    run(async () => {
      const started = await startPasskeyEnrollment(challengeId);
      const credential = await createPasskey(started.options);
      return finishPasskeyEnrollment({
        mfa_challenge_id: challengeId,
        passkey_challenge_id: started.passkey_challenge_id,
        credential,
      });
    });

  return {
    /** The person has a passkey and this browser can use it: offered first. */
    canSignIn: isSupported && methods.includes("passkey"),
    /** A platform admin may add a passkey as the first second factor. */
    canEnroll: isSupported && enrollmentMethods.includes("passkey"),
    /** The person also has a code (authenticator app or recovery codes). */
    hasCodes: methods.some((method) => method !== "passkey"),
    isWorking,
    problem,
    signIn: () => void signIn(),
    enroll: () => void enroll(),
  };
}
