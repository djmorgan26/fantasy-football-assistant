import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowsRightLeftIcon,
  BoltIcon,
  ChevronDownIcon,
  ExclamationTriangleIcon,
  RectangleStackIcon,
  Square3Stack3DIcon,
} from '@heroicons/react/24/outline';

import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { LiveStatus } from '@/components/ui/LiveStatus';
import { PlatformBadge } from '@/components/ui/PlatformBadge';
import { PlayerAvatar } from '@/components/ui/PlayerAvatar';
import { PullToRefresh } from '@/components/ui/PullToRefresh';
import { Skeleton } from '@/components/ui/Skeleton';
import { ToolHeader } from '@/components/ui/ToolHeader';
import { CrossLeagueGameCard } from '@/components/gameday/CrossLeagueGameCard';
import { usePortfolio } from '@/hooks/usePortfolio';
import { PlayerConflict, PlayerExposure, LeagueWeek, Portfolio, SlateGame } from '@/types';
import { cn } from '@/utils';

/**
 * Everything you own, across every league.
 *
 * Two questions live here. The first is the conflict: the same player on your
 * roster in one league and on your opponent's in another, where every point he
 * scores helps you and hurts you at once. The second is the one people
 * actually open the app to ask on a Sunday — *what is happening right now?* —
 * which used to mean picking a league and opening its Game Day, one at a time.
 * Both are answered on this one screen.
 */
const STATUS_TONE: Record<LeagueWeek['status'], string> = {
  comfortable: 'text-brand',
  tight: 'text-warning-600 dark:text-warning-400',
  behind: 'text-error-600 dark:text-error-400',
};

const STATUS_LABEL: Record<LeagueWeek['status'], string> = {
  comfortable: 'Comfortable',
  tight: 'Tight',
  behind: 'Behind',
};

const WeekRow: React.FC<{ week: LeagueWeek }> = ({ week }) => (
  <Link
    to={`/leagues/${week.league_id}`}
    className="block rounded-lg border border-border p-3 transition-colors hover:border-border-strong hover:bg-surface-sunken focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
  >
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
      <div className="flex min-w-0 items-center gap-2">
        {week.platform && <PlatformBadge platform={week.platform} size="sm" />}
        <span className="truncate font-semibold text-fg">{week.team}</span>
        <span className="shrink-0 text-xs text-fg-subtle tabular">({week.record})</span>
      </div>
      <span className={cn('shrink-0 text-sm font-semibold', STATUS_TONE[week.status])}>
        {week.margin > 0 ? '+' : ''}
        {week.margin.toFixed(1)} · {STATUS_LABEL[week.status]}
      </span>
    </div>

    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-fg-muted">
      <span className="truncate">vs {week.opponent ?? 'nobody this week'}</span>
      <span className="tabular">
        {week.points.toFixed(1)} – {week.opponent_points.toFixed(1)}
      </span>
    </div>

    {week.alerts.length > 0 && (
      <div className="mt-1.5 flex items-start gap-1.5 text-xs text-warning-700 dark:text-warning-400">
        <ExclamationTriangleIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          {week.alerts.map((a) => `${a.player} (${a.status})`).join(', ')}
        </span>
      </div>
    )}
  </Link>
);

