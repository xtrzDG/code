/**
 * Answers of the cabinet's API client for component tests. A test file
 * replaces the client first (vi.mock is hoisted above the imports):
 *
 *     vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
 *
 *     answerGet((path) => (path === "/v1/businesses/{business_id}/audit-log" ? ok(page) : pending()));
 */

import { vi } from "vitest";

import { api } from "@/api/client";

interface RequestInit {
  params?: { path?: Record<string, string>; query?: Record<string, string> };
  body?: unknown;
}

type Handler = (path: string, init: RequestInit) => Promise<unknown>;

/** A 200 answer with this body. */
export function ok<T>(data: T): Promise<{ data: T; response: Response }> {
  return Promise.resolve({ data, response: new Response(null, { status: 200 }) });
}

/** A refused request: the API's error body, its status and request id. */
export function failure(status: number, body: unknown, requestId?: string): Promise<{ error: unknown; response: Response }> {
  const headers: Record<string, string> = requestId ? { "x-request-id": requestId } : {};
  return Promise.resolve({ error: body, response: new Response(null, { status, headers }) });
}

/** A request that never answers: the screen stays loading. */
export function pending(): Promise<never> {
  return new Promise<never>(() => undefined);
}

export function answerGet(handler: Handler): void {
  vi.mocked(api.GET).mockImplementation(handler as never);
}

/** The query of the last GET the screen sent. */
export function lastGetQuery(): Record<string, string> {
  const init = vi.mocked(api.GET).mock.calls.at(-1)?.[1] as RequestInit | undefined;
  return init?.params?.query ?? {};
}
