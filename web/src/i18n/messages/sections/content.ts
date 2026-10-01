/**
 * Texts of the cabinet sections: Knowledge base and the assistant (test chat, versions, autotests, publishing).
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts and ka.ts, so they must not clash with the
 * namespaces of the other dictionaries. `ru` and `ka` are type-checked
 * against `en`.
 */

import type { Translation } from "../../translate";

export const contentEn = {} as const;

export const contentRu: Translation<typeof contentEn> = {};

export const contentKa: Translation<typeof contentEn> = {};
