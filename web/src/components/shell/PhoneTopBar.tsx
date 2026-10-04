"use client";

/**
 * The bar above a page on phones: the mark, the business and where you
 * are, which is also the page's title (its own header steps aside there):
 * a dot beside it says whether the page is live, and an (i) opens what the
 * page is for (PhonePageInfo), and a "?" its help article. The language and theme moved to the account
 * panel ("More"), so the bar stays calm; `action` adds one button at its
 * end (the account, when there is no tab bar), and `ring` the setup
 * guide's progress before it.
 */

import type { ReactNode } from "react";

import { usePageHelp, usePhoneChromeSnapshot } from "@/components/ui";
import { HOME_PATH } from "@/lib/navigation";

import { Brand } from "./Brand";
import { LiveDot, PageInfoButton } from "./PhonePageInfo";

export function PhoneTopBar({
  title,
  context,
  action,
  ring,
}: {
  title?: string;
  context?: string;
  action?: ReactNode;
  /** The setup guide's progress ring, before the action. */
  ring?: ReactNode;
}) {
  const { live } = usePhoneChromeSnapshot();
  const help = usePageHelp();
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas/85 pt-[env(safe-area-inset-top)] backdrop-blur-xl lg:hidden">
      <div className="flex h-14 items-center gap-3 px-4">
        <Brand href={HOME_PATH} hideName />
        <div className="min-w-0 flex-1 leading-tight">
          {context ? <p className="truncate text-xs text-ink-subtle">{context}</p> : null}
          {title ? (
            <p className="flex min-w-0 items-center gap-2 text-sm font-semibold text-ink">
              <span className="truncate">{title}</span>
              {live ? <LiveDot live={live} /> : null}
            </p>
          ) : null}
        </div>
        {help}
        <PageInfoButton title={title} />
        {ring}
        {action}
      </div>
    </header>
  );
}
