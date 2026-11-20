"use client";

import { useEffect, useLayoutEffect, useRef } from "react";

import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { LoginMethod } from "@/lib/countries";

import type { LoginFlow } from "../_lib/useLoginFlow";
import { EmailFields } from "./EmailFields";
import { PhoneFields } from "./PhoneFields";

/** Focus on the form's phone or e-mail field. */
function focusFieldOf(form: HTMLFormElement | null): void {
  form?.querySelector<HTMLInputElement>('input[type="tel"], input[type="email"]')?.focus();
}

/**
 * Step one: phone or e-mail, then "Get a code". The form names the method
 * it shows (`data-login-method`): scripts/smoke.sh reads it from the page's
 * first HTML of a deployment.
 */
export function DestinationForm({ flow, sessionExpired }: { flow: LoginFlow; sessionExpired: boolean }) {
  const { t } = useI18n();
  const { destination } = flow;
  const { method, isUnavailable } = destination;
  const formRef = useRef<HTMLFormElement>(null);
  const switchRef = useRef<HTMLFieldSetElement>(null);
  const focusAfterSwitch = useRef(false);
  // The switch goes when e-mail cannot deliver codes, but never from under a visitor who is on the e-mail form.
  const isSwitchHidden = !destination.isEmailOffered && method !== "email";

  // A notice's button leaves the page with its form: focus goes on to the
  // field of the form that took its place.
  useEffect(() => {
    if (focusAfterSwitch.current) {
      focusAfterSwitch.current = false;
      focusFieldOf(formRef.current);
    }
  }, [method]);

  // When the switch goes (the visitor chose phone, or an answer said that
  // e-mail cannot deliver), focus inside it goes on to the field. A layout
  // effect runs before the browser's next style update, which would drop
  // that focus to the page. A switch that stays keeps its focus.
  useLayoutEffect(() => {
    if (isSwitchHidden && switchRef.current?.contains(document.activeElement)) {
      focusFieldOf(formRef.current);
    }
  }, [isSwitchHidden]);

  function switchToField(other: LoginMethod) {
    focusAfterSwitch.current = other !== method;
    destination.setMethod(other);
  }

  return (
    <>
      <div className="mb-6 space-y-1.5">
        <h1 className="text-xl font-display tracking-tight text-ink">{t("auth.title")}</h1>
        <p className="text-sm text-ink-muted">{t("auth.subtitle")}</p>
      </div>

      {sessionExpired ? (
        <Alert tone="info" className="mb-5">
          {t("auth.sessionExpired")}
        </Alert>
      ) : null}

      {isUnavailable ? (
        <Alert tone="warning" className="mb-5">
          {t("loginOptions.nothingAvailable")}
        </Alert>
      ) : null}

      <form
        ref={formRef}
        noValidate
        className="space-y-5"
        data-login-method={method}
        onSubmit={flow.submitDestination}
      >
        <fieldset ref={switchRef} hidden={isSwitchHidden}>
          <legend className="sr-only">{t("auth.methodLabel")}</legend>
          <div className="grid grid-cols-2 gap-1 rounded-lg border border-line bg-surface-muted p-1">
            {(["phone", "email"] as const).map((option) => (
              <label
                key={option}
                className={cn(
                  "flex h-8 cursor-pointer items-center justify-center rounded-md px-3 text-sm font-medium transition-colors",
                  "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
                  method === option ? "bg-surface text-ink ring-1 ring-line-strong/40" : "text-ink-muted hover:text-ink",
                )}
              >
                <input
                  type="radio"
                  name="method"
                  value={option}
                  checked={method === option}
                  onChange={() => destination.setMethod(option)}
                  className="sr-only"
                />
                {option === "phone" ? t("auth.methodPhone") : t("auth.methodEmail")}
              </label>
            ))}
          </div>
        </fieldset>

        {method === "phone" ? (
          <PhoneFields destination={destination} onUseEmail={() => switchToField("email")} />
        ) : (
          <EmailFields destination={destination} onUsePhone={() => switchToField("phone")} />
        )}

        <Button
          type="submit"
          fullWidth
          size="lg"
          isLoading={flow.isSending}
          loadingText={t("auth.sendingCode")}
          disabled={!destination.canSend}
        >
          {t("auth.sendCode")}
        </Button>
      </form>
    </>
  );
}
