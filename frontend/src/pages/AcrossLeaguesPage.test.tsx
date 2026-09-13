import { describe, expect, it, vi, beforeEach } from 'vitest';

import { AcrossLeaguesPage } from './AcrossLeaguesPage';
import { renderWithProviders, screen, within } from '@/test/render';
import { LeagueWeek, PlayerConflict, PlayerExposure, Portfolio } from '@/types';

const state = vi.hoisted(() => ({
  data: undefined as Portfolio | undefined,
  isLoading: false,
  isError: false,
  error: undefined as { detail?: string } | undefined,
}));

vi.mock('@/hooks/usePortfolio', () => ({ usePortfolio: () => state }));

const week = (over: Partial<LeagueWeek> = {}): LeagueWeek => ({
  league_id: 1,
  league: 'The Sunday Scaries (ESPN)',
  platform: 'espn',
  week: 14,
  team: 'Game of Throws',
  record: '9-4',
  opponent: 'Comeback Cats',
  points: 120.4,
  opponent_points: 98.1,
  projected: 150.0,
  opponent_projected: 120.0,
  margin: 30.0,
  status: 'comfortable',
  alerts: [],
  ...over,
});

const conflict = (over: Partial<PlayerConflict> = {}): PlayerConflict => ({
  name: 'Josh Allen',
  position: 'QB',
  team: 'BUF',
  player_id: 1,
  for: [{ league_id: 1, league: 'ESPN League', team: 'Game of Throws', starting: true,
          slot: 'QB', projected: 22.5, points: 18.4 }],
  against: [{ league_id: 2, league: 'Sleeper League', team: 'Pain Train', starting: true,
              slot: 'QB', projected: 22.5, points: 18.4 }],
  for_count: 1,
  against_count: 1,
  net: 0,
  verdict: 'a genuine wash',
  ...over,
});

const exposure = (over: Partial<PlayerExposure> = {}): PlayerExposure => ({
  name: 'Christian McCaffrey',
  position: 'RB',
  team: 'SF',
  player_id: 2,
  for: [
    { league_id: 1, league: 'ESPN League', team: 'A', starting: true, slot: 'RB',
      projected: 20, points: 15 },
    { league_id: 2, league: 'Sleeper League', team: 'B', starting: true, slot: 'RB',
      projected: 20, points: 15 },
  ],
  against: [],
  leagues: 2,
  starting_in: 2,
  projected: 40,
  ...over,
});

const portfolio = (over: Partial<Portfolio> = {}): Portfolio => ({
  leagues: 2,
  teams: 2,
  unclaimed: [],
  weeks: [week()],
  conflicts: [conflict()],
  exposure: [exposure()],
  totals: { points: 240.8, projected: 300, winning: 2, alerts: 0 },
  ...over,
});

const show = (data?: Portfolio, flags: Partial<typeof state> = {}) => {
  state.data = data;
  state.isLoading = false;
  state.isError = false;
  state.error = undefined;
  Object.assign(state, flags);
  return renderWithProviders(<AcrossLeaguesPage />);
};

beforeEach(() => {
  state.data = undefined;
  state.isLoading = false;
  state.isError = false;
  state.error = undefined;
});

