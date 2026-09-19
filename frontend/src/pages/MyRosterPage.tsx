import React, { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLeague } from '@/hooks/useLeagues';
import { useLeagueTeams, useTeamRoster } from '@/hooks/useTeams';
import { useCurrentMatchup } from '@/hooks/useMatchups';
import { useCurrentUser } from '@/hooks/useAuth';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import { Progress } from '@/components/ui/Progress';
import { Skeleton, SkeletonList } from '@/components/ui/Skeleton';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import { PlayerAvatar } from '@/components/ui/PlayerAvatar';
import { ToolHeader } from '@/components/ui/ToolHeader';
import { PrimerCard } from '@/components/assistant/PrimerCard';
import { getPositionColor } from '@/utils';
import { RosterPlayer } from '@/types';
import {
  ArrowTopRightOnSquareIcon,
  ArrowTrendingUpIcon,
  ClipboardDocumentListIcon,
  ExclamationTriangleIcon,
  QueueListIcon,
  ShieldExclamationIcon,
} from '@heroicons/react/24/outline';

/** Statuses that mean a player will not or may not take the field. */
const UNAVAILABLE = ['OUT', 'INJURY_RESERVE', 'IR', 'SUSPENSION'];
const DOUBTFUL = ['DOUBTFUL', 'QUESTIONABLE'];

/** Short, readable label for an ESPN injury status. */
const injuryLabel = (status?: string) => {
  switch (status) {
    case 'INJURY_RESERVE':
      return 'IR';
    case 'QUESTIONABLE':
      return 'Q';
    case 'DOUBTFUL':
      return 'D';
    case 'OUT':
      return 'OUT';
    case 'SUSPENSION':
      return 'SUSP';
    case 'PROBABLE':
      return 'P';
    default:
      return null;
  }
};

/** How a status reads inside a sentence: "A.J. Brown is on injured reserve". */
const injuryPhrase = (status?: string) => {
  switch (status) {
    case 'INJURY_RESERVE':
    case 'IR':
      return 'on injured reserve';
    case 'OUT':
      return 'ruled out';
    case 'SUSPENSION':
      return 'suspended';
    case 'DOUBTFUL':
      return 'doubtful';
    case 'QUESTIONABLE':
      return 'questionable';
    default:
      return 'not at full strength';
  }
};

const injuryTone = (status?: string): 'error' | 'warning' | 'default' => {
  if (!status) return 'default';
  if (UNAVAILABLE.includes(status)) return 'error';
  if (DOUBTFUL.includes(status)) return 'warning';
  return 'default';
};

const initials = (name: string) =>
  name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

const pts = (n?: number | null) => (n ?? 0).toFixed(1);

/**
 * One player line. Used for starters, bench and IR so a player reads the same
 * everywhere: who they are on the left, what they are worth on the right.
 */
