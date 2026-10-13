"use client";

import type { ReactNode } from "react";

import { HOME_PATH } from "@/lib/navigation";

import { LanguageSwitcher } from "../LanguageSwitcher";
import { ThemeSwitcher } from "../theme/ThemeSwitcher";
import { Brand } from "./Brand";
import { ServiceWorker } from "./ServiceWorker";
import { SignOutButton } from "./SignOutButton";

/** The bar's last element: the page is not painted before the browser has read the whole bar. */
const TOP_BAR_END = "top-bar-end";

/**
 * Header of pages outside a business (landing, sign-in, business list):
 * brand, optional actions, the language and theme switches and, when signed
 * in, sign-out.
 */
export function TopBar({ signedIn = false, actions }: { signedIn?: boolean; actions?: ReactNode }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-canvas/85 backdrop-blur-md">
      {/* The browser paints a page while it still reads it: without this a phone painted the bar
          before its last switches, and the bar then grew under the reader (a layout shift). React
          moves the link into the head; Chromium holds the first paint until the bar's end is read. */}
      <link rel="expect" href={`#${TOP_BAR_END}`} blocking="render" />
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
      <template id={TOP_BAR_END} />
    </header>
  );
}
