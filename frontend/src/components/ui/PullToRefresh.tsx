import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

import { cn } from '@/utils';

/** How far you have to pull before letting go actually refreshes. */
const THRESHOLD = 72;

/** Past the threshold the rubber band stiffens rather than stopping dead. */
const MAX_PULL = 120;

/**
 * Drag resistance. A finger travelling 200px moves the sheet about 90px, which
 * is what every native list on a phone feels like; a 1:1 follow feels loose.
 */
const resist = (distance: number) =>
  Math.min(MAX_PULL, distance * 0.5 * (1 - Math.min(distance, 400) / 900));

interface PullToRefreshProps {
  /** Runs on release past the threshold. Awaited, so the spinner is honest. */
  onRefresh: () => Promise<unknown> | unknown;
  /**
   * Whether a refresh is already running — from a poll, a focus, or the
   * button. The indicator tracks it so two refreshes never race visually.
   */
  refreshing?: boolean;
  /** Turn the gesture off entirely, e.g. while the page has nothing to show. */
  disabled?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * Swipe down at the top of the page to refresh, the way a phone does it.
 *
 * Scores move while you are looking at them. Polling covers the general case,
 * but the moment that actually matters is the one right after a touchdown,
 * when you want the numbers *now* — and the gesture everybody already knows
 * for that is a pull.
 *
 * Only touch input engages this; a mouse has a Refresh button instead. The
 * listeners are attached by hand rather than through React's props because
 * React registers `touchmove` passively, and a passive listener cannot call
 * `preventDefault` to stop the browser's own overscroll fighting the gesture.
 */
export const PullToRefresh: React.FC<PullToRefreshProps> = ({
  onRefresh,
  refreshing = false,
  disabled = false,
  children,
  className,
}) => {
  const host = useRef<HTMLDivElement>(null);
  const startY = useRef<number | null>(null);
  const [pull, setPull] = useState(0);
  const [busy, setBusy] = useState(false);

  const active = busy || refreshing;
  const armed = pull >= THRESHOLD;

  const run = useCallback(async () => {
    setBusy(true);
    try {
      await onRefresh();
    } finally {
      setBusy(false);
    }
  }, [onRefresh]);

  useEffect(() => {
    const node = host.current;
    if (!node || disabled) return undefined;

    const atTop = () => window.scrollY <= 0;

    const onStart = (e: TouchEvent) => {
      // A second finger means a pinch, not a pull.
      startY.current = atTop() && e.touches.length === 1 ? e.touches[0].clientY : null;
    };

    const onMove = (e: TouchEvent) => {
      if (startY.current === null) return;
      const distance = e.touches[0].clientY - startY.current;

      // Scrolling up, or the page scrolled away under the finger: hand the
      // gesture back to the browser rather than half-owning it.
      if (distance <= 0 || !atTop()) {
        startY.current = null;
        setPull(0);
        return;
      }

      if (e.cancelable) e.preventDefault();
      setPull(resist(distance));
    };

    const onEnd = () => {
      if (startY.current === null) return;
      startY.current = null;
      setPull((current) => {
        if (current >= THRESHOLD) void run();
        return 0;
      });
    };

    node.addEventListener('touchstart', onStart, { passive: true });
    node.addEventListener('touchmove', onMove, { passive: false });
    node.addEventListener('touchend', onEnd);
    node.addEventListener('touchcancel', onEnd);

    return () => {
      node.removeEventListener('touchstart', onStart);
      node.removeEventListener('touchmove', onMove);
      node.removeEventListener('touchend', onEnd);
      node.removeEventListener('touchcancel', onEnd);
    };
  }, [disabled, run]);

  // While refreshing the sheet rests at the threshold so the spinner has
  // somewhere to sit; otherwise it follows the finger and springs back.
  const offset = active ? THRESHOLD * 0.6 : pull;
  const dragging = pull > 0;

  return (
    <div ref={host} className={cn('relative', className)}>
      {/* The indicator rides above the content and is revealed by the pull. */}
      <div
        aria-hidden={!active}
        className="pointer-events-none absolute inset-x-0 top-0 z-10 flex justify-center"
        style={{
          transform: `translateY(${Math.max(offset - 44, -44)}px)`,
          opacity: offset > 4 ? Math.min(1, offset / THRESHOLD) : 0,
          transition: dragging ? 'none' : 'transform 220ms ease-out, opacity 180ms ease-out',
        }}
      >
        <span
          className={cn(
            'flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-raised shadow-elevation-2',
            armed && !active && 'border-brand'
          )}
        >
          <ArrowPathIcon
            className={cn(
              'h-5 w-5',
              active ? 'text-brand motion-safe:animate-spin' : armed ? 'text-brand' : 'text-fg-muted'
            )}
            style={
              active
                ? undefined
                : { transform: `rotate(${Math.min(pull / THRESHOLD, 1) * 270}deg)` }
            }
          />
        </span>
      </div>

      <div
        style={{
          transform: `translateY(${offset}px)`,
          transition: dragging ? 'none' : 'transform 220ms ease-out',
        }}
      >
        {children}
      </div>

      <span aria-live="polite" className="sr-only">
        {active ? 'Refreshing' : ''}
      </span>
    </div>
  );
};
