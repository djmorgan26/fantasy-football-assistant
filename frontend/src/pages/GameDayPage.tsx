import React from 'react';
import { useParams } from 'react-router-dom';
import { BoltIcon, SignalIcon } from '@heroicons/react/24/outline';

import { PageContainer, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { LiveStatus } from '@/components/ui/LiveStatus';
import { PullToRefresh } from '@/components/ui/PullToRefresh';
import { Skeleton } from '@/components/ui/Skeleton';
import { ToolHeader } from '@/components/ui/ToolHeader';
import { GameCard } from '@/components/gameday/GameCard';
import { useLeague } from '@/hooks/useLeagues';
import { useGameday } from '@/hooks/useGameday';
import { GamedaySide } from '@/types';
import { cn } from '@/utils';

/**
 * Sunday afternoon.
 *
 * The headline is not the score — it is how many players each side has left.
 * A twenty-point lead with nobody left to play is a loss, and that is the fact
 * a scoreboard cannot tell you.
 */
const Scoreboard: React.FC<{ mine: GamedaySide; theirs: GamedaySide | null }> = ({
  mine,
  theirs,
}) => {
  const leading = theirs ? mine.summary.points > theirs.summary.points : true;

  const Column: React.FC<{ side: GamedaySide; me?: boolean }> = ({ side, me }) => (
    <div className={cn('min-w-0 flex-1', !me && 'text-right')}>
      <div className="truncate text-sm font-medium text-fg">{side.name}</div>
      <div
        className={cn(
          'font-display text-3xl font-bold tabular sm:text-4xl',
          me && leading ? 'text-brand' : 'text-fg'
        )}
      >
        {side.summary.points.toFixed(1)}
      </div>
      <div className="mt-0.5 text-xs text-fg-subtle tabular">
        {side.summary.points_in_play.toFixed(1)} still in play
      </div>
    </div>
  );

  return (
    <Card>
      <div className="flex items-start justify-between gap-3 sm:gap-6">
        <Column side={mine} me />
        <div className="shrink-0 pt-1 text-center text-[0.625rem] font-semibold uppercase tracking-wide text-fg-subtle sm:text-xs">
          vs
        </div>
        {theirs ? (
          <Column side={theirs} />
        ) : (
          <div className="flex-1 text-right text-sm text-fg-subtle">No opponent this week</div>
        )}
      </div>

      {/* The line that actually settles the argument. */}
      {theirs && (
        <div className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-4 text-center">
          {(
            [
              ['Playing now', mine.summary.playing_now, theirs.summary.playing_now],
              ['Yet to play', mine.summary.yet_to_play, theirs.summary.yet_to_play],
              ['Done', mine.summary.finished, theirs.summary.finished],
            ] as const
          ).map(([label, m, t]) => (
            <div key={label}>
              <div className="font-display text-lg font-bold tabular">
                <span className={cn(m > t ? 'text-brand' : 'text-fg')}>{m}</span>
                <span className="mx-1 text-fg-subtle">·</span>
                <span className="text-fg-muted">{t}</span>
              </div>
              <div className="mt-0.5 text-xs text-fg-muted">{label}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

export const GameDayPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = parseInt(leagueId || '0', 10);

  const { data: league } = useLeague(id);
  const { data, isLoading, isError, error, refetch, isFetching, dataUpdatedAt } =
    useGameday(id);

  const live = data?.games.filter((g) => g.state === 'in') ?? [];
  const upcoming = data?.games.filter((g) => g.state === 'pre') ?? [];
  const finished = data?.games.filter((g) => g.state === 'post') ?? [];

  // Only the very first load blanks the page. A poll or a pull updates the
  // numbers in place, because throwing a scoreboard back to its skeletons
  // every thirty seconds is unreadable.
  const firstLoad = isLoading && !data;

  const body = (
    <>
      <PageHeader
        backTo={`/leagues/${id}`}
        backLabel="Back to League"
        title="Game Day"
        subtitle={`Who you have on the field, who they have, and which games decide it${
          league?.name ? ` · ${league.name}` : ''
        }`}
      />

      {!firstLoad && (
        <LiveStatus
          className="mb-4"
          updatedAt={dataUpdatedAt}
          refreshing={isFetching}
          live={live.length > 0}
          liveLabel={`${live.length} ${live.length === 1 ? 'game' : 'games'} live`}
          onRefresh={() => void refetch()}
        />
      )}

      {firstLoad ? (
        <div className="space-y-4">
          <Skeleton className="h-40 w-full rounded-card" />
          <Skeleton className="h-52 w-full rounded-card" />
        </div>
      ) : isError || !data ? (
        <Card>
          <EmptyState
            icon={BoltIcon}
            title="Nothing to show yet"
            description={
              error?.detail || 'Claim your team in this league and game day will fill in.'
            }
            action={<Button onClick={() => void refetch()}>Try again</Button>}
          />
        </Card>
      ) : (
        <>
          <ToolHeader
            className="mb-4"
            icon={SignalIcon}
            title="Game Day"
            context={`Week ${data.week}`}
            subtitle={
              live.length
                ? `${live.length} of your games ${live.length === 1 ? 'is' : 'are'} live right now`
                : 'Nothing kicked off right now'
            }
          />

          <Scoreboard mine={data.my_team} theirs={data.opponent} />

          {data.games.length === 0 ? (
            <Card className="mt-6">
              <EmptyState
                icon={BoltIcon}
                title="Nobody is playing"
                description={
                  data.slate_size === 0
                    ? "The NFL slate isn't up yet. Check back closer to kickoff."
                    : 'None of your starters or theirs are in a game right now.'
                }
              />
            </Card>
          ) : (
            <div className="mt-6 space-y-6">
              {[
                ['Watch now', live] as const,
                ['Still to come', upcoming] as const,
                ['Finished', finished] as const,
              ]
                .filter(([, games]) => games.length > 0)
                .map(([label, games]) => (
                  <section key={label}>
                    <h2 className="mb-3 flex items-center gap-2 font-display text-lg font-bold text-fg">
                      {label}
                      <span className="text-sm font-medium text-fg-subtle tabular">
                        {games.length}
                      </span>
                    </h2>
                    <div className="space-y-3">
                      {games.map((game) => (
                        <GameCard
                          key={game.id}
                          game={game}
                          opponentName={data.opponent?.name}
                        />
                      ))}
                    </div>
                  </section>
                ))}
            </div>
          )}

          <p className="mt-6 text-center text-xs text-fg-subtle">
            Games nobody in this matchup is playing in are hidden. Pull down to refresh;
            scores update on their own every {live.length ? '30 seconds' : 'couple of minutes'}.
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
