"use client";

/**
 * "Confirm it is you": shown when the API asks a sensitive action to be
 * confirmed (src/api/stepUp.ts). People with an authenticator app enter
 * its code (or a recovery code); people with a passkey may use it instead
 * (with passkeys alone, nothing is sent unless they ask for a code);
 * others get a login code at their own phone or e-mail (one sent moments
 * ago is offered again: stepUpAsker.ts).
 * Once confirmed, the waiting requests run again by themselves; cancelling
 * leaves them refused. Loaded by StepUpDialog only when a confirmation is
 * asked for.
 */

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import { settleStepUp } from "@/api/stepUp";
import type { StepUpChallengeView } from "@/api/types";
import {
  Button,
  Field,
  Input,
  Modal,
  Spinner,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { canUsePasskeys } from "@/lib/security/passkeyCeremony";
import { usePasskeySupport } from "@/lib/security/usePasskeySupport";
import {
  RECOVERY_CODE_EXAMPLE,
  isCompleteOneTimeCode,
  secondFactorProblem,
} from "@/lib/security/secondFactor";
import { createStepUpAsker } from "@/lib/security/stepUpAsker";

import { OneTimeCodeField } from "./OneTimeCodeField";
import { StepUpPasskeyOption } from "./StepUpPasskeyOption";
import { useStepUpPasskey } from "./useStepUpPasskey";

const stepUp = createStepUpAsker(() => unwrap(api.POST("/v1/auth/step-up")));
/** A login code instead of a passkey (asked on purpose: it is sent). */
const loginCodeStepUp = createStepUpAsker(() =>
  unwrap(api.POST("/v1/auth/step-up", { body: { method: "login_code" } })),
);

export default function StepUpForm() {
  const { t } = useI18n();
  const toast = useToast();
  const [challenge, setChallenge] = useState<StepUpChallengeView | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [isChecking, setChecking] = useState(false);
  const passkey = useStepUpPasskey(() => {
    toast.success(t("mfa.stepUp.confirmed"));
    settleStepUp(true);
  });
  const isPasskeySupported = usePasskeySupport();
  const canPasskey = Boolean(challenge?.passkey_available) && isPasskeySupported === true;
  const isPasskeyOnly = challenge?.method === "passkey";

  // A code asked for on purpose (passkeys alone send nothing) is resent the same way.
  const [isCodeOnRequest, setCodeOnRequest] = useState(false);

  const askLoginCode = async (options: { onRequest: boolean; fresh: boolean }) => {
    try {
      const next = await (options.onRequest ? loginCodeStepUp : stepUp).ask({ fresh: options.fresh });
      setCodeOnRequest(options.onRequest);
      setProblem(null);
      setChallenge(next);
      setCode("");
    } catch (error) {
      toast.error(toApiError(error));
    }
  };
  const resend = () => askLoginCode({ onRequest: isCodeOnRequest, fresh: true });

  useEffect(() => {
    let isCurrent = true;
    // How to confirm (without an authenticator or a passkey, a login code is sent).
    stepUp.ask().then(
      (next) => {
        if (!isCurrent) {
          return;
        }
        if (next.method === "passkey" && !canUsePasskeys()) {
          // Passkeys only, and this browser cannot use them: a code instead.
          void askLoginCode({ onRequest: true, fresh: false });
          return;
        }
        setChallenge(next);
      },
      (error: unknown) => {
        toast.error(toApiError(error));
        settleStepUp(false);
      },
    );
    return () => {
      isCurrent = false;
    };
    // Asked once per opening.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const confirm = async (digits: string) => {
    if (!challenge || isChecking) {
      return;
    }
    if (!useRecovery && !isCompleteOneTimeCode(digits)) {
      setProblem(t("mfa.errors.codeFormat"));
      return;
    }
    setChecking(true);
    setProblem(null);
    const body =
      challenge.method === "totp"
        ? useRecovery
          ? { recovery_code: recoveryCode }
          : { code: digits }
        : {
            challenge_id: challenge.login_code?.challenge_id,
            login_code: digits,
          };
    try {
      await unwrap(api.POST("/v1/auth/step-up/verify", { body }));
      stepUp.forget();
      loginCodeStepUp.forget();
      toast.success(t("mfa.stepUp.confirmed"));
      settleStepUp(true);
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
  };

  const instruction =
    challenge?.method === "login_code"
      ? t("mfa.stepUp.loginCode", {
          destination: challenge.login_code?.masked_destination ?? "",
        })
      : useRecovery
        ? t("mfa.secondStep.recoveryDescription")
        : t("mfa.stepUp.totp");

  return (
    <Modal
      open
      onClose={() => settleStepUp(false)}
      size="sm"
      title={t("mfa.stepUp.title")}
      description={t("mfa.stepUp.description")}
      footer={
        <>
          <Button variant="secondary" onClick={() => settleStepUp(false)}>
            {t("common.cancel")}
          </Button>
          {isPasskeyOnly ? (
            <Button
              isLoading={passkey.isWorking}
              loadingText={t("passkeys.signIn.waiting")}
              onClick={() => void passkey.confirm()}
            >
              {t("passkeys.stepUp.use")}
            </Button>
          ) : (
            <Button
              type="submit"
              form="step-up-form"
              isLoading={isChecking}
              loadingText={t("mfa.stepUp.confirming")}
              disabled={!challenge || passkey.isWorking}
            >
              {t("mfa.stepUp.confirm")}
            </Button>
          )}
        </>
      }
    >
      {challenge && isPasskeyOnly ? (
        <StepUpPasskeyOption
          isOnly
          isWorking={passkey.isWorking}
          problem={passkey.problem}
          onConfirm={() => void passkey.confirm()}
          onUseLoginCode={() => void askLoginCode({ onRequest: true, fresh: false })}
        />
      ) : challenge ? (
        <form
          id="step-up-form"
          noValidate
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void confirm(code);
          }}
        >
          {canPasskey ? (
            <StepUpPasskeyOption
              isOnly={false}
              isWorking={passkey.isWorking}
              problem={passkey.problem}
              onConfirm={() => void passkey.confirm()}
              onUseLoginCode={() => void askLoginCode({ onRequest: true, fresh: false })}
            />
          ) : null}
          <p className="text-sm text-ink-muted">{instruction}</p>
          {useRecovery ? (
            <Field
              label={t("mfa.secondStep.recoveryCode")}
              hint={t("mfa.secondStep.recoveryHint", {
                example: RECOVERY_CODE_EXAMPLE,
              })}
              error={problem ?? undefined}
            >
              {(control) => (
                <Input
                  {...control}
                  value={recoveryCode}
                  autoComplete="off"
                  spellCheck={false}
                  autoFocus
                  onChange={(event) => setRecoveryCode(event.target.value)}
                />
              )}
            </Field>
          ) : (
            <OneTimeCodeField
              label={t("mfa.stepUp.code")}
              value={code}
              error={problem ?? undefined}
              onChange={(digits) => {
                setCode(digits);
                setProblem(null);
              }}
              onComplete={(digits) => void confirm(digits)}
              autoFocus
            />
          )}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {challenge.method === "totp" ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setUseRecovery((value) => !value)}
              >
                {useRecovery
                  ? t("mfa.secondStep.useApp")
                  : t("mfa.secondStep.useRecovery")}
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void resend()}
              >
                {t("mfa.stepUp.resend")}
              </Button>
            )}
          </div>
        </form>
      ) : (
        <p
          className="flex items-center gap-2 text-sm text-ink-muted"
          aria-live="polite"
        >
          <Spinner size="sm" /> {t("mfa.stepUp.sending")}
        </p>
      )}
    </Modal>
  );
}
