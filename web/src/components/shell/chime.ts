"use client";

/**
 * The short two-note chime when a customer needs a person. Browsers let a
 * page make sound only after the person interacted with it, so the audio
 * context is created on the first click or key press (or when the chime is
 * turned on) and the chime is skipped until then.
 */

import { useEffect, useSyncExternalStore } from "react";

import { readChimePreference, subscribeChimePreference, writeChimePreference } from "@/lib/chimePreference";

type AudioContextClass = typeof AudioContext;

let context: AudioContext | null = null;

function audioContextClass(): AudioContextClass | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }
  return window.AudioContext ?? (window as unknown as { webkitAudioContext?: AudioContextClass }).webkitAudioContext;
}

/** Prepares sound output (call from a click or key press). */
export function unlockChime(): void {
  const AudioContextType = audioContextClass();
  if (!AudioContextType) {
    return;
  }
  context ??= new AudioContextType();
  if (context.state === "suspended") {
    void context.resume().catch(() => undefined);
  }
}

/** Plays the chime if sound output is ready; false when it could not. */
export function playChime(): boolean {
  if (!context || context.state !== "running") {
    return false;
  }
  const start = context.currentTime;
  [880, 1318.5].forEach((frequency, index) => {
    if (!context) {
      return;
    }
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const at = start + index * 0.14;
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(0.16, at + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 0.36);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(at);
    oscillator.stop(at + 0.4);
  });
  return true;
}

const serverSnapshot = () => false;

/** Whether this device chimes, and how to change it. */
export function useChimePreference(): [boolean, (isOn: boolean) => void] {
  const isOn = useSyncExternalStore(subscribeChimePreference, readChimePreference, serverSnapshot);
  return [isOn, writeChimePreference];
}

/** While the chime is on, the first click or key press prepares sound output. */
export function useChimeUnlock(isOn: boolean): void {
  useEffect(() => {
    if (!isOn) {
      return;
    }
    const unlock = () => unlockChime();
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, [isOn]);
}
