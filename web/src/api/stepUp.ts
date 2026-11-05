/**
 * Step-up: a sensitive action (exporting or erasing a contact's data, team
 * changes, connecting a channel, the admin's own actions) answered with
 * the API's "confirm it is you" 401 (lib/stepUpChallenge.ts) waits while
 * the person confirms with a code, then runs once more. The dialog
 * (components/security/StepUpDialog.tsx) listens to this broker; requests
 * refused at the same time share one dialog. Without a dialog on the page,
 * or when the person cancels, the refusal stays the answer.
 */

import type { Middleware } from "openapi-fetch";

import { isStepUpChallenge } from "@/lib/stepUpChallenge";

type Listener = () => void;

interface PendingStepUp {
  promise: Promise<boolean>;
  resolve: (confirmed: boolean) => void;
}

let pending: PendingStepUp | null = null;
const listeners = new Set<Listener>();

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}

/** Ask the person to confirm; true once confirmed, false when cancelled. */
export function requestStepUp(): Promise<boolean> {
  if (pending) {
    return pending.promise;
  }
  if (listeners.size === 0) {
    return Promise.resolve(false);
  }
  let resolve: (confirmed: boolean) => void = () => undefined;
  const promise = new Promise<boolean>((settle) => {
    resolve = settle;
  });
  pending = { promise, resolve };
  notify();
  return promise;
}

/** The dialog's answer: every request waiting on it continues or gives up. */
export function settleStepUp(confirmed: boolean): void {
  const current = pending;
  pending = null;
  notify();
  current?.resolve(confirmed);
}

export function isStepUpPending(): boolean {
  return pending !== null;
}

export function subscribeStepUp(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Copies of the requests on their way, to send again after a confirmation. */
const retries = new Map<string, Request>();

/**
 * openapi-fetch middleware: keeps a copy of each request and, when the API
 * asks to confirm, waits for the dialog and sends the copy again. Register
 * it after the session-expiry redirect so it sees the answer first.
 */
export const stepUpRetry: Middleware = {
  onRequest({ request, id }) {
    retries.set(id, request.clone());
    return undefined;
  },
  async onResponse({ response, id }) {
    const copy = retries.get(id);
    retries.delete(id);
    if (!copy || !isStepUpChallenge(response.status, response.headers)) {
      return undefined;
    }
    if (!(await requestStepUp())) {
      return undefined;
    }
    return fetch(copy);
  },
  onError({ id }) {
    retries.delete(id);
    return undefined;
  },
};
