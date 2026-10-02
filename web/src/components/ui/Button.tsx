import Link from "next/link";
import type { ComponentPropsWithRef, ReactNode } from "react";

import { mergeClassOverrides } from "@/lib/classMerge";
import { cn } from "@/lib/cn";

import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "danger-ghost";
export type ButtonSize = "sm" | "md" | "lg";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent-solid text-on-accent hover:bg-accent-solid-hover",
  secondary: "border border-line bg-surface text-ink hover:border-line-strong hover:bg-surface-muted",
  ghost: "text-ink-muted hover:bg-surface-muted hover:text-ink",
  danger: "bg-danger-solid text-white hover:opacity-90",
  /** A quiet destructive action (remove, disconnect) next to others. */
  "danger-ghost": "text-danger hover:bg-danger-soft",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 gap-1.5 rounded-md px-2.5 text-sm",
  md: "h-9 gap-2 rounded-lg px-3.5 text-sm",
  lg: "h-11 gap-2 rounded-lg px-5 text-[0.9375rem]",
};

/**
 * Classes of a button, for elements that only look like one. `className`
 * replaces the variant's own width, height, padding, radius, font size and
 * colours of the same kind (`w-40`, `hover:bg-…`), see `mergeClassOverrides`.
 */
export function buttonClasses(
  options: { variant?: ButtonVariant; size?: ButtonSize; fullWidth?: boolean; className?: string } = {},
): string {
  const { variant = "primary", size = "md", fullWidth = false, className } = options;
  return mergeClassOverrides(
    cn(
      "inline-flex shrink-0 cursor-pointer items-center justify-center font-medium whitespace-nowrap transition-colors select-none",
      "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
      "disabled:pointer-events-none disabled:opacity-50 aria-disabled:pointer-events-none aria-disabled:opacity-50",
      VARIANTS[variant],
      SIZES[size],
      fullWidth && "w-full",
    ),
    className,
  );
}

export interface ButtonProps extends ComponentPropsWithRef<"button"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  /** Shows a spinner, disables the button and announces `loadingText`. */
  isLoading?: boolean;
  loadingText?: string;
  leadingIcon?: ReactNode;
}

export function Button({
  variant,
  size,
  fullWidth,
  isLoading = false,
  loadingText,
  leadingIcon,
  className,
  children,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={buttonClasses({ variant, size, fullWidth, className })}
      {...props}
    >
      {isLoading ? <Spinner size="sm" /> : leadingIcon}
      <span>{isLoading && loadingText ? loadingText : children}</span>
    </button>
  );
}

export interface ButtonLinkProps extends ComponentPropsWithRef<typeof Link> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  leadingIcon?: ReactNode;
}

/** A link styled as a button (navigation, not actions). */
export function ButtonLink({
  variant,
  size,
  fullWidth,
  leadingIcon,
  className,
  children,
  ...props
}: ButtonLinkProps) {
  return (
    <Link className={buttonClasses({ variant, size, fullWidth, className })} {...props}>
      {leadingIcon}
      <span>{children}</span>
    </Link>
  );
}
