"use client";

/**
 * Confetti for the moment the assistant goes live: three bursts drawn on a
 * canvas over the page in clay, sand and ink, gone in about three seconds. Nothing is drawn with
 * reduced motion (the finale's glow and card carry the moment then).
 */

import { useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";

import { confettiPalette } from "@/lib/tunnel/confettiPalette";
import { advance, alive, burst, type Particle } from "@/lib/tunnel/depth";

const MAX_STEP_SECONDS = 0.05;

function draw(context: CanvasRenderingContext2D, particles: readonly Particle[]) {
  for (const particle of particles) {
    context.save();
    context.globalAlpha = Math.min(1, particle.life);
    context.translate(particle.x, particle.y);
    context.rotate(particle.rotation);
    context.fillStyle = particle.color;
    context.fillRect(-particle.size / 2, -particle.size / 4, particle.size, particle.size / 2);
    context.restore();
  }
}

export function Confetti() {
  const canvas = useRef<HTMLCanvasElement>(null);
  const isReduced = useReducedMotion();

  useEffect(() => {
    const node = canvas.current;
    const context = node?.getContext("2d");
    if (!node || !context || isReduced) {
      return;
    }
    const ratio = window.devicePixelRatio || 1;
    const size = () => ({ width: window.innerWidth, height: window.innerHeight });
    const resize = () => {
      const { width, height } = size();
      node.width = width * ratio;
      node.height = height * ratio;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };
    resize();
    const { width, height } = size();
    // Clay, sand and the page's ink (the canvas carries text-ink, so its colour follows the theme).
    const palette = confettiPalette(getComputedStyle(node).color);
    let particles = [
      ...burst(110, { x: width * 0.5, y: height * 0.38 }, palette),
      ...burst(60, { x: width * 0.18, y: height * 0.62 }, palette),
      ...burst(60, { x: width * 0.82, y: height * 0.62 }, palette),
    ];
    let last = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      const seconds = Math.min((now - last) / 1000, MAX_STEP_SECONDS);
      last = now;
      particles = alive(
        particles.map((particle) => advance(particle, seconds)),
        size().height,
      );
      context.clearRect(0, 0, node.width, node.height);
      draw(context, particles);
      if (particles.length > 0) {
        frame = requestAnimationFrame(tick);
      }
    };
    frame = requestAnimationFrame(tick);
    window.addEventListener("resize", resize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
    };
  }, [isReduced]);

  return <canvas ref={canvas} aria-hidden className="pointer-events-none fixed inset-0 z-40 size-full text-ink" />;
}