const PlayerRow: React.FC<{
  player: RosterPlayer;
  slotLabel: string;
  dimmed?: boolean;
  flag?: string;
  /** Narrow column layout: identity and one number, nothing that would wrap. */
  compact?: boolean;
}> = ({ player, slotLabel, dimmed, flag, compact }) => {
  const status = player.injury_status;
  const label = injuryLabel(status);
  const tone = injuryTone(status);
  const scored = (player.applied_points ?? 0) > 0;

  return (
    <div
      className={`flex items-center rounded-lg border border-border transition-all hover:bg-surface-sunken hover:shadow-elevation-3 ${
        compact ? 'gap-2 p-2' : 'gap-2 p-2.5 sm:gap-3 sm:p-3'
      } ${dimmed ? 'bg-surface-sunken/50' : 'bg-surface-raised'}`}
    >
      {/* Lineup slot rail */}
      <div className={`shrink-0 text-center ${compact ? 'w-9' : 'w-9 sm:w-12'}`}>
        <span
          className={`inline-block w-full rounded-md px-1 py-1 text-xs font-semibold ${getPositionColor(
            slotLabel
          )}`}
        >
          {slotLabel}
        </span>
      </div>

      {/* The headshot is the first thing to go on a narrow screen: it costs
          48px that the player's name needs more. */}
      {!compact && (
        <PlayerAvatar
          name={player.full_name}
          playerId={player.player_id}
          position={player.position_name}
          className="hidden sm:flex"
        />
      )}

      {/* Identity */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span
            className={`truncate font-semibold text-fg ${compact ? 'text-sm' : ''}`}
          >
            {player.full_name}
          </span>
          {label && (
            <Badge variant={tone === 'default' ? 'secondary' : tone} size="sm">
              {label}
            </Badge>
          )}
        </div>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-fg-muted">
          <span className="font-medium">{player.position_name}</span>
          <span aria-hidden>•</span>
          <span>{player.pro_team_abbr || 'FA'}</span>
          {!compact && !!player.positional_ranking && (
            <span className="hidden items-center gap-1.5 sm:flex">
              <span aria-hidden>•</span>
              <span>
                {player.position_name} #{player.positional_ranking}
              </span>
            </span>
          )}
          {!compact && !!player.percent_owned && (
            <span className="hidden items-center gap-1.5 md:flex">
              <span aria-hidden>•</span>
              <span className="tabular">{player.percent_owned.toFixed(0)}% rostered</span>
            </span>
          )}
        </div>
        {flag && (
          <div className="mt-1 flex items-start gap-1 text-xs font-medium text-warning-700 dark:text-warning-400">
            <ArrowTrendingUpIcon className="mt-0.5 h-3 w-3 shrink-0" />
            <span>{flag}</span>
          </div>
        )}
      </div>

      {/* Numbers */}
      {compact ? (
        <div className="w-12 shrink-0 text-right">
          <div className="font-display text-base font-bold tabular text-brand">
            {pts(player.projected_points)}
          </div>
          <div className="text-[10px] uppercase tracking-wide text-fg-subtle">
            {scored ? `${pts(player.applied_points)} pts` : 'proj'}
          </div>
        </div>
      ) : (
        <div className="flex shrink-0 items-center gap-2.5 text-right sm:gap-4">
          <div className="w-11 sm:w-12">
            <div
              className={`font-display text-base font-bold tabular ${
                scored ? 'text-fg' : 'text-fg-subtle'
              }`}
            >
              {pts(player.applied_points)}
            </div>
            <div className="text-[10px] uppercase tracking-wide text-fg-subtle">pts</div>
          </div>
          <div className="w-11 sm:w-12">
            <div className="font-display text-base font-bold tabular text-brand">
              {pts(player.projected_points)}
            </div>
            <div className="text-[10px] uppercase tracking-wide text-fg-subtle">proj</div>
          </div>
          <div className="hidden w-14 md:block">
            <div className="font-display text-base font-bold tabular text-fg-muted">
              {pts(player.season_points)}
            </div>
            <div className="text-[10px] uppercase tracking-wide text-fg-subtle">season</div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatTile: React.FC<{
  label: string;
  value: string;
  hint?: string;
  accent?: boolean;
  className?: string;
}> = ({ label, value, hint, accent, className }) => (
  <div className={`rounded-lg bg-surface-sunken p-3 text-center sm:p-4 ${className ?? ''}`}>
    <div
      className={`font-display text-xl font-bold tabular sm:text-2xl ${
        accent ? 'text-brand' : 'text-fg'
      }`}
    >
      {value}
    </div>
    <div className="mt-1 text-xs text-fg-muted sm:text-sm">{label}</div>
    {hint && <div className="mt-0.5 text-xs text-fg-subtle">{hint}</div>}
  </div>
);

export const MyRosterPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const numericLeagueId = parseInt(leagueId || '0', 10);
  const { data: league } = useLeague(numericLeagueId);
  const { data: teams, isLoading: teamsLoading } = useLeagueTeams(numericLeagueId);
  const { data: currentUser, isLoading: userLoading } = useCurrentUser();

  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const week = selectedWeek ?? league?.current_week ?? 1;

  const userTeam = teams?.find((team) => team.owner_user_id === currentUser?.id);

  const { data: rosterData, isLoading: rosterLoading } = useTeamRoster(userTeam?.id || 0, week);
  // The matchups endpoint reports our own database team ids, not ESPN's, so the
  // lookup uses userTeam.id. espn_team_id is only for links back to ESPN.
  const { opponent, myScore } = useCurrentMatchup(numericLeagueId, userTeam?.id || 0, week);

  const { starters, bench, injuredReserve, startCandidates, totals } = useMemo(() => {
    // Derived in here rather than above: `rosterData?.roster || []` is a fresh
    // array identity on every render, which defeated this memo entirely.
    const players: RosterPlayer[] = rosterData?.roster || [];
    const starters = players.filter((p) => p.is_starter);
    const bench = players.filter((p) => !p.is_starter && !p.on_injured_reserve);
    const injuredReserve = players.filter((p) => p.on_injured_reserve);

    // A bench player is worth flagging when they out-project the weakest
    // starter they could actually replace: same position, or the flex.
    const flexible = ['RB', 'WR', 'TE'];
    const startCandidates = new Map<number, string>();
    bench.forEach((b) => {
      const replaceable = starters.filter(
        (s) =>
          s.position_name === b.position_name ||
          (s.lineup_slot_name === 'FLEX' && flexible.includes(b.position_name))
      );
      if (!replaceable.length) return;
      const weakest = replaceable.reduce((low, s) =>
        (s.projected_points ?? 0) < (low.projected_points ?? 0) ? s : low
      );
      const gain = (b.projected_points ?? 0) - (weakest.projected_points ?? 0);
      // Ignore a player who cannot play and trivial differences.
      if (gain > 0.5 && !UNAVAILABLE.includes(b.injury_status || '')) {
        startCandidates.set(
          b.player_id,
          `+${gain.toFixed(1)} proj over ${weakest.full_name}`
        );
      }
    });

    const sum = (list: RosterPlayer[], key: 'applied_points' | 'projected_points') =>
      list.reduce((acc, p) => acc + (p[key] ?? 0), 0);

    return {
      starters,
      bench,
      injuredReserve,
      startCandidates,
      totals: {
        actual: sum(starters, 'applied_points'),
        projected: sum(starters, 'projected_points'),
        benchActual: sum(bench, 'applied_points'),
      },
    };
  }, [rosterData]);

  // Starters who cannot play, or might not. The single most useful thing this
  // page can tell you before kickoff.
  const lineupAlerts = starters.filter((p) =>
    [...UNAVAILABLE, ...DOUBTFUL].includes(p.injury_status || '')
  );

  const espnTeamUrl =
    league?.espn_league_id && userTeam?.espn_team_id
      ? `https://fantasy.espn.com/football/team?leagueId=${league.espn_league_id}&teamId=${userTeam.espn_team_id}&seasonId=${league.season_year}`
      : null;

  // Which team is mine is the answer this whole page is built on, and it takes
  // two requests to work out. Until both land there is no honest thing to say:
  // rendering the "no team" state in the meantime told every visitor they had
  // not claimed a team, a second before showing them their roster.
  if (teamsLoading || userLoading) {
    return (
      <PageContainer>
        <div className="mb-6 space-y-3">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
        </div>
        <Skeleton className="mb-6 h-28 w-full rounded-card" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <SkeletonList rows={6} />
          </div>
          <SkeletonList rows={3} height="h-24" />
        </div>
      </PageContainer>
    );
  }

  if (!userTeam) {
    return (
      <PageContainer>
        <Card>
          <EmptyState
            icon={ExclamationTriangleIcon}
            title="No Team Selected"
            description="Please select your team first to view your roster."
            action={
              <Link to={`/leagues/${leagueId}`}>
                <Button>Back to League</Button>
              </Link>
            }
          />
        </Card>
      </PageContainer>
    );
  }

  const totalWeekPoints = myScore ?? totals.actual;
  const opponentScore = opponent?.score ?? 0;
  const combined = totalWeekPoints + opponentScore;
  const sharePct = combined > 0 ? (totalWeekPoints / combined) * 100 : 50;

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${leagueId}`}
        backLabel="Back to League"
        title="My Roster"
        subtitle={`${userTeam.name} • ${league?.name}`}
        media={
          userTeam.logo_url ? (
            <img
              src={userTeam.logo_url}
              alt=""
              className="h-11 w-11 rounded-full bg-surface-sunken object-cover sm:h-12 sm:w-12"
            />
          ) : (
            <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-brand to-primary-700 text-sm font-bold text-brand-fg sm:h-12 sm:w-12">
              {initials(userTeam.name)}
            </div>
          )
        }
        actions={
          <>
            <Select
              value={String(week)}
              onChange={(v) => setSelectedWeek(parseInt(v, 10))}
              options={Array.from({ length: 18 }, (_, i) => ({
                value: String(i + 1),
                label: `Week ${i + 1}`,
              }))}
              className="w-32"
            />
            {espnTeamUrl && (
              <a href={espnTeamUrl} target="_blank" rel="noopener noreferrer">
                <Button variant="secondary" size="sm">
                  Set lineup on ESPN
                  <ArrowTopRightOnSquareIcon className="ml-1.5 h-4 w-4" />
                </Button>
              </a>
            )}
          </>
        }
      />

      {/* Scoreboard */}
      {opponent && (
        <Card className="mb-6">
          <CardContent>
            <div className="flex items-center justify-between gap-3 sm:gap-4">
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-fg">{userTeam.name}</div>
                <div className="font-display text-2xl font-bold tabular text-brand sm:text-3xl">
                  {pts(totalWeekPoints)}
                </div>
                <div className="text-xs text-fg-subtle">projected {pts(totals.projected)}</div>
              </div>
              <div className="shrink-0 text-center text-[0.625rem] font-semibold uppercase tracking-wide text-fg-subtle sm:text-xs">
                Week <br className="sm:hidden" />
                {week}
              </div>
              <div className="min-w-0 flex-1 text-right">
                <div className="truncate text-sm font-medium text-fg">{opponent.teamName}</div>
                <div className="font-display text-2xl font-bold tabular text-fg sm:text-3xl">
                  {pts(opponentScore)}
                </div>
                <div className="text-xs text-fg-subtle">opponent</div>
              </div>
            </div>
            <Progress
              value={sharePct}
              className="mt-4"
              label={`${userTeam.name} share of points scored`}
            />
          </CardContent>
        </Card>
      )}

      {/* Team stats */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Team Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-2 sm:gap-4 md:grid-cols-5">
            <StatTile
              label="Record"
              value={`${userTeam.wins}-${userTeam.losses}${
                userTeam.ties ? `-${userTeam.ties}` : ''
              }`}
            />
            <StatTile label="Points For" value={userTeam.points_for.toFixed(1)} hint="season" />
            <StatTile
              label={`Week ${week} Points`}
              value={pts(totals.actual)}
              hint="starters"
              accent
            />
            <StatTile label="Projected" value={pts(totals.projected)} hint="starters" />
            <StatTile
              label="On Bench"
              value={pts(totals.benchActual)}
              hint="points not started"
              className="col-span-2 md:col-span-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Lineup alerts */}
      {!rosterLoading && lineupAlerts.length > 0 && (
        <Card className="mb-6 border-warning-300 dark:border-warning-700">
          <CardContent>
            <div className="flex gap-3">
              <ShieldExclamationIcon className="h-5 w-5 shrink-0 text-warning-600" />
              <div>
                <h3 className="font-semibold text-fg">
                  {lineupAlerts.length === 1
                    ? '1 starter needs attention'
                    : `${lineupAlerts.length} starters need attention`}
                </h3>
                <ul className="mt-1 space-y-0.5 text-sm text-fg-muted">
                  {lineupAlerts.map((p) => (
                    <li key={p.player_id}>
                      <span className="font-medium text-fg">{p.full_name}</span> is{' '}
                      {injuryPhrase(p.injury_status)} in your {p.lineup_slot_name} slot
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Starting lineup */}
        <div className="lg:col-span-2">
          <ToolHeader
            className="mb-4"
            icon={ClipboardDocumentListIcon}
            title="Starting Lineup"
            context={`Week ${week}`}
            subtitle={`${starters.length} ${starters.length === 1 ? 'starter' : 'starters'} · ${league?.scoring_type ?? ''} scoring`}
          />
          <Card data-testid="starters-panel">
            <CardContent>
              {rosterLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 9 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full rounded-lg" />
                  ))}
                </div>
              ) : starters.length ? (
                <div className="space-y-2">
                  {starters.map((player) => (
                    <PlayerRow
                      key={player.player_id}
                      player={player}
                      slotLabel={player.lineup_slot_name}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={QueueListIcon}
                  title="No lineup for this week"
                  description="ESPN has no roster data for the week you selected."
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Bench, IR, and the week's briefing */}
        <div className="space-y-6">
          <PrimerCard leagueId={numericLeagueId} />

          <Card data-testid="bench-panel">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center">
                  <QueueListIcon className="mr-2 h-5 w-5" />
                  Bench
                </CardTitle>
                <span className="text-sm text-fg-muted">{bench.length}</span>
              </div>
            </CardHeader>
            <CardContent>
              {rosterLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full rounded-lg" />
                  ))}
                </div>
              ) : bench.length ? (
                <div className="space-y-2">
                  {bench.map((player) => (
                    <PlayerRow
                      key={player.player_id}
                      player={player}
                      slotLabel={player.position_name}
                      dimmed
                      compact
                      flag={startCandidates.get(player.player_id)}
                    />
                  ))}
                </div>
              ) : (
                <p className="py-4 text-center text-sm text-fg-muted">Nobody on the bench.</p>
              )}
            </CardContent>
          </Card>

          {injuredReserve.length > 0 && (
            <Card data-testid="ir-panel">
              <CardHeader>
                <CardTitle className="flex items-center">
                  <ShieldExclamationIcon className="mr-2 h-5 w-5" />
                  Injured Reserve
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {injuredReserve.map((player) => (
                    <PlayerRow
                      key={player.player_id}
                      player={player}
                      slotLabel="IR"
                      dimmed
                      compact
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </PageContainer>
  );
};
