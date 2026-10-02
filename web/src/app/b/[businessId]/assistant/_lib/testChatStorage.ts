/** The test chat's conversation, kept in this browser tab's session storage. */

import { parseStoredTestChat, type StoredTestChat } from "@/lib/assistant/testChat";

function storageKey(businessId: string): string {
  return `aw:test-chat:${businessId}`;
}

export function readStored(businessId: string): StoredTestChat | null {
  try {
    return parseStoredTestChat(window.sessionStorage.getItem(storageKey(businessId)));
  } catch {
    return null;
  }
}

export function writeStored(businessId: string, value: StoredTestChat): void {
  try {
    window.sessionStorage.setItem(storageKey(businessId), JSON.stringify(value));
  } catch {
    // Storage can be unavailable (private mode); the chat still works.
  }
}
