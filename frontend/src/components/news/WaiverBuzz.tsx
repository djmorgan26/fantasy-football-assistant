import React from 'react';
import { ArrowTrendingUpIcon } from '@heroicons/react/24/outline';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { PlayerAvatar } from '@/components/ui/PlayerAvatar';
import { Skeleton } from '@/components/ui/Skeleton';
import { useTrending } from '@/hooks/useNews';

/**
 * Who the rest of the fantasy world is adding right now.
 *
 * The counts come from Sleeper's whole user base, so they are a far stronger
 * waiver signal than any single site's projections: it is what millions of
 * managers are actually doing in the last 24 hours, and the number is not
 * arguable.
 */
export const WaiverBuzz: React.FC<{ limit?: number }> = ({ limit = 6 }) => {
  const { data: players, isLoading } = useTrending('add');

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Waiver buzz</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!players || players.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ArrowTrendingUpIcon className="h-5 w-5 text-accent" />
          Waiver buzz
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-2">
          {players.slice(0, limit).map((player) => (
            <li key={player.sleeper_id} className="flex items-center gap-3">
              <PlayerAvatar
                name={player.name}
                src={player.headshot}
                position={player.position}
                size="sm"
              />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold text-fg">{player.name}</div>
                <div className="text-xs text-fg-subtle">
                  {player.position} · {player.team || 'FA'}
                </div>
              </div>
              <div className="shrink-0 text-right">
                <div className="font-display text-sm font-bold text-accent tabular">
                  {player.count.toLocaleString()}
                </div>
                <div className="text-[10px] uppercase tracking-wide text-fg-subtle">adds</div>
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-fg-subtle">Adds across Sleeper in the last 24 hours.</p>
      </CardContent>
    </Card>
  );
};
