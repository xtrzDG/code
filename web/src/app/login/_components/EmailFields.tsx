"use client";

import { Alert, Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { Destination } from "../_lib/useDestination";

/** The e-mail address and, when codes cannot go by e-mail, the way to the phone form. */
export function EmailFields({ destination, onUsePhone }: { destination: Destination; onUsePhone: () => void }) {
  const { t } = useI18n();
  const { isEmailOffered, isUnavailable, error } = destination;

  return (
    <>
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
      {!isEmailOffered && !isUnavailable ? (
        <Alert tone="warning">
          <p>{t("loginOptions.noEmail")}</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={onUsePhone}>
            {t("loginOptions.usePhone")}
          </Button>
        </Alert>
      ) : null}
    </>
  );
}
