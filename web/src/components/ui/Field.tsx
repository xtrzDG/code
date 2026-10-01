"use client";

import { useId, type ReactNode } from "react";

import { cn } from "@/lib/cn";

/** Props a Field passes to its control for labelling and error announcing. */
export interface FieldControlProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: true;
  required?: boolean;
}

/**
 * A labelled form control with an optional hint and error message.
 *
 *     <Field label="Name" hint="Shown to customers" error={error} required>
 *       {(control) => <Input {...control} value={value} onChange={...} />}
 *     </Field>
 */
export function Field({
  label,
  hint,
  error,
  required = false,
  optionalLabel,
  className,
  children,
}: {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  required?: boolean;
  /** Text after the label for optional fields ("optional"). */
  optionalLabel?: string;
  className?: string;
  children: (control: FieldControlProps) => ReactNode;
}) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={id} className="block text-sm font-medium text-ink">
        {label}
        {required ? (
          <span className="ml-0.5 text-danger" aria-hidden>
            *
          </span>
        ) : null}
        {optionalLabel ? <span className="ml-1.5 font-normal text-ink-subtle">({optionalLabel})</span> : null}
      </label>
      {children({
        id,
        "aria-describedby": describedBy,
        "aria-invalid": error ? true : undefined,
        required: required || undefined,
      })}
      {error ? (
        <p id={errorId} className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {hint ? (
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/** A group of related controls (checkboxes, radios, rows) with a legend. */
export function Fieldset({
  legend,
  hint,
  error,
  className,
  children,
}: {
  legend: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <fieldset
      className={cn("space-y-3", className)}
      aria-describedby={[error ? `${id}-error` : null, hint ? `${id}-hint` : null].filter(Boolean).join(" ") || undefined}
    >
      <legend className="text-sm font-medium text-ink">{legend}</legend>
      {hint ? (
        <p id={`${id}-hint`} className="-mt-2 text-sm text-ink-muted">
          {hint}
        </p>
      ) : null}
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-danger">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
