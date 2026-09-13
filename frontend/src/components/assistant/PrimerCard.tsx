import React from 'react';
import {
  ArrowsRightLeftIcon,
  ClipboardDocumentIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { useWeeklyPrimer } from '@/hooks/useAssistant';

/**
 * Your week in one card: what is broken, the one call worth making, and the
 * matchup. Everything here is computed from the roster — the closing line of
 * trash talk is the only generated part, and the card reads fine without it.
 */
export const PrimerCard: React.FC<{ leagueId: number }> = ({ leagueId }) => {
  const { data: primer, isLoading, isError } = useWeeklyPrimer(leagueId);

  if (isLoading) return <Skeleton className="h-44 w-full rounded-card" />;
  // No claimed team yet. The league page already prompts for that.
  if (isError || !primer) return null;

  const copyTrashTalk = async () => {
    if (!primer.trash_talk) return;
    await navigator.clipboard.writeText(primer.trash_talk);
    toast.success('Copied — go ruin their day');
  };

  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-base font-bold text-fg sm:text-lg">
          Your Week {primer.week}
        </h3>
        <span className="text-sm text-fg-muted">
          {primer.team_name} <span className="tabular">({primer.record})</span>
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-surface-sunken p-3">
          <div className="font-display text-xl font-bold text-brand tabular">
            {primer.projected.toFixed(1)}
          </div>
          <div className="mt-0.5 text-xs text-fg-muted">
            projected from {primer.starters} starters
          </div>
        </div>
        <div className="rounded-lg bg-surface-sunken p-3">
          <div className="truncate font-display text-base font-bold text-fg">
            {primer.opponent ?? 'No opponent'}
          </div>
          <div className="mt-0.5 text-xs text-fg-muted">this week's matchup</div>
        </div>
      </div>

      {primer.alerts.length > 0 && (
        <div className="mt-3 rounded-lg border border-warning-300 bg-warning-50 p-3 dark:border-warning-700 dark:bg-warning-900/20">
          <div className="flex items-start gap-2">
            <ShieldExclamationIcon className="mt-0.5 h-4 w-4 shrink-0 text-warning-600" />
            <div className="min-w-0">
              <p className="text-sm font-semibold text-warning-800 dark:text-warning-300">
                {primer.alerts.length === 1
                  ? '1 starter needs attention'
                  : `${primer.alerts.length} starters need attention`}
              </p>
              <ul className="mt-1 space-y-0.5 text-xs text-warning-700 dark:text-warning-300/90">
                {primer.alerts.map((alert) => (
                  <li key={alert.player}>
                    <span className="font-medium">{alert.player}</span> is {alert.status} in your{' '}
                    {alert.slot} slot
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {primer.best_swap && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-brand/5 p-3">
          <ArrowsRightLeftIcon className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
          <p className="text-sm text-fg">
            Start <span className="font-semibold">{primer.best_swap.start}</span> over{' '}
            <span className="font-semibold">{primer.best_swap.sit}</span> at{' '}
            {primer.best_swap.slot} —{' '}
            <span className="font-semibold text-brand tabular">
              +{primer.best_swap.gain.toFixed(1)}
            </span>{' '}
            projected.
          </p>
        </div>
      )}

      {primer.trash_talk && (
        <div className="mt-3 border-t border-border pt-3">
          <p className="text-sm italic leading-relaxed text-fg-muted">“{primer.trash_talk}”</p>
          <button
            type="button"
            onClick={copyTrashTalk}
            className="mt-2 inline-flex min-h-[2.25rem] items-center gap-1.5 rounded-lg px-2 text-xs font-semibold text-brand transition-colors hover:bg-brand/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ClipboardDocumentIcon className="h-4 w-4" />
            Copy for the group chat
          </button>
        </div>
      )}
    </Card>
  );
};
