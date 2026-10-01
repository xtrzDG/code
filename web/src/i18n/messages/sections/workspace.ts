/**
 * Texts of the cabinet sections: Channels, billing, settings and the platform admin.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts and ka.ts, so they must not clash with the
 * namespaces of the other dictionaries. `ru` and `ka` are type-checked
 * against `en`.
 */

import type { Translation } from "../../translate";

export const workspaceEn = {} as const;

export const workspaceRu: Translation<typeof workspaceEn> = {};

export const workspaceKa: Translation<typeof workspaceEn> = {};
