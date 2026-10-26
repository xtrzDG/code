/** Types of scripts/visual-browser.mjs for its tests (e2e/visual/visualBrowser.test.ts). */

export const VISUAL_BROWSER_IMAGE: string;

export function dockerRunArguments(options: { name: string; nodeModules: string; image?: string }): string[];

export function playwrightArguments(update: boolean, extra: readonly string[]): string[];

export function publishedPort(output: string): number;
