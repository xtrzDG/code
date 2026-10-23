/**
 * Facebook's JavaScript SDK, loaded once and only when a connect dialog
 * that offers "Continue with Facebook" opens (never with the page), from
 * Facebook's own address and in the cabinet's language. Only the pages of
 * lib/metaSignInPages.ts let it run (their Content Security Policy), and
 * its address passes the Trusted Types policy `facebook-sdk`
 * (lib/csp/trustedFacebookSdk.ts).
 */

import { trustedFacebookSdkUrl } from "@/lib/csp/trustedFacebookSdk";

export interface FacebookLoginResponse {
  authResponse?: { code?: string | null } | null;
  status?: string;
}

export interface FacebookSdk {
  init(options: { appId: string; version: string; xfbml: boolean; cookie: boolean; autoLogAppEvents: boolean }): void;
  /** Facebook refuses an `async` callback: pass a plain function. */
  login(callback: (response: FacebookLoginResponse) => void, options: Record<string, unknown>): void;
}

declare global {
  interface Window {
    FB?: FacebookSdk;
    fbAsyncInit?: () => void;
  }
}

/** Facebook's names of the cabinet's languages (its dialogs speak them). */
const SDK_LOCALES: Readonly<Record<string, string>> = {
  en: "en_US",
  ru: "ru_RU",
  ka: "ka_GE",
  he: "he_IL",
  de: "de_DE",
};

export function facebookSdkUrl(locale: string): string {
  return `https://connect.facebook.net/${SDK_LOCALES[locale] ?? "en_US"}/sdk.js`;
}

const LOAD_TIMEOUT_MS = 20_000;
let loading: Promise<FacebookSdk> | null = null;

/** The SDK, loading it on the first call; a failed load can be tried again. */
export function loadFacebookSdk(locale: string): Promise<FacebookSdk> {
  if (window.FB) {
    return Promise.resolve(window.FB);
  }
  loading ??= new Promise<FacebookSdk>((resolve, reject) => {
    const script = document.createElement("script");
    const fail = () => {
      window.clearTimeout(timer);
      loading = null;
      script.remove();
      reject(new Error("Facebook's SDK did not load."));
    };
    const settle = () => {
      if (window.FB) {
        window.clearTimeout(timer);
        resolve(window.FB);
      }
    };
    const timer = window.setTimeout(fail, LOAD_TIMEOUT_MS);
    window.fbAsyncInit = settle;
    script.src = trustedFacebookSdkUrl(facebookSdkUrl(locale));
    script.async = true;
    script.crossOrigin = "anonymous";
    script.onload = settle;
    script.onerror = fail;
    document.head.appendChild(script);
  });
  return loading;
}
