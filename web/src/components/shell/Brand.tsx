"use client";

import Link from "next/link";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconSparkles } from "../icons";

/** The product mark and name, linking home (businesses when signed in, the landing page otherwise). */
export function Brand({
  href,
  hideNameOnPhones = false,
  className,
}: {
  href: string;
  /** Only the mark below `sm`, to leave room for the switches in a phone's top bar. */
  hideNameOnPhones?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  return (
    <Link href={href} className={cn("flex min-w-0 items-center gap-2.5 rounded-md", className)}>
      <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent-solid text-on-accent" aria-hidden>
        <IconSparkles className="size-4" />
      </span>
      <span className={cn("truncate text-sm font-semibold tracking-tight text-ink", hideNameOnPhones && "sr-only sm:not-sr-only")}>
        {t("common.appName")}
      </span>
    </Link>
  );
}
