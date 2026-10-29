/**
 * Texts of the cabinet's frame: the five sections and the navigation,
 * the user menu and installing the app, "Create an AI assistant" before
 * the assistant exists, the offline page, the live cabinet and the
 * phone's compact page chrome, the notice of a new data processing
 * agreement, and closing a business or deleting an account.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./shell/`; this
 * file composes them.
 */

import type { Translation } from "../../translate";
import { accountEn } from "./shell/account.en";
import { appEn } from "./shell/app.en";
import { chromeEn } from "./shell/chrome.en";
import { closureIt } from "./shell/closure.it";
import { closureEn } from "./shell/closure.en";
import { dpaNoticeEn } from "./shell/dpaNotice.en";
import { liveEn } from "./shell/live.en";
import { navigationEn } from "./shell/navigation.en";
import { setupEn } from "./shell/setup.en";
import { accountIt } from "./shell/account.it";
import { appIt } from "./shell/app.it";
import { chromeIt } from "./shell/chrome.it";
import { dpaNoticeIt } from "./shell/dpaNotice.it";
import { liveIt } from "./shell/live.it";
import { navigationIt } from "./shell/navigation.it";
import { setupIt } from "./shell/setup.it";

export const shellEn = {
  navigation: navigationEn,
  account: accountEn,
  setup: setupEn,
  app: appEn,
  live: liveEn,
  chrome: chromeEn,
  dpaNotice: dpaNoticeEn,
  closure: closureEn,
} as const;

export const shellIt: Translation<typeof shellEn> = {
  navigation: navigationIt,
  account: accountIt,
  setup: setupIt,
  app: appIt,
  live: liveIt,
  chrome: chromeIt,
  dpaNotice: dpaNoticeIt,
  closure: closureIt,
};
