"use client";

import { useEffect, useRef } from "react";

import { hideLinkToken, openPageSession, storePageSession } from "./pageSession";

/**
 * Takes the link's token out of the address bar once the page has opened:
 * the token is traded for the page's credential, which the page uses from
 * then on (`onCredential`), and the address becomes `/r/booking`. With
 * `isSession` the page already runs on a credential: each newer one an
 * answer carries (a move re-issues it) is kept for the tab. When the
 * trade fails, or the browser keeps nothing, the page goes on with the
 * link as before.
 */
export function usePageSession({
  token,
  language,
  isSession,
  expiresAt,
  onCredential,
}: {
  token: string;
  language: string;
  isSession: boolean;
  expiresAt: number | null;
  onCredential: (token: string, expiresAt: number) => void;
}) {
  const traded = useRef(false);
  const isMounted = useRef(false);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    // Once per page: a second run (React's strict mode) keeps the first trade.
    if (isSession || traded.current) {
      return;
    }
    traded.current = true;
    openPageSession(token, language)
      .then((session) => {
        if (isMounted.current && storePageSession(session)) {
          onCredential(session.token, session.expiresAt);
          hideLinkToken();
        }
      })
      .catch(() => {
        // The link keeps working: the page simply keeps it.
      });
  }, [isSession, token, language, onCredential]);

  useEffect(() => {
    if (isSession && expiresAt !== null) {
      storePageSession({ token, expiresAt, language });
    }
  }, [isSession, token, expiresAt, language]);
}
