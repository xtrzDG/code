"use client";

import { Alert, Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { LoginFlow } from "../_lib/useLoginFlow";
import { PhoneFields } from "./PhoneFields";

/** Step one: phone or e-mail, then "Get a code". */
export function DestinationForm({
  flow,
  sessionExpired,
}: {
  flow: LoginFlow;
  sessionExpired: boolean;
}) {
  const { t } = useI18n();
  const { destination } = flow;
  const { method, isUnavailable, error } = destination;

  return (
    <>
      <div className="mb-6 space-y-1.5">
        <h1 className="text-xl font-semibold tracking-tight text-ink">
          {t("auth.title")}
        </h1>
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

      <form noValidate className="space-y-5" onSubmit={flow.submitDestination}>
        <fieldset hidden={!destination.isEmailOffered}>
          <legend className="sr-only">{t("auth.methodLabel")}</legend>
          <div className="grid grid-cols-2 gap-1 rounded-lg border border-line bg-surface-muted p-1">
            {(["phone", "email"] as const).map((option) => (
              <label
                key={option}
                className={cn(
                  "flex h-8 cursor-pointer items-center justify-center rounded-md px-3 text-sm font-medium transition-colors",
                  "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
                  method === option
                    ? "bg-surface text-ink ring-1 ring-line-strong/40"
                    : "text-ink-muted hover:text-ink",
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
                {option === "phone"
                  ? t("auth.methodPhone")
                  : t("auth.methodEmail")}
              </label>
            ))}
          </div>
        </fieldset>

        {method === "phone" ? (
          <PhoneFields destination={destination} />
        ) : (
          <Field label={t("auth.email")} error={error ? t(error) : undefined}>
            {(control) => (
              <Input
                {...control}
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder={t("auth.emailPlaceholder")}
                value={destination.email}
                onChange={(event) => destination.setEmail(event.target.value)}
              />
            )}
          </Field>
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
