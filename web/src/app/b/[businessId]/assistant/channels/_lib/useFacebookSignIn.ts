"use client";

/**
 * "Continue with Facebook" as state, for one channel's connect dialog:
 *
 *  1. The dialog opens: Facebook's SDK loads (only now, and only where the
 *     page may open Facebook; elsewhere the first click loads the page
 *     again and reopens the dialog: lib/metaSignInPages.ts).
 *  2. The owner presses the button: the server starts a one-time sign-in
 *     (it asks "confirm it is you" first if needed, so Meta's code never
 *     waits for it). Facebook's window opens at once while the click still
 *     counts as the owner's; otherwise a second button opens it.
 *  3. Facebook answers with a code: WhatsApp is connected with it (and the
 *     ids its signup window reported), or the owner's pages are listed to
 *     pick one for Instagram or Messenger.
 *
 * The code and the sign-in's state live only in memory; failures stay in
 * the dialog (toasts sit under it).
 */

import { useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";

import type { ChannelView } from "./channels";
import { loadFacebookSdk, type FacebookLoginResponse, type FacebookSdk } from "./facebookSdk";
import {
  completeSignupBody,
  documentAllowsFacebook,
  facebookLoginOptions,
  loadedDocumentUrl,
  purposeOf,
  readSignupMessage,
  resumeAddress,
  type MetaChannel,
  type MetaPage,
  type MetaSignInStart,
  type SignupSession,
} from "./metaSignIn";

type FacebookStep =
  | { name: "idle" }
  | { name: "starting" }
  | { name: "ready"; start: MetaSignInStart }
  | { name: "window"; start: MetaSignInStart }
  | { name: "finishing" }
  | { name: "pages"; state: string; pages: MetaPage[] }
  | { name: "connecting"; state: string; pages: MetaPage[]; pageId: string };

/** Why Facebook's window gave nothing back. */
export type FacebookNotice = "cancelled" | "failed" | "unavailable";

export interface FacebookSignIn {
  step: FacebookStep;
  notice: FacebookNotice | null;
  error: ApiError | null;
  /** The SDK is loaded (or the page loads again on the first click). */
  isSdkReady: boolean;
  begin: () => void;
  openWindow: () => void;
  pickPage: (pageId: string) => void;
}

function isUserActive(): boolean {
  const activation = (navigator as Navigator & { userActivation?: { isActive: boolean } }).userActivation;
  return activation?.isActive === true;
}

export function useFacebookSignIn(options: {
  businessId: string;
  kind: MetaChannel;
  locale: string;
  isOffered: boolean;
  onConnected: (channel: ChannelView) => void;
}): FacebookSignIn {
  const { businessId, kind, locale, isOffered } = options;
  const [step, setStep] = useState<FacebookStep>({ name: "idle" });
  const [notice, setNotice] = useState<FacebookNotice | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [sdk, setSdk] = useState<FacebookSdk | null>(null);
  const session = useRef<SignupSession | null>(null);
  const onConnected = useRef(options.onConnected);
  useEffect(() => {
    onConnected.current = options.onConnected;
  });
  const [isAllowedHere] = useState(() => typeof window !== "undefined" && documentAllowsFacebook(loadedDocumentUrl()));

  useEffect(() => {
    if (!isOffered || !isAllowedHere) {
      return;
    }
    let isCurrent = true;
    loadFacebookSdk(locale)
      .then((loaded) => isCurrent && setSdk(loaded))
      .catch(() => isCurrent && setNotice("unavailable"));
    return () => {
      isCurrent = false;
    };
  }, [isOffered, isAllowedHere, locale]);

  useEffect(() => {
    if (kind !== "whatsapp" || !isOffered) {
      return;
    }
    const onMessage = (event: MessageEvent) => {
      session.current = readSignupMessage(event.origin, event.data) ?? session.current;
    };
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [kind, isOffered]);

  const stale = [queryKeys.assistant.all(businessId), queryKeys.channels.all(businessId)];
  const startSignIn = useMutation(
    () =>
      api.POST("/v1/businesses/{business_id}/channels/meta/sign-in", {
        params: { path: { business_id: businessId } },
        body: { purpose: purposeOf(kind) },
      }),
    { errorToast: false },
  );
  const completeSignup = useMutation(
    (start: MetaSignInStart, code: string) =>
      api.POST("/v1/businesses/{business_id}/channels/whatsapp/embedded-signup", {
        params: { path: { business_id: businessId } },
        body: completeSignupBody(start.state, code, session.current),
      }),
    { errorToast: false, stale },
  );
  const listPages = useMutation(
    (start: MetaSignInStart, code: string) =>
      api.POST("/v1/businesses/{business_id}/channels/meta/pages", {
        params: { path: { business_id: businessId } },
        body: { state: start.state, code },
      }),
    { errorToast: false },
  );
  const connectPage = useMutation(
    (state: string, pageId: string) =>
      api.PUT("/v1/businesses/{business_id}/channels/{channel}/page", {
        params: { path: { business_id: businessId, channel: kind } },
        body: { state, page_id: pageId },
      }),
    { errorToast: false, stale },
  );

  const finish = async (start: MetaSignInStart, response: FacebookLoginResponse) => {
    const code = response.authResponse?.code;
    if (!code) {
      setNotice(session.current?.event === "error" ? "failed" : "cancelled");
      setStep({ name: "ready", start });
      return;
    }
    setStep({ name: "finishing" });
    if (start.purpose === "whatsapp") {
      const result = await completeSignup.run(start, code);
      if (result.ok) {
        onConnected.current(result.data);
        return;
      }
      setError(result.error);
      setStep({ name: "idle" });
      return;
    }
    const result = await listPages.run(start, code);
    if (result.ok) {
      setStep({ name: "pages", state: start.state, pages: result.data.pages ?? [] });
    } else {
      setError(result.error);
      setStep({ name: "idle" });
    }
  };

  const openWith = (start: MetaSignInStart) => {
    if (!sdk) {
      setNotice("unavailable");
      setStep({ name: "ready", start });
      return;
    }
    setNotice(null);
    setError(null);
    session.current = null;
    sdk.init({ appId: start.app_id, version: start.graph_api_version, xfbml: false, cookie: false, autoLogAppEvents: false });
    setStep({ name: "window", start });
    sdk.login((response) => {
      void finish(start, response);
    }, facebookLoginOptions(start));
  };

  const begin = () => {
    if (!isAllowedHere) {
      window.location.assign(resumeAddress(window.location.href, kind));
      return;
    }
    setNotice(null);
    setError(null);
    setStep({ name: "starting" });
    void startSignIn.run().then((result) => {
      if (!result.ok) {
        setError(result.error);
        setStep({ name: "idle" });
      } else if (sdk && isUserActive()) {
        openWith(result.data);
      } else {
        setStep({ name: "ready", start: result.data });
      }
    });
  };

  const openWindow = () => {
    if (step.name === "ready") {
      openWith(step.start);
    }
  };

  const pickPage = (pageId: string) => {
    if (step.name !== "pages") {
      return;
    }
    const { state, pages } = step;
    setError(null);
    setStep({ name: "connecting", state, pages, pageId });
    void connectPage.run(state, pageId).then((result) => {
      if (result.ok) {
        onConnected.current(result.data);
      } else {
        setError(result.error);
        setStep({ name: "pages", state, pages });
      }
    });
  };

  return { step, notice, error, isSdkReady: sdk !== null || !isAllowedHere, begin, openWindow, pickPage };
}
