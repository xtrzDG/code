/** Types of scripts/payment-page-scripts.mjs for its tests (src/test/paymentPageScripts.test.ts). */

export interface PageScript {
  path: string;
  integrity?: string;
  /** The HTTP status of a deployed file that was not served. */
  status?: number;
}

export interface ScriptInventory {
  pages: Record<string, PageScript[]>;
}

export interface ScriptChange {
  route: string;
  path: string;
  kind: "added" | "removed" | "changed" | "unavailable";
  detail: string;
}

export interface BuildManifest {
  polyfillFiles?: string[];
  rootMainFiles?: string[];
}

export interface ClientManifest {
  entryJSFiles?: Record<string, string[]>;
  clientModules?: Record<string, { chunks?: string[] }>;
}

export const PAYMENT_PAGES: readonly string[];

export function routeManifestPaths(route: string): { buildManifest: string; clientManifest: string };

export function parseClientManifest(text: string, route: string): ClientManifest;

export function entryScripts(buildManifest: BuildManifest, clientManifest: ClientManifest): string[];

export function loadedScripts(entries: readonly string[], read: (path: string) => string): string[];

export function parseInventory(raw: unknown): ScriptInventory;

export function differences(expected: ScriptInventory, found: ScriptInventory): ScriptChange[];

export function renderReport(changes: readonly ScriptChange[], source: string): string;
