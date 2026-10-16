"use client";

/**
 * The "?" beside a page's title: opens the page's article in the drawer
 * (HelpProvider), or its help center page where there is no drawer.
 */

import Link from "next/link";

import { IconHelp } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { helpArticlePath } from "@/lib/help/helpTopics";

import { useHelpDrawer } from "./HelpProvider";

const BUTTON =
  "motion-press inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-subtle hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus pointer-coarse:size-11";

export function HelpLink({ slug, className }: { slug: string; className?: string }) {
  const { t } = useI18n();
  const drawer = useHelpDrawer();
  const label = t("helpCenter.pageHelp");

  if (!drawer) {
    return (
      <Link href={helpArticlePath(slug)} aria-label={label} title={label} className={cn(BUTTON, className)}>
        <IconHelp className="size-5" aria-hidden />
      </Link>
    );
  }
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      aria-haspopup="dialog"
      onClick={() => drawer.open(slug)}
      className={cn(BUTTON, className)}
      data-help-slug={slug}
    >
      <IconHelp className="size-5" aria-hidden />
    </button>
  );
}
