import React from 'react';

import { Card } from '@/components/ui/Card';
import { GamedayGame, GamedayPlayer } from '@/types';
import { cn } from '@/utils';

/**
 * One NFL game, told from the point of view of your matchup.
 *
 * A generic scoreboard shows the score. What matters on a Sunday is which of
 * these twenty-two players are yours and which belong to the person you are
 * playing, so the roster split is the body of the card and the score is the
 * header.
 */
const STATE_LABEL: Record<string, string> = {
  in: 'Live',
  pre: 'Upcoming',
  post: 'Final',
};

const PlayerLine: React.FC<{ player: GamedayPlayer; tone: 'mine' | 'theirs' }> = ({
  player,
  tone,
}) => {
  const done = player.game_state === 'post';
  const unavailable =
    player.injury_status && ['OUT', 'INJURY_RESERVE', 'IR', 'SUSPENSION'].includes(
      player.injury_status
    );

  return (
    <li className="flex items-baseline gap-2 text-sm">
      <span
        className={cn(
          'w-8 shrink-0 text-[10px] font-bold uppercase tracking-wide',
          tone === 'mine' ? 'text-brand' : 'text-fg-subtle'
        )}
      >
        {player.slot}
      </span>
      <span className={cn('min-w-0 flex-1 truncate', unavailable ? 'text-fg-subtle line-through' : 'text-fg')}>
        {player.name}
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
    </li>
  );
};

const Side: React.FC<{ label: string; players: GamedayPlayer[]; tone: 'mine' | 'theirs' }> = ({
  label,
  players,
  tone,
}) => (
  <div className="min-w-0">
    <h4
      className={cn(
        'mb-1.5 text-[11px] font-bold uppercase tracking-wider',
        tone === 'mine' ? 'text-brand' : 'text-fg-subtle'
      )}
    >
      {label}
    </h4>
    {players.length === 0 ? (
      <p className="text-sm text-fg-subtle">Nobody</p>
    ) : (
      <ul className="flex flex-col gap-1.5">
        {players.map((p) => (
          <PlayerLine key={`${p.player_id}-${p.name}`} player={p} tone={tone} />
        ))}
      </ul>
    )}
  </div>
);

interface GameCardProps {
  game: GamedayGame;
  opponentName?: string | null;
}

export const GameCard: React.FC<GameCardProps> = ({ game, opponentName }) => {
  const live = game.state === 'in';
  const awayScore = Number(game.away.score ?? 0);
  const homeScore = Number(game.home.score ?? 0);

  return (
    <Card
      className={cn(
        'transition-shadow',
        live && 'border-l-4 border-l-accent shadow-elevation-2'
      )}
    >
      {/* Scoreline */}
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
            live
              ? 'bg-accent/15 text-accent'
              : game.state === 'post'
              ? 'bg-surface-sunken text-fg-subtle'
              : 'bg-surface-sunken text-fg-muted'
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

      <div className="mt-4 grid grid-cols-1 gap-4 border-t border-border pt-4 sm:grid-cols-2">
        <Side label="Yours" players={game.mine} tone="mine" />
        <Side label={opponentName || 'Theirs'} players={game.theirs} tone="theirs" />
      </div>
    </Card>
  );
};
