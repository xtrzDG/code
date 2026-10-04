"use client";

/**
 * "Confirm it is you": shown when the API asks a sensitive action to be
 * confirmed (src/api/stepUp.ts). People with an authenticator app enter
 * its code (or a recovery code); others get a login code at their own
 * phone or e-mail. Once confirmed, the waiting requests run again by
 * themselves; cancelling leaves them refused. Mounted once, in the root
 * layout, so every page of the cabinet has it.
 */

import { useEffect, useState, useSyncExternalStore } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import { isStepUpPending, settleStepUp, subscribeStepUp } from "@/api/stepUp";
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
import {
  RECOVERY_CODE_EXAMPLE,
  isCompleteOneTimeCode,
  secondFactorProblem,
} from "@/lib/security/secondFactor";

import { OneTimeCodeField } from "./OneTimeCodeField";

export function StepUpDialog() {
  const open = useSyncExternalStore(
    subscribeStepUp,
    isStepUpPending,
    () => false,
  );
  return open ? <StepUpForm /> : null;
}

function StepUpForm() {
  const { t } = useI18n();
  const toast = useToast();
  const [challenge, setChallenge] = useState<StepUpChallengeView | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [isChecking, setChecking] = useState(false);

  /** Ask how to confirm (and, without an authenticator, send a login code). */
  const ask = () => unwrap(api.POST("/v1/auth/step-up"));

  const resend = async () => {
    try {
      const next = await ask();
      setProblem(null);
      setChallenge(next);
      setCode("");
    } catch (error) {
      toast.error(toApiError(error));
    }
  };

  useEffect(() => {
    let isCurrent = true;
    ask().then(
      (next) => {
        if (isCurrent) {
          setChallenge(next);
        }
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
          <Button
            type="submit"
            form="step-up-form"
            isLoading={isChecking}
            loadingText={t("mfa.stepUp.confirming")}
            disabled={!challenge}
          >
            {t("mfa.stepUp.confirm")}
          </Button>
        </>
      }
    >
      {challenge ? (
        <form
          id="step-up-form"
          noValidate
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            void confirm(code);
          }}
        >
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
