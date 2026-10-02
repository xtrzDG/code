"use client";

import { usePathname } from "next/navigation";

import { useI18n } from "@/i18n/client";
import { HOME_PATH } from "@/lib/navigation";

import { LanguageSwitcher } from "../LanguageSwitcher";
import { IconMenu } from "../icons";
import { ThemeSwitcher } from "../theme/ThemeSwitcher";
import { Brand } from "./Brand";
import { isActiveItem, type ShellNavItem } from "./Sidebar";

/**
 * The bar above every signed-in page: where you are (business and section)
 * on large screens, the menu button and the mark on phones, and on every
 * screen the language and theme switches.
 */
export function ShellTopBar({
  context,
  items,
  isMenuOpen,
  onOpenMenu,
}: {
  /** The business name (or "Platform admin") before the section name. */
  context?: string;
  items: readonly ShellNavItem[];
  isMenuOpen: boolean;
  onOpenMenu: () => void;
}) {
  const { t } = useI18n();
  const pathname = usePathname();
  const active = items.find((item) => isActiveItem(pathname, item.href));

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas/85 backdrop-blur-md">
      <div className="flex h-14 items-center gap-2 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-expanded={isMenuOpen}
          className="-ml-1.5 shrink-0 rounded-lg p-1.5 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink lg:hidden"
          aria-label={t("nav.openMenu")}
        >
          <IconMenu className="size-5" aria-hidden />
        </button>
        <Brand href={HOME_PATH} hideNameOnPhones className="lg:hidden" />
        <p className="hidden min-w-0 items-center gap-2 text-sm lg:flex">
          {context ? (
            <>
              <span className="truncate text-ink-muted">{context}</span>
              {active ? (
                <span className="text-ink-subtle" aria-hidden>
                  /
                </span>
              ) : null}
            </>
          ) : null}
          {active ? <span className="truncate font-medium text-ink">{active.label}</span> : null}
        </p>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <LanguageSwitcher compact />
          <ThemeSwitcher />
        </div>
      </div>
    </header>
  );
}
