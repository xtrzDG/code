/**
 * A passkey inside the tests: Chromium's virtual authenticator (the
 * DevTools protocol's WebAuthn domain), a platform authenticator that
 * keeps resident keys and verifies its user at once, as a phone's or a
 * laptop's would. Its credentials can be read and put back, which is how
 * a test plays a cloned passkey: the same key with an older signature
 * counter than the one the server has seen.
 */

import type { CDPSession, Page } from "@playwright/test";

interface VirtualCredential {
  credentialId: string;
  isResidentCredential: boolean;
  rpId?: string;
  privateKey: string;
  userHandle?: string;
  signCount: number;
}

export interface VirtualAuthenticator {
  credentials: () => Promise<VirtualCredential[]>;
  /** Puts this credential back with an older counter: a copy of the key made earlier. */
  rewindCounter: (credential: VirtualCredential, signCount: number) => Promise<void>;
}

export async function addVirtualAuthenticator(page: Page): Promise<VirtualAuthenticator> {
  const session: CDPSession = await page.context().newCDPSession(page);
  await session.send("WebAuthn.enable", { enableUI: false });
  const { authenticatorId } = await session.send("WebAuthn.addVirtualAuthenticator", {
    options: {
      protocol: "ctap2",
      transport: "internal",
      hasResidentKey: true,
      hasUserVerification: true,
      isUserVerified: true,
      automaticPresenceSimulation: true,
    },
  });
  return {
    credentials: async () => (await session.send("WebAuthn.getCredentials", { authenticatorId })).credentials,
    rewindCounter: async (credential, signCount) => {
      await session.send("WebAuthn.removeCredential", { authenticatorId, credentialId: credential.credentialId });
      await session.send("WebAuthn.addCredential", { authenticatorId, credential: { ...credential, signCount } });
    },
  };
}
