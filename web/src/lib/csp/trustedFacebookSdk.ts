/**
 * The address of Facebook's JavaScript SDK as a Trusted Types value, for
 * the script the connect dialog adds (assistant/channels/_lib/facebookSdk.ts).
 * The page's default policy admits scripts of the cabinet and Turnstile only
 * (trustedTypes.ts); this named policy vouches for nothing but the SDK's own
 * address in one of Facebook's locales, and only the pages whose Content
 * Security Policy admits connect.facebook.net use it (lib/metaSignInPages.ts).
 * Browsers without Trusted Types get the string itself.
 */

interface ScriptUrlPolicy {
  createScriptURL: (value: string) => unknown;
}

interface TrustedTypesFactory {
  createPolicy: (name: string, rules: { createScriptURL: (value: string) => string }) => ScriptUrlPolicy;
}

const POLICY_NAME = "facebook-sdk";
const SDK_ADDRESS = /^https:\/\/connect\.facebook\.net\/[a-z]{2}_[A-Z]{2}\/sdk\.js$/;

/** Whether an address is the SDK's (and nothing else of Facebook's). */
function isFacebookSdkAddress(value: string): boolean {
  return SDK_ADDRESS.test(value);
}

let policy: ScriptUrlPolicy | null | undefined;

function sdkPolicy(): ScriptUrlPolicy | null {
  if (policy === undefined) {
    const factory = (globalThis as { trustedTypes?: TrustedTypesFactory }).trustedTypes;
    policy = factory
      ? factory.createPolicy(POLICY_NAME, {
          createScriptURL: (value) => {
            if (!isFacebookSdkAddress(value)) {
              throw new TypeError("Only Facebook's SDK passes the facebook-sdk policy.");
            }
            return value;
          },
        })
      : null;
  }
  return policy;
}

/** The SDK's address as a script's `src` takes it (throws for any other address). */
export function trustedFacebookSdkUrl(address: string): string {
  const current = sdkPolicy();
  if (current === null) {
    return address;
  }
  // A TrustedScriptURL stands in for the string: the element takes it as it is.
  return current.createScriptURL(address) as string;
}
