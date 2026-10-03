/**
 * Texts of "Create an AI assistant", the full-screen setup at /create and
 * /b/{id}/setup: its frame, the business and where it is, what it offers
 * and when it is open, who helps and where customers write, trying it,
 * the launch and the finale.
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries (the frame's `setup.*` is the invitation before the
 * assistant exists, in shell.ts). `ru` and `ka` are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { tunnelEn } from "./setup/tunnel.en";
import { tunnelKa } from "./setup/tunnel.ka";
import { tunnelRu } from "./setup/tunnel.ru";
import { tunnelBusinessEn } from "./setup/tunnelBusiness.en";
import { tunnelBusinessKa } from "./setup/tunnelBusiness.ka";
import { tunnelBusinessRu } from "./setup/tunnelBusiness.ru";
import { tunnelLaunchEn } from "./setup/tunnelLaunch.en";
import { tunnelLaunchKa } from "./setup/tunnelLaunch.ka";
import { tunnelLaunchRu } from "./setup/tunnelLaunch.ru";
import { tunnelOfferEn } from "./setup/tunnelOffer.en";
import { tunnelOfferKa } from "./setup/tunnelOffer.ka";
import { tunnelOfferRu } from "./setup/tunnelOffer.ru";
import { tunnelTeamEn } from "./setup/tunnelTeam.en";
import { tunnelTeamKa } from "./setup/tunnelTeam.ka";
import { tunnelTeamRu } from "./setup/tunnelTeam.ru";

export const setupFlowEn = {
  tunnel: tunnelEn,
  tunnelBusiness: tunnelBusinessEn,
  tunnelOffer: tunnelOfferEn,
  tunnelTeam: tunnelTeamEn,
  tunnelLaunch: tunnelLaunchEn,
} as const;

export const setupFlowRu: Translation<typeof setupFlowEn> = {
  tunnel: tunnelRu,
  tunnelBusiness: tunnelBusinessRu,
  tunnelOffer: tunnelOfferRu,
  tunnelTeam: tunnelTeamRu,
  tunnelLaunch: tunnelLaunchRu,
};

export const setupFlowKa: Translation<typeof setupFlowEn> = {
  tunnel: tunnelKa,
  tunnelBusiness: tunnelBusinessKa,
  tunnelOffer: tunnelOfferKa,
  tunnelTeam: tunnelTeamKa,
  tunnelLaunch: tunnelLaunchKa,
};