describe('AcrossLeaguesPage', () => {
  it('leads with the conflicts, because nobody spots those alone', () => {
    show(portfolio());
    expect(screen.getByText('Rooting for and against')).toBeInTheDocument();
    expect(screen.getByText('Josh Allen')).toBeInTheDocument();
    expect(screen.getByText('a genuine wash')).toBeInTheDocument();
  });

  it('names both sides of a conflict', () => {
    show(portfolio());
    // Scoped to the conflict card: the team name also appears in the week list.
    const card = screen.getByTestId('conflict-card');

    expect(within(card).getByText('You have him')).toBeInTheDocument();
    expect(within(card).getByText('Against him')).toBeInTheDocument();
    expect(within(card).getByText(/Game of Throws/)).toBeInTheDocument();
    expect(within(card).getByText(/Pain Train/)).toBeInTheDocument();
  });

  it('counts the conflicts in the header', () => {
    show(portfolio());
    expect(screen.getByText(/1 player is on both sides/)).toBeInTheDocument();
  });

  it('says so when nobody is playing both sides', () => {
    show(portfolio({ conflicts: [] }));
    expect(screen.getByText(/Nobody is playing both sides/)).toBeInTheDocument();
    expect(screen.queryByText('Rooting for and against')).toBeNull();
  });

  it('ignores a holding where the player is benched', () => {
    // A bench player is doing nothing to anybody, so he should not be listed.
    show(portfolio({
      conflicts: [conflict({
        against: [{ league_id: 2, league: 'Sleeper League', team: 'Pain Train',
                    starting: false, slot: 'BN', projected: 0, points: 0 }],
      })],
    }));
    expect(screen.queryByText(/Pain Train/)).toBeNull();
  });

  it('lists every league week', () => {
    show(portfolio({
      conflicts: [],   // keep the team names unique to the week list
      weeks: [week({ league_id: 1 }), week({ league_id: 2, team: 'Pain Train' })],
    }));
    expect(screen.getByText('Game of Throws')).toBeInTheDocument();
    expect(screen.getByText('Pain Train')).toBeInTheDocument();
  });

  it('shows the margin and how safe it is', () => {
    show(portfolio());
    expect(screen.getByText(/\+30\.0 · Comfortable/)).toBeInTheDocument();
  });

  it('flags a week that is behind', () => {
    show(portfolio({ weeks: [week({ margin: -20, status: 'behind' })] }));
    expect(screen.getByText(/-20\.0 · Behind/)).toBeInTheDocument();
  });

  it('surfaces lineup problems per league', () => {
    show(portfolio({
      weeks: [week({ alerts: [{ player: 'A.J. Brown', slot: 'WR', status: 'OUT' }] })],
    }));
    expect(screen.getByText(/A\.J\. Brown \(OUT\)/)).toBeInTheDocument();
  });

  it('links each week to its league', () => {
    show(portfolio());
    expect(screen.getByRole('link', { name: /Game of Throws/ })).toHaveAttribute(
      'href',
      '/leagues/1'
    );
  });

  it('shows how many of your teams start an exposed player', () => {
    show(portfolio());
    const panel = screen.getByText('Most exposed').closest('div')!.parentElement!;
    expect(within(panel).getByText('Christian McCaffrey')).toBeInTheDocument();
    expect(within(panel).getByText('2/2')).toBeInTheDocument();
  });

  it('says plainly when no player spans two teams', () => {
    show(portfolio({ exposure: [] }));
    expect(screen.getByText(/No player is on more than one of your teams/)).toBeInTheDocument();
  });

  it('explains which leagues are missing and why', () => {
    // A league quietly absent from this page is worse than one named.
    show(portfolio({ unclaimed: [{ league_id: 9, name: 'Work League' }] }));
    expect(screen.getByText(/Not shown: Work League/)).toBeInTheDocument();
  });

  it('asks you to connect a league when there are none', () => {
    show(portfolio({ leagues: 0, teams: 0, weeks: [], conflicts: [], exposure: [] }));
    expect(screen.getByText('No leagues connected')).toBeInTheDocument();
  });

  it('asks you to claim a team when leagues exist but none are claimed', () => {
    show(portfolio({ leagues: 2, teams: 0, weeks: [], conflicts: [], exposure: [] }));
    expect(screen.getByText('No teams claimed yet')).toBeInTheDocument();
  });

  it('shows placeholders while loading', () => {
    const { container } = show(undefined, { isLoading: true });
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('reports a failure rather than rendering an empty page', () => {
    show(undefined, { isError: true, error: { detail: 'Upstream is down' } });
    expect(screen.getByText('Upstream is down')).toBeInTheDocument();
  });
});
