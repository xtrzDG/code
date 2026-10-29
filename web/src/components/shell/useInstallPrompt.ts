"use client";

import { useCallback, useSyncExternalStore } from "react";

import { installModeOf, type InstallMode } from "@/lib/installPrompt";

/** Chrome's install prompt event (not in TypeScript's DOM types yet). */
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

let deferredPrompt: BeforeInstallPromptEvent | null = null;
let installedNow = false;
const listeners = new Set<() => void>();

function notify(): void {
  listeners.forEach((listener) => listener());
}

// The browser offers its prompt once, early: catch it as soon as the
// cabinet's code runs, before any menu that offers "Install" is open.
if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event as BeforeInstallPromptEvent;
    notify();
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt = null;
    installedNow = true;
    notify();
  });
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const standalone = window.matchMedia("(display-mode: standalone)");
  standalone.addEventListener("change", listener);
  return () => {
    listeners.delete(listener);
    standalone.removeEventListener("change", listener);
  };
}

function currentMode(): InstallMode {
  const isIosStandalone = (navigator as Navigator & { standalone?: boolean }).standalone === true;
  return installModeOf({
    isStandalone: installedNow || isIosStandalone || window.matchMedia("(display-mode: standalone)").matches,
    hasPrompt: deferredPrompt !== null,
    userAgent: navigator.userAgent,
    maxTouchPoints: navigator.maxTouchPoints,
  });
}

/**
 * Whether and how "Install the app" can be offered here, and the action
 * that shows the browser's prompt (a no-op without one).
 */
export function useInstallPrompt(): { mode: InstallMode; install: () => Promise<void> } {
  const mode = useSyncExternalStore(subscribe, currentMode, () => "unavailable" as const);
  const install = useCallback(async () => {
    const prompt = deferredPrompt;
    if (!prompt) {
      return;
    }
    await prompt.prompt();
    await prompt.userChoice;
    // A prompt can be shown once; the browser offers a new one if it may.
    deferredPrompt = null;
    notify();
  }, []);
  return { mode, install };
}
