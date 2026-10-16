/**
 * Texts of "Create an AI assistant", the full-screen setup at /create and
 * /b/{id}/setup: its frame, the business and where it is, what it offers
 * and when it is open, who helps and where customers write, trying it,
 * the launch and the finale.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries (the frame's `setup.*` is the invitation before the
 * assistant exists, in shell.ts). The other languages are type-checked against `en`.
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
import { tunnelHe } from "./setup/tunnel.he";
import { tunnelDe } from "./setup/tunnel.de";
import { tunnelBusinessHe } from "./setup/tunnelBusiness.he";
import { tunnelBusinessDe } from "./setup/tunnelBusiness.de";
import { tunnelLaunchHe } from "./setup/tunnelLaunch.he";
import { tunnelLaunchDe } from "./setup/tunnelLaunch.de";
import { tunnelOfferHe } from "./setup/tunnelOffer.he";
import { tunnelOfferDe } from "./setup/tunnelOffer.de";
import { tunnelTeamHe } from "./setup/tunnelTeam.he";
import { tunnelTeamDe } from "./setup/tunnelTeam.de";

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

export const setupFlowHe: Translation<typeof setupFlowEn> = {
  tunnel: tunnelHe,
  tunnelBusiness: tunnelBusinessHe,
  tunnelOffer: tunnelOfferHe,
  tunnelTeam: tunnelTeamHe,
  tunnelLaunch: tunnelLaunchHe,
};

export const setupFlowDe: Translation<typeof setupFlowEn> = {
  tunnel: tunnelDe,
  tunnelBusiness: tunnelBusinessDe,
  tunnelOffer: tunnelOfferDe,
  tunnelTeam: tunnelTeamDe,
  tunnelLaunch: tunnelLaunchDe,
};
