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
import { tunnelBusinessEn } from "./setup/tunnelBusiness.en";
import { tunnelLaunchEn } from "./setup/tunnelLaunch.en";
import { tunnelOfferEn } from "./setup/tunnelOffer.en";
import { tunnelTeamEn } from "./setup/tunnelTeam.en";
import { tunnelIt } from "./setup/tunnel.it";
import { tunnelBusinessIt } from "./setup/tunnelBusiness.it";
import { tunnelLaunchIt } from "./setup/tunnelLaunch.it";
import { tunnelOfferIt } from "./setup/tunnelOffer.it";
import { tunnelTeamIt } from "./setup/tunnelTeam.it";

export const setupFlowEn = {
  tunnel: tunnelEn,
  tunnelBusiness: tunnelBusinessEn,
  tunnelOffer: tunnelOfferEn,
  tunnelTeam: tunnelTeamEn,
  tunnelLaunch: tunnelLaunchEn,
} as const;

export const setupFlowIt: Translation<typeof setupFlowEn> = {
  tunnel: tunnelIt,
  tunnelBusiness: tunnelBusinessIt,
  tunnelOffer: tunnelOfferIt,
  tunnelTeam: tunnelTeamIt,
  tunnelLaunch: tunnelLaunchIt,
};
