import React from 'react';
import { ArrowsRightLeftIcon, ArrowDownTrayIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline';
import { Badge, Button, Card, CardContent } from '@/components/ui';
import { LeagueTrade, TradePlayer } from '@/types';
import { cn } from '@/utils';

const STATUS_LABEL: Record<string, string> = {
  proposed: 'Pending',
  executed: 'Completed',
  rejected: 'Rejected',
  vetoed: 'Vetoed',
};

const relativeTime = (iso?: string | null): string | null => {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return null;
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
};

/**
 * One trade, pending or historical.
 *
 * Laid out as two named sides rather than a generic list, because "who is
 * giving up what" is the first thing to understand and a flat list of players
 * does not say it. The `has_consented` flag drives the incoming/outgoing label:
 * on a proposed trade the proposer has always consented, so the side that has
 * not is the one being asked.
 */
export const OfferCard: React.FC<{
  trade: LeagueTrade;
  myTeamId: number | null;
  onAnalyze?: (trade: LeagueTrade) => void;
}> = ({ trade, myTeamId, onAnalyze }) => {
  const isPending = trade.status === 'proposed';
  const mine = trade.parties.find((p) => p.team_id === myTeamId);
  const others = trade.parties.filter((p) => p !== mine);

  // Show my side first when I am in the trade; otherwise keep platform order.
  const ordered = mine ? [mine, ...others] : trade.parties;
  const when = relativeTime(trade.proposed_at);

  const DirectionIcon =
    trade.direction === 'incoming'
      ? ArrowDownTrayIcon
      : trade.direction === 'outgoing'
      ? ArrowUpTrayIcon
      : ArrowsRightLeftIcon;

  return (
    <Card className={cn(isPending && trade.direction === 'incoming' && 'border-brand')}>
      <CardContent className="pt-5">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <DirectionIcon className="h-4 w-4 text-fg-muted" aria-hidden="true" />
          {trade.direction !== 'other' && (
            <Badge variant={trade.direction === 'incoming' ? 'success' : 'default'} size="sm">
              {trade.direction === 'incoming' ? 'Incoming' : 'Outgoing'}
            </Badge>
          )}
          <Badge variant={isPending ? 'warning' : 'default'} size="sm">
            {STATUS_LABEL[trade.status] ?? trade.status}
          </Badge>
          {when && <span className="ml-auto text-xs text-fg-muted">{when}</span>}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
          {ordered.map((party, index) => (
            <React.Fragment key={`${party.team_name}-${index}`}>
              {index > 0 && (
                <div className="flex justify-center py-1 sm:py-0">
                  <ArrowsRightLeftIcon
                    className="h-5 w-5 rotate-90 text-fg-muted sm:rotate-0"
                    aria-hidden="true"
                  />
                </div>
              )}
              <div className="rounded-lg border border-border bg-surface-sunken p-3">
                <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-fg-muted">
                  <span className="truncate">
                    {party.team_id === myTeamId ? 'You give' : `${party.team_name} gives`}
                  </span>
                  {isPending && party.has_consented && (
                    <span className="shrink-0 text-[10px] font-normal normal-case text-success-600">
                      accepted
                    </span>
                  )}
                </p>
                {party.sends.length > 0 ? (
                  <ul className="space-y-1.5">
                    {party.sends.map((player) => (
                      <PlayerRow key={player.player_id} player={player} />
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-fg-muted">Nothing</p>
                )}
              </div>
            </React.Fragment>
          ))}
        </div>

        {onAnalyze && mine && (
          <div className="mt-4">
            <Button variant="secondary" onClick={() => onAnalyze(trade)} className="w-full sm:w-auto">
              Analyze this offer
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const PlayerRow: React.FC<{ player: TradePlayer }> = ({ player }) => (
  <li className="flex items-center gap-2">
    <span className="w-9 shrink-0 rounded bg-surface-raised px-1 py-0.5 text-center text-[10px] font-bold text-fg-muted">
      {player.position}
    </span>
    <span className="min-w-0 flex-1 truncate text-sm font-medium text-fg">
      {player.full_name}
    </span>
    {player.projected_points > 0 && (
      <span className="tabular shrink-0 text-xs text-fg-muted">
        {player.projected_points.toFixed(1)}
      </span>
    )}
  </li>
);
