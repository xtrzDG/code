"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  browserStorage,
  currentPushSupport,
  existingSubscription,
  isEndpointRememberedElsewhere,
  notifyPushState,
  parseRememberedDevice,
  rememberDevice,
  rememberedDeviceText,
  subscribePushState,
  subscribeThisBrowser,
  subscriptionBody,
} from "@/lib/webPush";

import { findThisDevice, type NotificationPreferences, type PushDevice } from "./notifications";

const IS_PRODUCTION = process.env.NODE_ENV === "production";
const noBrowser = () => null;

/** Why turning this device on did not work, shown under the button. */
export type DeviceProblem = "dismissed" | "denied" | "failed";

export const DEVICE_PROBLEMS: Record<DeviceProblem, MessageKey> = {
  dismissed: "notifications.device.dismissed",
  denied: "notifications.device.denied",
  failed: "notifications.device.failed",
};

/**
 * My notifications in this business: the events and quiet hours I chose,
 * and my devices, this browser among them ("Enable notifications on this
 * device" subscribes it at its push service and gives the subscription to
 * the API). A browser has one subscription for the whole cabinet, so
 * turning it off in one business keeps it for the others.
 */
export function useMyNotifications() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const key = queryKeys.notifications.mine(business.id);
  const path = { business_id: business.id };
  const settings = useQuery(key, () => api.GET("/v1/businesses/{business_id}/notification-preferences", { params: { path } }));

  // The browser is only read after hydration (the server knows nothing of it).
  const support = useSyncExternalStore(subscribePushState, currentPushSupport, noBrowser);
  const rememberedText = useSyncExternalStore(
    subscribePushState,
    () => rememberedDeviceText(browserStorage(), business.id),
    noBrowser,
  );
  const remembered = useMemo(() => parseRememberedDevice(rememberedText), [rememberedText]);
  const [endpoint, setEndpoint] = useState<string | null>(null);
  const [problem, setProblem] = useState<DeviceProblem | null>(null);
  const [isSwitching, setIsSwitching] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    existingSubscription()
      .then((subscription) => {
        if (isCurrent) {
          setEndpoint(subscription?.endpoint ?? null);
        }
      })
      .catch(() => undefined);
    return () => {
      isCurrent = false;
    };
  }, [business.id]);

  const savePreferences = useMutation(
    (preferences: NotificationPreferences) =>
      api.PUT("/v1/businesses/{business_id}/notification-preferences", {
        params: { path },
        body: { events: preferences.events ?? [], quiet_hours: preferences.quiet_hours ?? null },
      }),
    { errorToast: false },
  );
  const subscribe = useMutation(
    (body: NonNullable<ReturnType<typeof subscriptionBody>>) =>
      api.POST("/v1/businesses/{business_id}/push-subscriptions", { params: { path }, body }),
    { invalidate: [key] },
  );
  const unsubscribe = useMutation(
    (device: PushDevice) =>
      api.DELETE("/v1/businesses/{business_id}/push-subscriptions/{subscription_id}", {
        params: { path: { ...path, subscription_id: device.id } },
      }),
    { invalidate: [key] },
  );
  const check = useMutation(
    (device: PushDevice) =>
      api.POST("/v1/businesses/{business_id}/push-subscriptions/{subscription_id}/test", {
        params: { path: { ...path, subscription_id: device.id } },
      }),
    { invalidate: [key] },
  );

  const devices = settings.data?.devices ?? [];
  const thisDevice = findThisDevice(devices, remembered, endpoint);
  const publicKey = settings.data?.push_public_key ?? null;

  const enable = async () => {
    if (publicKey === null) {
      return;
    }
    setProblem(null);
    setIsSwitching(true);
    try {
      const outcome = await subscribeThisBrowser(publicKey, IS_PRODUCTION);
      if (!outcome.ok) {
        setProblem(outcome.reason);
        notifyPushState();
        return;
      }
      const body = subscriptionBody(outcome.subscription, locale);
      if (body === null) {
        setProblem("failed");
        return;
      }
      const result = await subscribe.run(body);
      if (result.ok) {
        const device = { endpoint: body.endpoint, deviceId: result.data.id };
        rememberDevice(browserStorage(), business.id, device);
        setEndpoint(body.endpoint);
        settings.setData((current) => current && { ...current, devices: [...current.devices.filter((item) => item.id !== result.data.id), result.data] });
        toast.success(t("notifications.device.enabled"));
      }
    } catch {
      setProblem("failed");
    } finally {
      setIsSwitching(false);
    }
  };

  const disable = async () => {
    if (thisDevice === null || remembered === null) {
      return;
    }
    setIsSwitching(true);
    try {
      const result = await unsubscribe.run(thisDevice);
      if (!result.ok) {
        return;
      }
      rememberDevice(browserStorage(), business.id, null);
      if (!isEndpointRememberedElsewhere(browserStorage(), business.id, remembered.endpoint)) {
        const subscription = await existingSubscription().catch(() => null);
        await subscription?.unsubscribe().catch(() => false);
        setEndpoint(null);
      }
      toast.success(t("notifications.device.disabled"));
    } finally {
      setIsSwitching(false);
    }
  };

  const removeOther = async (device: PushDevice) => {
    const result = await unsubscribe.run(device);
    if (result.ok) {
      toast.success(t("notifications.device.removed"));
    }
  };

  const sendTest = async (device: PushDevice) => {
    const result = await check.run(device);
    if (!result.ok) {
      return;
    }
    const { status, last_error: error } = result.data.delivery;
    if (status === "delivered") {
      toast.success(t("notifications.contacts.testDelivered", { name: t("notifications.device.title") }));
    } else {
      toast.show({
        tone: status === "dead" ? "error" : "info",
        title: t(status === "dead" ? "notifications.contacts.testFailed" : "notifications.contacts.testPending", {
          name: t("notifications.device.title"),
          error: error ?? "",
        }),
      });
    }
  };

  return {
    settings,
    support,
    problem,
    publicKey,
    thisDevice,
    otherDevices: devices.filter((device) => device.id !== thisDevice?.id),
    isSwitching,
    isChecking: check.isPending,
    enable,
    disable,
    removeOther,
    sendTest,
    savePreferences,
  };
}
