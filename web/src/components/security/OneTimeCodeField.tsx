"use client";

/**
 * The 6-digit code of an authenticator app (or a login code): digits from
 * any keyboard, filled in by the phone's one-time-code suggestion, and
 * submitted as soon as the sixth digit is typed.
 */

import type { Ref } from "react";

import { Field, Input } from "@/components/ui";
import {
  ONE_TIME_CODE_LENGTH,
  oneTimeCodeDigits,
} from "@/lib/security/secondFactor";

export function OneTimeCodeField({
  label,
  hint,
  error,
  value,
  onChange,
  onComplete,
  inputRef,
  disabled = false,
  autoFocus = false,
}: {
  label: string;
  hint?: string;
  error?: string;
  value: string;
  onChange: (digits: string) => void;
  /** Called with the six digits once complete (not while a check runs). */
  onComplete?: (digits: string) => void;
  inputRef?: Ref<HTMLInputElement>;
  disabled?: boolean;
  /** Focus it when it appears (a step whose only job is this code). */
  autoFocus?: boolean;
}) {
  return (
    <Field label={label} hint={hint} error={error}>
      {(control) => (
        <Input
          {...control}
          ref={inputRef}
          value={value}
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="\d{6}"
          maxLength={ONE_TIME_CODE_LENGTH}
          disabled={disabled}
          autoFocus={autoFocus}
          className="h-12 text-center font-mono text-2xl tracking-[0.5em]"
          onChange={(event) => {
            const digits = oneTimeCodeDigits(event.target.value);
            onChange(digits);
            if (digits.length === ONE_TIME_CODE_LENGTH) {
              onComplete?.(digits);
            }
          }}
        />
      )}
    </Field>
  );
}
