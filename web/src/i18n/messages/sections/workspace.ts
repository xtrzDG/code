/**
 * Texts of the cabinet sections: Channels, billing, settings and the platform admin.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts and ka.ts, so they must not clash with the
 * namespaces of the other dictionaries. `ru` and `ka` are type-checked
 * against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./workspace/`; this file composes them.
 */

import type { Translation } from "../../translate";
import { adminEn } from "./workspace/admin.en";
import { adminKa } from "./workspace/admin.ka";
import { adminRu } from "./workspace/admin.ru";
import { billingEn } from "./workspace/billing.en";
import { billingKa } from "./workspace/billing.ka";
import { billingRu } from "./workspace/billing.ru";
import { channelsEn } from "./workspace/channels.en";
import { channelsKa } from "./workspace/channels.ka";
import { channelsRu } from "./workspace/channels.ru";
import { workspaceCommonEn } from "./workspace/common.en";
import { workspaceCommonKa } from "./workspace/common.ka";
import { workspaceCommonRu } from "./workspace/common.ru";
import { loginOptionsEn } from "./workspace/loginOptions.en";
import { loginOptionsKa } from "./workspace/loginOptions.ka";
import { loginOptionsRu } from "./workspace/loginOptions.ru";
import { notificationsEn } from "./workspace/notifications.en";
import { notificationsKa } from "./workspace/notifications.ka";
import { notificationsRu } from "./workspace/notifications.ru";
import { settingsEn } from "./workspace/settings.en";
import { settingsKa } from "./workspace/settings.ka";
import { settingsRu } from "./workspace/settings.ru";
import { settingsRecordsEn } from "./workspace/settingsRecords.en";
import { settingsRecordsKa } from "./workspace/settingsRecords.ka";
import { settingsRecordsRu } from "./workspace/settingsRecords.ru";

export const workspaceEn = {
  workspace: workspaceCommonEn,
  channels: channelsEn,
  loginOptions: loginOptionsEn,
  billing: billingEn,
  settings: { ...settingsEn, ...settingsRecordsEn },
  notifications: notificationsEn,
  admin: adminEn,
} as const;

export const workspaceRu: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonRu,
  channels: channelsRu,
  loginOptions: loginOptionsRu,
  billing: billingRu,
  settings: { ...settingsRu, ...settingsRecordsRu },
  notifications: notificationsRu,
  admin: adminRu,
};

export const workspaceKa: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonKa,
  channels: channelsKa,
  loginOptions: loginOptionsKa,
  billing: billingKa,
  settings: { ...settingsKa, ...settingsRecordsKa },
  notifications: notificationsKa,
  admin: adminKa,
};
