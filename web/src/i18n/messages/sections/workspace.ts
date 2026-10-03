/**
 * Texts of the cabinet sections: Channels, billing, settings (Calls, Quick replies and Reviews among them) and the platform admin.
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
import { adminSecurityEn } from "./workspace/adminSecurity.en";
import { adminSecurityKa } from "./workspace/adminSecurity.ka";
import { adminSecurityRu } from "./workspace/adminSecurity.ru";
import { billingEn } from "./workspace/billing.en";
import { billingKa } from "./workspace/billing.ka";
import { billingRu } from "./workspace/billing.ru";
import { callSettingsEn } from "./workspace/callSettings.en";
import { callSettingsKa } from "./workspace/callSettings.ka";
import { callSettingsRu } from "./workspace/callSettings.ru";
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
import { privacyNoticeEn } from "./workspace/privacyNotice.en";
import { privacyNoticeKa } from "./workspace/privacyNotice.ka";
import { privacyNoticeRu } from "./workspace/privacyNotice.ru";
import { quickRepliesEn } from "./workspace/quickReplies.en";
import { quickRepliesKa } from "./workspace/quickReplies.ka";
import { quickRepliesRu } from "./workspace/quickReplies.ru";
import { reviewSettingsEn } from "./workspace/reviewSettings.en";
import { reviewSettingsKa } from "./workspace/reviewSettings.ka";
import { reviewSettingsRu } from "./workspace/reviewSettings.ru";
import { settingsEn } from "./workspace/settings.en";
import { settingsKa } from "./workspace/settings.ka";
import { settingsRu } from "./workspace/settings.ru";
import { settingsRecordsEn } from "./workspace/settingsRecords.en";
import { settingsRecordsKa } from "./workspace/settingsRecords.ka";
import { settingsRecordsRu } from "./workspace/settingsRecords.ru";
import { shareEn } from "./workspace/share.en";
import { shareKa } from "./workspace/share.ka";
import { shareRu } from "./workspace/share.ru";

export const workspaceEn = {
  workspace: workspaceCommonEn,
  channels: channelsEn,
  loginOptions: loginOptionsEn,
  billing: billingEn,
  settings: { ...settingsEn, ...settingsRecordsEn },
  notifications: notificationsEn,
  callSettings: callSettingsEn,
  reviewSettings: reviewSettingsEn,
  quickReplies: quickRepliesEn,
  admin: adminEn,
  adminSecurity: adminSecurityEn,
  share: shareEn,
  privacyNotice: privacyNoticeEn,
} as const;

export const workspaceRu: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonRu,
  channels: channelsRu,
  loginOptions: loginOptionsRu,
  billing: billingRu,
  settings: { ...settingsRu, ...settingsRecordsRu },
  notifications: notificationsRu,
  callSettings: callSettingsRu,
  reviewSettings: reviewSettingsRu,
  quickReplies: quickRepliesRu,
  admin: adminRu,
  adminSecurity: adminSecurityRu,
  share: shareRu,
  privacyNotice: privacyNoticeRu,
};

export const workspaceKa: Translation<typeof workspaceEn> = {
  workspace: workspaceCommonKa,
  channels: channelsKa,
  loginOptions: loginOptionsKa,
  billing: billingKa,
  settings: { ...settingsKa, ...settingsRecordsKa },
  notifications: notificationsKa,
  callSettings: callSettingsKa,
  reviewSettings: reviewSettingsKa,
  quickReplies: quickRepliesKa,
  admin: adminKa,
  adminSecurity: adminSecurityKa,
  share: shareKa,
  privacyNotice: privacyNoticeKa,
};
