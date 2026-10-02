"use client";

import type { ReactNode } from "react";

import { HOME_PATH } from "@/lib/navigation";

import { LanguageSwitcher } from "../LanguageSwitcher";
import { ThemeSwitcher } from "../theme/ThemeSwitcher";
import { Brand } from "./Brand";
import { ServiceWorker } from "./ServiceWorker";
import { SignOutButton } from "./SignOutButton";

/**
 * Header of pages outside a business (landing, sign-in, business list):
 * brand, optional actions, the language and theme switches and, when signed
 * in, sign-out.
 */
export function TopBar({ signedIn = false, actions }: { signedIn?: boolean; actions?: ReactNode }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas/85 backdrop-blur-md">
      {signedIn ? <ServiceWorker /> : null}
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-2 px-4 sm:px-6">
        <Brand href={signedIn ? HOME_PATH : "/"} hideNameOnPhones />
        <div className="flex min-w-0 items-center gap-2">
          {actions}
          <LanguageSwitcher compact />
          <ThemeSwitcher />
          {signedIn ? <SignOutButton iconOnlyOnPhones /> : null}
        </div>
      </div>
    </header>
  );
}
