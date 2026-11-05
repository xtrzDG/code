/**
 * How the cabinet can be installed as an app on this device: by the
 * browser's own prompt (Chrome, Edge, Samsung Internet: the
 * `beforeinstallprompt` event), by hand on iPhone and iPad (Safari's Share →
 * Add to Home Screen; Safari has no prompt), or not at all (already
 * installed, or a browser that cannot).
 */

export type InstallMode = "prompt" | "ios" | "installed" | "unavailable";

export interface InstallEnvironment {
  /** The page runs as an installed app (display-mode: standalone, or iOS's navigator.standalone). */
  isStandalone: boolean;
  /** The browser offered its install prompt and it is still unused. */
  hasPrompt: boolean;
  userAgent: string;
  maxTouchPoints: number;
}

/** iPhone, iPod and iPad (an iPad says "Macintosh" but has a touch screen). */
export function isAppleMobile(userAgent: string, maxTouchPoints: number): boolean {
  return /iPhone|iPad|iPod/.test(userAgent) || (/Macintosh/.test(userAgent) && maxTouchPoints > 1);
}

export function installModeOf(environment: InstallEnvironment): InstallMode {
  if (environment.isStandalone) {
    return "installed";
  }
  if (environment.hasPrompt) {
    return "prompt";
  }
  return isAppleMobile(environment.userAgent, environment.maxTouchPoints) ? "ios" : "unavailable";
}
