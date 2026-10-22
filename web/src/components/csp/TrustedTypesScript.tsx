import { trustedTypesBootstrap } from "@/lib/csp/trustedTypes";

/**
 * The first script of every page: installs the Trusted Types default
 * policy (src/lib/csp/trustedTypes.ts) before any other script can reach
 * a sink. Rendered by the root layout into <head>, with the page's nonce.
 */
export function TrustedTypesScript({ nonce }: { nonce: string | undefined }) {
  return <script nonce={nonce} dangerouslySetInnerHTML={{ __html: trustedTypesBootstrap() }} />;
}
