/**
 * Texts of the cabinet's frame: the five sections and the navigation,
 * the user menu and installing the app, "Create an AI assistant" before
 * the assistant exists, the offline page and the live cabinet.
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./shell/`; this
 * file composes them.
 */

import type { Translation } from "../../translate";
import { accountEn } from "./shell/account.en";
import { accountKa } from "./shell/account.ka";
import { accountRu } from "./shell/account.ru";
import { appEn } from "./shell/app.en";
import { appKa } from "./shell/app.ka";
import { appRu } from "./shell/app.ru";
import { liveEn } from "./shell/live.en";
import { liveKa } from "./shell/live.ka";
import { liveRu } from "./shell/live.ru";
import { navigationEn } from "./shell/navigation.en";
import { navigationKa } from "./shell/navigation.ka";
import { navigationRu } from "./shell/navigation.ru";
import { setupEn } from "./shell/setup.en";
import { setupKa } from "./shell/setup.ka";
import { setupRu } from "./shell/setup.ru";

export const shellEn = {
  navigation: navigationEn,
  account: accountEn,
  setup: setupEn,
  app: appEn,
  live: liveEn,
} as const;

export const shellRu: Translation<typeof shellEn> = {
  navigation: navigationRu,
  account: accountRu,
  setup: setupRu,
  app: appRu,
  live: liveRu,
};

export const shellKa: Translation<typeof shellEn> = {
  navigation: navigationKa,
  account: accountKa,
  setup: setupKa,
  app: appKa,
  live: liveKa,
};
