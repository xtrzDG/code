/**
 * A link from the public site into the cabinet ("Sign in", "Create an AI
 * assistant"): a plain anchor, so the browser loads the cabinet page whole.
 * A public page carries only its own texts and no animation code
 * (i18n/publicScope.ts, components/siteMotion), and a client-side
 * navigation would keep that root layout around the cabinet page (the
 * I18nProvider would then have to reload it anyway).
 */

import type { ReactNode } from "react";

import { buttonClasses, type ButtonSize, type ButtonVariant } from "@/components/ui";

export function CabinetButtonLink({
  href,
  variant,
  size,
  fullWidth,
  trailingIcon,
  className,
  children,
}: {
  href: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  trailingIcon?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <a href={href} className={buttonClasses({ variant, size, fullWidth, className })}>
      <span>{children}</span>
      {trailingIcon}
    </a>
  );
}
