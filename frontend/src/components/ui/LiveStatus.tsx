import React, { useEffect, useState } from 'react';
import { ArrowPathIcon } from '@heroicons/react/24/outline';

import { cn } from '@/utils';

/**
 * How old the numbers on screen are, in the words somebody would use.
 *
 * Exported because the wording is the point: "a moment ago" is honest about a
 * few seconds of slack in a way "0s ago" is not, and the whole app should say
 * it the same way.
 */
export const describeAge = (ms: number): string => {
  const seconds = Math.max(0, Math.round(ms / 1000));
  if (seconds < 10) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`;
};

interface LiveStatusProps {
  /** When the data on screen was fetched (react-query's `dataUpdatedAt`). */
  updatedAt?: number;
  /** A fetch is in flight — including a background poll. */
  refreshing?: boolean;
  /** Something is happening in the NFL right now, so the dot pulses. */
  live?: boolean;
  /** What the live dot is counting, e.g. "2 games live". */
  liveLabel?: string;
  onRefresh: () => void;
  className?: string;
}

/**
 * The strip that says how fresh what you are looking at is, and lets you do
 * something about it.
 *
 * Polling alone leaves a question a scoreboard cannot answer: *is this
 * number old?* Saying when it was last fetched costs one line and removes the
 * doubt. The button is the desktop counterpart to the pull-to-refresh gesture
 * on a phone — the same action, reachable with a mouse.
 */
export const LiveStatus: React.FC<LiveStatusProps> = ({
  updatedAt,
  refreshing = false,
  live = false,
  liveLabel,
  onRefresh,
  className,
}) => {
  // "34s ago" has to keep counting on its own; nothing else re-renders this.
  const [, tick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => tick((n) => n + 1), 15 * 1000);
    return () => window.clearInterval(id);
  }, []);

  const age = updatedAt ? describeAge(Date.now() - updatedAt) : null;

  return (
    <div className={cn('flex flex-wrap items-center gap-x-3 gap-y-1 text-xs', className)}>
      {live && (
        <span className="inline-flex items-center gap-1.5 font-semibold text-accent">
          <span
            aria-hidden
            className="h-1.5 w-1.5 rounded-full bg-accent motion-safe:animate-pulse"
          />
          {liveLabel || 'Live'}
        </span>
      )}

      <span className="text-fg-subtle" aria-live="polite">
        {refreshing ? 'Updating…' : age ? `Updated ${age}` : ''}
      </span>

      <button
        type="button"
        onClick={onRefresh}
        disabled={refreshing}
        className="ml-auto inline-flex min-h-[2rem] items-center gap-1.5 rounded-lg px-2 py-1 font-semibold text-fg-muted transition-colors hover:bg-surface-sunken hover:text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
      >
        <ArrowPathIcon
          className={cn('h-4 w-4', refreshing && 'motion-safe:animate-spin')}
          aria-hidden
        />
        Refresh
      </button>
    </div>
  );
};
