import React from 'react';
import { ArrowsRightLeftIcon, LightBulbIcon } from '@heroicons/react/24/outline';
import { Badge, Button, Card, CardContent, LoadingSpinner } from '@/components/ui';
import { CounterLikelihood, CounterOffer, CounterResult, TradePlayer } from '@/types';

const KIND_LABEL: Record<string, string> = {
  ask_for_more: 'Ask for more',
  different_target: 'Different target',
  give_less: 'Give up less',
  different_piece: 'Different piece',
  swap_both: 'Swap both sides',
};

/**
 * How likely they are to take it, coloured by how big an ask it is.
 *
 * The scale is relative to the offer they themselves made, which is the only
 * baseline that means anything here: they have already shown what they will
 * part with, so "no worse for them than their own offer" is genuinely easy and
 * everything else is a negotiation.
 */
const LIKELIHOOD: Record<
  CounterLikelihood,
  { label: string; variant: 'success' | 'default' | 'warning' | 'error' }
> = {
  easy_ask: { label: 'Easy ask', variant: 'success' },
  fair_ask: { label: 'Fair ask', variant: 'default' },
  big_ask: { label: 'Big ask', variant: 'warning' },
  unlikely: { label: 'Long shot', variant: 'error' },
};

export const CounterOffers: React.FC<{
  result?: CounterResult | null;
  isLoading: boolean;
  onExplore: () => void;
  onAnalyze: (counter: CounterOffer) => void;
}> = ({ result, isLoading, onExplore, onAnalyze }) => {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 pt-6">
          <LoadingSpinner size="sm" />
          <span className="text-sm text-fg-muted">
            Building counters off both rosters…
          </span>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <h3 className="flex items-center gap-2 text-base font-semibold text-fg">
                <LightBulbIcon className="h-5 w-5 text-brand" aria-hidden="true" />
                Not sure? Explore counters
              </h3>
              <p className="mt-1 text-sm text-fg-muted">
                See what else you could ask for, and how likely they'd be to take it.
              </p>
            </div>
            <Button variant="secondary" onClick={onExplore}>
              Explore counters
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="space-y-4 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h3 className="flex items-center gap-2 text-base font-semibold text-fg">
            <LightBulbIcon className="h-5 w-5 text-brand" aria-hidden="true" />
            Counter-offers
          </h3>
          <Button variant="ghost" onClick={onExplore} className="shrink-0">
            Rerun
          </Button>
        </div>

        <p className="text-sm text-fg-muted">{result.summary}</p>

        {result.ai_summary && (
          <div className="rounded-lg border border-border bg-surface-sunken p-3">
            <p className="text-sm text-fg">{result.ai_summary}</p>
          </div>
        )}

        {result.counters.length > 0 && (
          <ul className="space-y-3">
            {result.counters.map((counter, index) => (
              <li key={`${counter.kind}-${index}`}>
                <CounterCard counter={counter} onAnalyze={onAnalyze} />
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
};

const CounterCard: React.FC<{
  counter: CounterOffer;
  onAnalyze: (counter: CounterOffer) => void;
}> = ({ counter, onAnalyze }) => {
  const odds = LIKELIHOOD[counter.likelihood] ?? LIKELIHOOD.fair_ask;

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge variant="default" size="sm">
          {KIND_LABEL[counter.kind] ?? counter.kind}
        </Badge>
        <Badge variant={odds.variant} size="sm">
          {odds.label}
        </Badge>
        <span className="tabular ml-auto text-xs font-semibold text-success-600 dark:text-success-400">
          {counter.gain_vs_original >= 0 ? '+' : ''}
          {counter.gain_vs_original.toFixed(1)}/wk vs accepting
        </span>
      </div>

      <p className="mb-3 text-sm text-fg">{counter.rationale}</p>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <Side label="You give" players={counter.give} />
        <div className="flex justify-center">
          <ArrowsRightLeftIcon
            className="h-4 w-4 rotate-90 text-fg-muted sm:rotate-0"
            aria-hidden="true"
          />
        </div>
        <Side label="You get" players={counter.receive} />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Button variant="ghost" onClick={() => onAnalyze(counter)}>
          Analyze this
        </Button>
        <span className="text-xs text-fg-muted">{counter.likelihood_reason}</span>
      </div>
    </div>
  );
};

const Side: React.FC<{ label: string; players: TradePlayer[] }> = ({
  label,
  players,
}) => (
  <div className="rounded bg-surface-sunken p-2">
    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-fg-muted">
      {label}
    </p>
    <ul className="space-y-1">
      {players.map((player) => (
        <li key={player.player_id} className="flex items-center gap-2">
          <span className="w-8 shrink-0 rounded bg-surface-raised px-1 text-center text-[10px] font-bold text-fg-muted">
            {player.position}
          </span>
          <span className="min-w-0 flex-1 truncate text-sm text-fg">
            {player.full_name}
          </span>
          <span className="tabular shrink-0 text-xs text-fg-muted">
            {player.projected_points.toFixed(1)}
          </span>
        </li>
      ))}
    </ul>
  </div>
);
