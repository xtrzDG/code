/** How the signed-in person is named in the shell: their name, else how they sign in. */

import type { UserView } from "@/api/types";
import { formatPhone } from "@/lib/phone";

export type UserNames = Pick<UserView, "display_name" | "phone_number" | "email">;

/** How the user signs in: the phone number as people read it ("+995 555 00 00 01"), else the e-mail. */
export function userContact(user: UserNames): string {
  return user.phone_number ? formatPhone(user.phone_number) : user.email || "";
}

/** Name to show for the signed-in user: display name, else phone or e-mail. */
export function userDisplayName(user: UserNames): string {
  return user.display_name || userContact(user);
}

/** Up to two letters of the name ("Nino Beridze" -> "NB"), or the first digit-free character. */
export function userInitials(user: UserNames): string {
  const words = (user.display_name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length > 0) {
    return words
      .slice(0, 2)
      .map((word) => Array.from(word)[0] ?? "")
      .join("")
      .toLocaleUpperCase();
  }
  const fallback = (user.email ?? "").trim();
  return fallback ? (Array.from(fallback)[0] ?? "").toLocaleUpperCase() : "#";
}
