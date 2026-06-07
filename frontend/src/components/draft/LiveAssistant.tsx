import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { useDraftAssist, useDraftAdvice } from '@/hooks/useDraft';
import { DraftAdvice, DraftPickRecommendation } from '@/types';
import { cn, getPositionColor } from '@/utils';
import {
  BoltIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  FireIcon,
} from '@heroicons/react/24/outline';

interface LiveAssistantProps {
  leagueId: number;
}

export const LiveAssistant: React.FC<LiveAssistantProps> = ({ leagueId }) => {
  const [live, setLive] = useState(true);
  const { data, isLoading, error, refetch, isFetching } = useDraftAssist(leagueId, live);
  const adviceMutation = useDraftAdvice(leagueId);
  const [advice, setAdvice] = useState<DraftAdvice | null>(null);

  const handleGetAdvice = async () => {
    const result = await adviceMutation.mutateAsync();
    if (result.ai_advice) setAdvice(result.ai_advice);
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <EmptyState
          icon={ExclamationTriangleIcon}
          title="No active draft found"
          description={
            error?.detail ||
            "We couldn't find a draft for this league yet. Once your Sleeper draft is created, recommendations will appear here live."
          }
        />
      </Card>
    );
  }

  const runs = Object.entries(data.positional_runs || {}).filter(([, n]) => n >= 2);

  return (
    <div className="space-y-5">
      {data.live_pick_tracking === false && data.note && (
        <div className="rounded-lg border border-border bg-surface-sunken p-3 text-sm text-fg-muted">
          {data.note}
        </div>
      )}

      {/* Status bar */}
      <Card
        className={cn(
          data.on_the_clock && 'ring-2 ring-accent bg-accent/10 border-accent'
        )}
      >
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <Stat label="Round" value={data.round ?? '—'} />
            <Stat label="Pick" value={data.current_pick ?? '—'} />
            {data.on_the_clock ? (
              <div className="flex items-center text-accent font-bold text-lg">
                <BoltIcon className="h-6 w-6 mr-1.5" />
                YOU'RE ON THE CLOCK
              </div>
            ) : (
              <Stat
                label="Your next pick"
                value={
                  data.next_user_pick
                    ? `#${data.next_user_pick} (${data.picks_until_next} away)`
                    : '—'
                }
              />
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setLive((v) => !v)}
              className={cn(
                'inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                live ? 'bg-success-100 text-success-800' : 'bg-surface-sunken text-fg-muted'
              )}
            >
              <span
                className={cn(
                  'h-2 w-2 rounded-full mr-2',
                  live ? 'bg-success-500 animate-pulse' : 'bg-fg-subtle'
                )}
              />
              {live ? 'Live' : 'Paused'}
            </button>
            <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isFetching}>
              <ArrowPathIcon className={cn('h-4 w-4', isFetching && 'animate-spin')} />
            </Button>
          </div>
        </div>

        {runs.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border flex items-center flex-wrap gap-2">
            <span className="flex items-center text-sm font-medium text-fg-muted">
              <FireIcon className="h-4 w-4 mr-1 text-accent" />
              Position run:
            </span>
            {runs.map(([pos, n]) => (
              <Badge key={pos} variant="warning" size="sm">
                {n} {pos} in last 8 picks
              </Badge>
            ))}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Recommendations */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Best Available</span>
                <Button
                  size="sm"
                  onClick={handleGetAdvice}
                  loading={adviceMutation.isLoading}
                >
                  <SparklesIcon className="h-4 w-4 mr-1.5" />
                  AI advice
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div aria-live="polite">
                {advice && <AdvicePanel advice={advice} />}
                <div className="space-y-2">
                  {data.recommendations.map((p, i) => (
                    <RecommendationRow key={p.player_id} player={p} rank={i + 1} />
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Your roster */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Your Roster</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.entries(data.user_position_counts)
                  .filter(([, n]) => n > 0)
                  .map(([pos, n]) => (
                    <span
                      key={pos}
                      className={cn(
                        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
                        getPositionColor(pos)
                      )}
                    >
                      {pos} {n}
                    </span>
                  ))}
              </div>
              {data.user_roster.length === 0 ? (
                <p className="text-sm text-fg-muted">No picks yet.</p>
              ) : (
                <ul className="space-y-1.5 text-sm">
                  {data.user_roster.map((pick, idx) => (
                    <li key={idx} className="flex items-center justify-between">
                      <span className="text-fg">{pick.name || 'Unknown'}</span>
                      <span className="text-fg-subtle tabular">
                        {pick.position} {pick.round ? `· R${pick.round}` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div>
    <div className="text-xs uppercase tracking-wide text-fg-muted">{label}</div>
    <div className="text-lg font-bold text-fg tabular">{value}</div>
  </div>
);

const RecommendationRow: React.FC<{ player: DraftPickRecommendation; rank: number }> = ({
  player,
  rank,
}) => (
  <div className="flex items-center gap-3 p-2.5 rounded-lg border border-border hover:bg-surface-sunken">
    <span className="w-6 text-center text-sm font-semibold text-fg-subtle tabular">{rank}</span>
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold',
        getPositionColor(player.position)
      )}
    >
      {player.position}
    </span>
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        <span className="font-medium text-fg truncate">{player.name}</span>
        {player.is_value && (
          <Badge variant="success" size="sm">
            VALUE
          </Badge>
        )}
        {player.injury_status && (
          <Badge variant="error" size="sm">
            {player.injury_status}
          </Badge>
        )}
      </div>
      <div className="text-xs text-fg-muted tabular">
        {player.team || 'FA'} · {player.projected_points.toFixed(1)} proj
        {player.adp ? ` · ADP ${player.adp}` : ''}
      </div>
    </div>
    <div className="text-right">
      <div className="text-sm font-bold text-success-600 tabular">
        {(player.pick_score ?? player.vbd).toFixed(0)}
      </div>
      <div className="text-[10px] uppercase tracking-wide text-fg-subtle">score</div>
    </div>
  </div>
);

const AdvicePanel: React.FC<{ advice: DraftAdvice }> = ({ advice }) => (
  <div className="mb-4 p-4 rounded-lg bg-brand/10 border border-brand/20">
    <div className="flex items-center text-brand font-semibold mb-1">
      <SparklesIcon className="h-4 w-4 mr-1.5" />
      AI recommends: {advice.recommended_player || '—'}
    </div>
    <p className="text-sm text-fg">{advice.reasoning}</p>
    {advice.alternatives?.length > 0 && (
      <p className="text-xs text-fg-muted mt-2">
        Alternatives: {advice.alternatives.join(', ')}
      </p>
    )}
    {advice.strategy_note && (
      <p className="text-xs text-fg-muted mt-1 italic">{advice.strategy_note}</p>
    )}
  </div>
);
