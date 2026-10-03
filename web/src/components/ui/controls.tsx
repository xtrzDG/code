/**
 * Form controls. Wrap them in <Field> for a label, hint and error:
 *
 *     <Field label={t("businesses.name")} error={errors.name}>
 *       {(control) => <Input {...control} value={name} onChange={...} />}
 *     </Field>
 */

import type { ComponentPropsWithRef, ReactNode } from "react";

import { mergeClassOverrides } from "@/lib/classMerge";
import { cn } from "@/lib/cn";

import { IconChevronDown } from "../icons";

const CONTROL =
  "block rounded-lg border border-line-strong bg-surface text-ink transition-colors " +
  "placeholder:text-ink-subtle hover:border-ink-subtle " +
  "focus:border-focus focus:outline-none focus:ring-3 focus:ring-focus/20 " +
  "disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-ink-subtle " +
  "aria-invalid:border-danger aria-invalid:focus:ring-danger/20";

export type InputProps = ComponentPropsWithRef<"input">;

/** Free text may be in any script: the browser sets its direction from what is typed. */
const FREE_TEXT_TYPES = new Set(["text", "search"]);

/**
 * A text input; it fills its container unless `className` sets a width ("w-32").
 * Free text (names, addresses, answers) follows its own direction, so Arabic
 * or Hebrew typed in an English cabinet reads right to left.
 */
export function Input({ className, type = "text", dir, ...props }: InputProps) {
  return (
    <input
      type={type}
      dir={dir ?? (FREE_TEXT_TYPES.has(type) ? "auto" : undefined)}
      className={mergeClassOverrides(`${CONTROL} w-full h-9 px-3 text-sm`, className)}
      {...props}
    />
  );
}

export type TextareaProps = ComponentPropsWithRef<"textarea">;

export function Textarea({ className, rows = 3, dir = "auto", ...props }: TextareaProps) {
  return (
    <textarea rows={rows} dir={dir} className={mergeClassOverrides(`${CONTROL} w-full px-3 py-2 text-sm`, className)} {...props} />
  );
}

export type SelectProps = ComponentPropsWithRef<"select">;

/** Native select: accessible, type-to-search, works well on phones. */
export function Select({ className, children, ...props }: SelectProps) {
  return (
    <div className={cn("relative", className)}>
      <select className={cn(CONTROL, "h-9 w-full cursor-pointer appearance-none pr-9 pl-3 text-sm")} {...props}>
        {children}
      </select>
      <IconChevronDown
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-subtle"
        aria-hidden
      />
    </div>
  );
}

interface ChoiceProps extends Omit<ComponentPropsWithRef<"input">, "type"> {
  label: ReactNode;
  description?: ReactNode;
}

function Choice({ type, label, description, className, id, ...props }: ChoiceProps & { type: "checkbox" | "radio" }) {
  return (
    <label className={cn("flex cursor-pointer items-start gap-3 text-sm", props.disabled && "cursor-not-allowed opacity-60", className)} htmlFor={id}>
      <input
        id={id}
        type={type}
        className={cn(
          "mt-0.5 size-4 shrink-0 border-line-strong accent-[var(--accent-solid)]",
          type === "checkbox" ? "rounded" : "rounded-full",
        )}
        {...props}
      />
      <span className="min-w-0">
        <span className="text-ink">{label}</span>
        {description ? <span className="mt-0.5 block text-ink-muted">{description}</span> : null}
      </span>
    </label>
  );
}

export function Checkbox(props: ChoiceProps) {
  return <Choice type="checkbox" {...props} />;
}

export function Radio(props: ChoiceProps) {
  return <Choice type="radio" {...props} />;
}
