/**
 * GET /.well-known/security.txt (RFC 9116): the security contact, the
 * policy and the file's canonical address (src/server/securityTxt.ts).
 */

import { headers } from "next/headers";

import { securityTxt } from "@/server/securityTxt";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  return new Response(securityTxt(await headers()), {
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "public, max-age=3600",
    },
  });
}
