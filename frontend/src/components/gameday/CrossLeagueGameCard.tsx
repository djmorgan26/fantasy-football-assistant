import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowsRightLeftIcon } from '@heroicons/react/24/outline';

import { Card } from '@/components/ui/Card';
import { SlateGame, SlateHolding, SlatePlayer } from '@/types';
import { cn } from '@/utils';

const STATE_LABEL: Record<string, string> = {
  in: 'Live',
  pre: 'Upcoming',
  post: 'Final',
};

const UNAVAILABLE = ['OUT', 'INJURY_RESERVE', 'IR', 'SUSPENSION'];

/**
 * Which leagues this player is playing for, and which he is playing against.
 *
 * On a single-league card the answer is implicit and the slot is enough. Here
 * it is the whole point: the only way to know whether to cheer is to know
 * which of your teams he is on.
 */
const Stakes: React.FC<{ rows: SlateHolding[]; tone: 'for' | 'against' }> = ({
  rows,
  tone,
}) => (
  <>
    {rows.map((row) => (
      <Link
        key={`${tone}-${row.league_id}`}
        to={`/leagues/${row.league_id}/gameday`}
        className={cn(
          // Capped so a long league name cannot push a row to two lines on a
          // phone; the full name is in the title.
          'inline-flex max-w-[11rem] items-center gap-1 rounded-pill px-2 py-0.5 text-[11px] font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          tone === 'for'
            ? 'bg-brand/10 text-brand hover:bg-brand/20'
            : 'bg-error-100 text-error-700 hover:bg-error-200 dark:bg-error-900/40 dark:text-error-300 dark:hover:bg-error-900/60'
        )}
        title={`${tone === 'for' ? 'Starting for' : 'Against'} ${row.team} · ${row.league}`}
      >
        {row.slot && <span className="shrink-0 opacity-70">{row.slot}</span>}
        <span className="truncate">{row.league}</span>
      </Link>
    ))}
  </>
);

const PlayerRow: React.FC<{ player: SlatePlayer }> = ({ player }) => {
  const done = player.game_state === 'post';
  const unavailable =
    player.injury_status && UNAVAILABLE.includes(player.injury_status);

  return (
    <li
      data-testid="slate-player"
      className={cn(
        'flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-lg px-2 py-1.5',
        player.conflict && 'bg-accent/10'
      )}
    >
      <span
        className={cn(
          'min-w-0 flex-1 truncate text-sm font-medium',
          unavailable ? 'text-fg-subtle line-through' : 'text-fg'
        )}
      >
        {player.name}
        <span className="ml-1.5 text-xs font-normal text-fg-subtle">{player.position}</span>
      </span>

      <span
        className={cn(
          'shrink-0 font-display text-sm font-bold tabular',
          done ? 'text-fg' : 'text-fg-muted'
        )}
        title={done ? 'Final points' : 'Points so far'}
      >
        {player.points.toFixed(1)}
      </span>
      {!done && (
        <span className="w-10 shrink-0 text-right text-[11px] text-fg-subtle tabular">
          /{player.projected.toFixed(1)}
        </span>
      )}

      <div className="flex w-full flex-wrap items-center gap-1">
        {player.conflict && (
          <span
            className="inline-flex items-center gap-1 rounded-pill bg-accent/20 px-2 py-0.5 text-[11px] font-semibold text-accent"
            title="You start him in one league and play against him in another"
          >
            <ArrowsRightLeftIcon className="h-3 w-3" aria-hidden />
            Both ways
          </span>
        )}
        <Stakes rows={player.for} tone="for" />
        <Stakes rows={player.against} tone="against" />
      </div>
    </li>
  );
};

/**
 * One NFL game, told across every league you are in at once.
 *
 * The single-league version splits the card down the middle: yours on the
 * left, theirs on the right. That split does not survive contact with four
 * leagues, where the same man can be on both sides. So this is one list, and
 * each player carries the leagues he is playing for and against as chips.
 */
export const CrossLeagueGameCard: React.FC<{ game: SlateGame }> = ({ game }) => {
  const live = game.state === 'in';
  const awayScore = Number(game.away.score ?? 0);
  const homeScore = Number(game.home.score ?? 0);

  return (
    <Card
      className={cn('transition-shadow', live && 'border-l-4 border-l-accent shadow-elevation-2')}
    >
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="flex items-center gap-3">
          {(['away', 'home'] as const).map((side, i) => {
            const team = game[side];
            const score = side === 'away' ? awayScore : homeScore;
            const other = side === 'away' ? homeScore : awayScore;
            const winning = game.state !== 'pre' && score > other;
            return (
              <React.Fragment key={side}>
                {i === 1 && <span className="text-xs text-fg-subtle">at</span>}
                <span className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      'font-display text-sm font-bold',
                      winning ? 'text-fg' : 'text-fg-muted'
                    )}
                  >
                    {team.abbr}
                  </span>
                  {game.state !== 'pre' && (
                    <span
                      className={cn(
                        'font-display text-base font-bold tabular',
                        winning ? 'text-fg' : 'text-fg-muted'
                      )}
                    >
                      {score}
                    </span>
                  )}
                </span>
              </React.Fragment>
            );
          })}
        </div>

        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-xs font-semibold',
            live ? 'bg-accent/15 text-accent' : 'bg-surface-sunken text-fg-muted'
          )}
        >
          {live && (
            <span
              aria-hidden
              className="h-1.5 w-1.5 rounded-full bg-accent motion-safe:animate-pulse"
            />
          )}
          {game.state === 'pre' ? game.detail : `${STATE_LABEL[game.state]} · ${game.detail}`}
        </span>
      </div>

      {game.why && <p className="mt-2 text-sm text-fg-muted">{game.why}</p>}

      <ul className="mt-3 space-y-1 border-t border-border pt-3">
        {game.players.map((player) => (
          <PlayerRow key={`${player.player_id}-${player.name}`} player={player} />
        ))}
      </ul>
    </Card>
  );
};
