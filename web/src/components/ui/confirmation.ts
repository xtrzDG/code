/** True when the typed text matches the expected one (case and surrounding spaces aside). */
export function isConfirmationTyped(typed: string, expected: string): boolean {
  const target = expected.trim();
  return target !== "" && typed.trim().toLocaleLowerCase() === target.toLocaleLowerCase();
}
