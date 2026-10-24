"use client";

/**
 * A phone number of the profile (for customers, for calls that need a
 * person), typed in any national or international format; the API checks
 * it and says why when it is not a number it can call.
 */

import { describeError, type ApiError } from "@/api/errors";
import { Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export function PhoneField({
  label,
  hint,
  value,
  onChange,
  error,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  error: ApiError | null;
}) {
  const { t } = useI18n();
  return (
    <Field label={label} hint={hint} optionalLabel={t("common.optional")} error={error ? describeError(error, t).title : undefined}>
      {(control) => (
        <Input
          {...control}
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          dir="ltr"
          maxLength={40}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </Field>
  );
}