const Holdings: React.FC<{ label: string; rows: PlayerConflict['for']; tone: 'for' | 'against' }> = ({
  label,
  rows,
  tone,
}) => {
  const starting = rows.filter((r) => r.starting);
  if (starting.length === 0) return null;

  return (
    <div className="min-w-0">
      <div
        className={cn(
          'text-[11px] font-bold uppercase tracking-wider',
          tone === 'for' ? 'text-brand' : 'text-error-600 dark:text-error-400'
        )}
      >
        {label}
      </div>
      <ul className="mt-0.5 space-y-0.5">
        {starting.map((row) => (
          <li key={`${row.league_id}-${row.team}`} className="truncate text-sm text-fg-muted">
            {row.team} <span className="text-fg-subtle">· {row.league}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};

const ConflictCard: React.FC<{ player: PlayerConflict }> = ({ player }) => (
  <div
    data-testid="conflict-card"
    className="rounded-lg border border-accent/40 border-l-4 border-l-accent bg-surface-raised p-3"
  >
    <div className="flex items-center gap-3">
      <PlayerAvatar
        name={player.name}
        playerId={typeof player.player_id === 'number' ? player.player_id : undefined}
        position={player.position}
      />
      <div className="min-w-0 flex-1">
        <div className="truncate font-semibold text-fg">{player.name}</div>
        <div className="text-xs text-fg-subtle">
          {player.position} · {player.team || 'FA'}
        </div>
      </div>
      <span className="shrink-0 rounded-pill bg-accent/15 px-2.5 py-1 text-xs font-semibold text-accent">
        {player.verdict}
      </span>
    </div>

    <div className="mt-3 grid grid-cols-1 gap-3 border-t border-border pt-3 sm:grid-cols-2">
      <Holdings label="You have him" rows={player.for} tone="for" />
      <Holdings label="Against him" rows={player.against} tone="against" />
    </div>
  </div>
);

const ExposureRow: React.FC<{ player: PlayerExposure }> = ({ player }) => (
  <li className="flex items-center gap-3">
    <PlayerAvatar
      name={player.name}
      playerId={typeof player.player_id === 'number' ? player.player_id : undefined}
      position={player.position}
      size="sm"
    />
    <div className="min-w-0 flex-1">
      <div className="truncate text-sm font-semibold text-fg">{player.name}</div>
      <div className="truncate text-xs text-fg-subtle">
        {player.for.map((f) => f.league).join(' · ')}
      </div>
    </div>
    <div className="shrink-0 text-right">
      <div className="font-display text-sm font-bold text-fg tabular">
        {player.starting_in}/{player.leagues}
      </div>
      <div className="text-[10px] uppercase tracking-wide text-fg-subtle">starting</div>
    </div>
  </li>
);

/**
 * One section of the slate, with the games inside it.
 *
 * Only the first group is open. Across four leagues the full slate runs to a
 * dozen cards, and a page you have to scroll past nine kickoff times to read
 * is not a page about what is happening right now.
 */
const SlateGroup: React.FC<{ label: string; games: SlateGame[]; open: boolean }> = ({
  label,
  games,
  open,
}) => {
  const [expanded, setExpanded] = useState(open);

  return (
    <section>
      <button
        type="button"
        onClick={() => setExpanded((was) => !was)}
        aria-expanded={expanded}
        className="mb-3 flex w-full items-center gap-2 rounded-lg py-1 text-left font-display text-base font-bold text-fg transition-colors hover:text-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ChevronDownIcon
          aria-hidden
          className={cn(
            'h-4 w-4 text-fg-subtle transition-transform',
            !expanded && '-rotate-90'
          )}
        />
        {label}
        <span className="text-sm font-medium text-fg-subtle tabular">{games.length}</span>
      </button>

      {expanded && (
        <div className="space-y-3">
          {games.map((game) => (
            <CrossLeagueGameCard key={game.id} game={game} />
          ))}
        </div>
      )}
    </section>
  );
};

/**
 * Game Day, for every league at once.
 *
 * Grouped the way an afternoon actually runs — what is on now, what is coming,
 * what is settled — because the first group is the only one anybody looks at
 * while a game is being played.
 */
const RightNow: React.FC<{ data: Portfolio }> = ({ data }) => {
  const groups = (
    [
      ['Watch now', data.games.filter((g) => g.state === 'in')],
      ['Still to come', data.games.filter((g) => g.state === 'pre')],
      ['Finished', data.games.filter((g) => g.state === 'post')],
    ] as const
  ).filter(([, games]) => games.length > 0);

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BoltIcon className="h-5 w-5 text-accent" />
          Right now
        </CardTitle>
        <p className="mt-1 text-sm text-fg-muted">
          Every NFL game with somebody of yours in it, from any league. The ones that
          decide the most come first.
        </p>
      </CardHeader>
      <CardContent>
        {data.games.length === 0 ? (
          <EmptyState
            icon={BoltIcon}
            title="Nobody is playing"
            description={
              data.slate_size === 0
                ? "The NFL slate isn't up yet. Check back closer to kickoff."
                : 'None of your starters, in any league, are in a game on the slate.'
            }
          />
        ) : (
          <div className="space-y-6">
            {groups.map(([label, games], i) => (
              <SlateGroup key={label} label={label} games={games} open={i === 0} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export const AcrossLeaguesPage: React.FC = () => {
  const { data, isLoading, isError, error, refetch, isFetching, dataUpdatedAt } =
    usePortfolio();

  const live = data?.live;
  const liveGames = live?.games ?? 0;

  // The first load shows skeletons; every load after that keeps the page on
  // screen and says "Updating…" instead, so a poll never blanks a scoreboard
  // somebody is reading.
  const firstLoad = isLoading && !data;

  const body = (
    <>
      <PageHeader
        title="Across Leagues"
        subtitle="Every team you run, the games on right now, and the players pulling in two directions at once"
      />

      {!firstLoad && (
        <LiveStatus
          className="mb-4"
          updatedAt={dataUpdatedAt}
          refreshing={isFetching}
          live={liveGames > 0}
          liveLabel={`${liveGames} ${liveGames === 1 ? 'game' : 'games'} live`}
          onRefresh={() => void refetch()}
        />
      )}

      {firstLoad ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-card" />
          <Skeleton className="h-52 w-full rounded-card" />
          <Skeleton className="h-52 w-full rounded-card" />
        </div>
      ) : isError || !data ? (
        <Card>
          <EmptyState
            icon={Square3Stack3DIcon}
            variant="error"
            title="Couldn't pull your leagues together"
            description={error?.detail || 'Try again in a moment.'}
            action={<Button onClick={() => void refetch()}>Try again</Button>}
          />
        </Card>
      ) : data.teams === 0 ? (
        <Card>
          <EmptyState
            icon={Square3Stack3DIcon}
            title={data.leagues === 0 ? 'No leagues connected' : 'No teams claimed yet'}
            description={
              data.leagues === 0
                ? 'Connect an ESPN or Sleeper league and this fills in.'
                : 'Claim your team in each league and this page can compare them.'
            }
            action={
              <Link to="/leagues">
                <Button>Go to your leagues</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <>
          <ToolHeader
            className="mb-4"
            icon={Square3Stack3DIcon}
            title="Across Leagues"
            context={`${data.teams} ${data.teams === 1 ? 'team' : 'teams'}`}
            subtitle={
              liveGames > 0
                ? `${live?.playing_now ?? 0} of your players ${
                    (live?.playing_now ?? 0) === 1 ? 'is' : 'are'
                  } on the field right now`
                : data.conflicts.length > 0
                ? `${data.conflicts.length} ${
                    data.conflicts.length === 1 ? 'player is' : 'players are'
                  } on both sides of your week`
                : 'Nobody is playing both sides of your week'
            }
          />

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(
              [
                ['Playing now', String(live?.playing_now ?? 0)],
                ['Yet to play', String(live?.yet_to_play ?? 0)],
                ['Points', data.totals.points.toFixed(1)],
                ['Still in play', (live?.points_in_play ?? 0).toFixed(1)],
              ] as const
            ).map(([label, value]) => (
              <div key={label} className="rounded-lg bg-surface-sunken p-3 text-center">
                <div className="font-display text-xl font-bold text-fg tabular">{value}</div>
                <div className="mt-0.5 text-xs text-fg-muted">{label}</div>
              </div>
            ))}
          </div>

          {/* What is happening right now comes first: it is the reason to have
              this screen open on a Sunday at all. */}
          <RightNow data={data} />

          {/* Conflicts next — they are the thing nobody notices on their own. */}
          {data.conflicts.length > 0 && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ArrowsRightLeftIcon className="h-5 w-5 text-accent" />
                  Rooting for and against
                </CardTitle>
                <p className="mt-1 text-sm text-fg-muted">
                  You start these players in one league and play against them in another.
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {data.conflicts.map((player) => (
                    <ConflictCard key={player.name} player={player} />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Your week, everywhere</CardTitle>
                  <p className="mt-1 text-sm text-fg-muted">
                    Closest matchup first — that is the one that needs you.
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2.5">
                    {data.weeks.map((week) => (
                      <WeekRow key={week.league_id} week={week} />
                    ))}
                  </div>

                  {data.unclaimed.length > 0 && (
                    <p className="mt-4 border-t border-border pt-3 text-xs text-fg-subtle">
                      Not shown: {data.unclaimed.map((u) => u.name).join(', ')} — claim your
                      team there to include {data.unclaimed.length === 1 ? 'it' : 'them'}.
                    </p>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <RectangleStackIcon className="h-5 w-5 text-brand" />
                  Most exposed
                </CardTitle>
                <p className="mt-1 text-sm text-fg-muted">
                  Own him in several leagues and a bad Sunday hurts more than once.
                </p>
              </CardHeader>
              <CardContent>
                {data.exposure.length === 0 ? (
                  <p className="text-sm text-fg-muted">
                    No player is on more than one of your teams.
                  </p>
                ) : (
                  <ul className="space-y-3">
                    {data.exposure.slice(0, 8).map((player) => (
                      <ExposureRow key={player.name} player={player} />
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <p className="mt-6 text-center text-xs text-fg-subtle">
            Pull down to refresh. Scores update on their own every {liveGames > 0 ? '30 seconds' : 'couple of minutes'}.
          </p>
        </>
      )}
    </>
  );

  return (
    <PullToRefresh onRefresh={() => refetch()} refreshing={isFetching}>
      <PageContainer>{body}</PageContainer>
    </PullToRefresh>
  );
};
