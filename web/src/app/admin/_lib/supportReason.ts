/**
 * The reason an admin gives for opening a client's cabinet: the owner sees
 * it in the banner, the audit log keeps it (8 to 300 characters, as the
 * API's `SupportAccessReason`).
 */

export const SUPPORT_REASON_MIN = 8;
export const SUPPORT_REASON_MAX = 300;

/** The reason as sent: no blanks around it. */
export function cleanSupportReason(text: string): string {
  return text.trim();
}

export function isSupportReasonValid(text: string): boolean {
  const reason = cleanSupportReason(text);
  return reason.length >= SUPPORT_REASON_MIN && reason.length <= SUPPORT_REASON_MAX;
}
