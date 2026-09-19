import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { AcrossLeaguesPage } from './AcrossLeaguesPage';
import { CrossLeagueGameCard } from '@/components/gameday/CrossLeagueGameCard';
import { renderWithProviders, screen, within } from '@/test/render';
import {
  LeagueWeek,
  PlayerConflict,
  PlayerExposure,
  Portfolio,
  SlateGame,
  SlatePlayer,
} from '@/types';

const state = vi.hoisted(() => ({
  data: undefined as Portfolio | undefined,
  isLoading: false,
  isError: false,
  error: undefined as { detail?: string } | undefined,
  isFetching: false,
  dataUpdatedAt: 0,
  refetch: vi.fn(() => Promise.resolve()),
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

const holding = (over: Partial<SlatePlayer['for'][number]> = {}) => ({
  league_id: 1,
  league: 'ESPN League',
  team: 'Game of Throws',
  slot: 'QB',
  points: 18.4,
  projected: 22.5,
  ...over,
});

const slatePlayer = (over: Partial<SlatePlayer> = {}): SlatePlayer => ({
  name: 'Josh Allen',
  player_id: 1,
  position: 'QB',
  team: 'BUF',
  injury_status: null,
  game_state: 'in',
  points: 18.4,
  projected: 22.5,
  for: [holding()],
  against: [],
  conflict: false,
  ...over,
});

const slateGame = (over: Partial<SlateGame> = {}): SlateGame => ({
  id: 'g1',
  state: 'in',
  detail: 'Q4 2:41',
  home: { abbr: 'MIA', name: 'Dolphins', score: '17' },
  away: { abbr: 'BUF', name: 'Bills', score: '24' },
  players: [slatePlayer()],
  yours: 1,
  theirs: 0,
  conflicts: 0,
  why: '1 of yours',
  leverage: 100,
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
  games: [],
  live: {
    games: 0,
    playing_now: 0,
    yet_to_play: 0,
    theirs_playing_now: 0,
    points_in_play: 0,
  },
  slate_size: 0,
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
  state.isFetching = false;
  state.dataUpdatedAt = Date.now();
  state.refetch = vi.fn(() => Promise.resolve());
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

describe('AcrossLeaguesPage — what is happening right now', () => {
  const live = (over: Partial<Portfolio['live']> = {}): Portfolio['live'] => ({
    games: 1,
    playing_now: 1,
    yet_to_play: 2,
    theirs_playing_now: 1,
    points_in_play: 44.5,
    ...over,
  });

  it('shows the live games without making you pick a league first', () => {
    // The whole point: one screen for the whole Sunday.
    show(portfolio({ conflicts: [], games: [slateGame()], live: live(), slate_size: 16 }));

    expect(screen.getByText('Right now')).toBeInTheDocument();
    expect(screen.getByText('Watch now')).toBeInTheDocument();
    expect(screen.getByText(/Josh Allen/)).toBeInTheDocument();
    expect(screen.getByText(/Live · Q4 2:41/)).toBeInTheDocument();
  });

  it('groups the slate the way an afternoon runs', () => {
    show(portfolio({
      conflicts: [],
      games: [
        slateGame({ id: 'a', state: 'in' }),
        slateGame({ id: 'b', state: 'pre', detail: 'Sun 4:05 PM ET' }),
        slateGame({ id: 'c', state: 'post', detail: 'Final' }),
      ],
      live: live(),
      slate_size: 16,
    }));

    expect(screen.getByText('Watch now')).toBeInTheDocument();
    expect(screen.getByText('Still to come')).toBeInTheDocument();
    expect(screen.getByText('Finished')).toBeInTheDocument();
  });

  it('opens only the first group, so the live games are not below nine kickoff times', async () => {
    show(portfolio({
      conflicts: [],
      games: [
        slateGame({ id: 'a', state: 'in' }),
        slateGame({
          id: 'b',
          state: 'pre',
          detail: 'Sun 4:05 PM ET',
          players: [slatePlayer({ name: 'Bijan Robinson' })],
        }),
      ],
      live: live(),
      slate_size: 16,
    }));

    expect(screen.getByText(/Josh Allen/)).toBeInTheDocument();
    expect(screen.queryByText(/Bijan Robinson/)).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: /Still to come/ }));
    expect(screen.getByText(/Bijan Robinson/)).toBeInTheDocument();
  });

  it('opens what is still to come when nothing has kicked off', async () => {
    show(portfolio({
      conflicts: [],
      games: [slateGame({ state: 'pre', detail: 'Sun 4:05 PM ET' })],
      live: live({ games: 0, playing_now: 0 }),
      slate_size: 16,
    }));

    expect(screen.getByText(/Josh Allen/)).toBeInTheDocument();
  });

  it('leads the header with the field, not the conflicts, once games are on', () => {
    show(portfolio({ games: [slateGame()], live: live({ playing_now: 3 }), slate_size: 16 }));
    expect(screen.getByText(/3 of your players are on the field right now/)).toBeInTheDocument();
  });

  it('counts your players on the field and the points still coming', () => {
    show(portfolio({ conflicts: [], games: [slateGame()], live: live(), slate_size: 16 }));
    expect(screen.getByText('Playing now')).toBeInTheDocument();
    expect(screen.getByText('Still in play')).toBeInTheDocument();
    expect(screen.getByText('44.5')).toBeInTheDocument();
  });

  it('explains an empty slate', () => {
    show(portfolio({ conflicts: [], games: [], slate_size: 0 }));
    expect(screen.getByText(/slate isn't up yet/i)).toBeInTheDocument();
  });

  it('distinguishes an empty slate from nobody of yours playing in it', () => {
    show(portfolio({ conflicts: [], games: [], slate_size: 16 }));
    expect(screen.getByText(/None of your starters, in any league/i)).toBeInTheDocument();
  });

  it('says how old the numbers on screen are', () => {
    show(portfolio());
    expect(screen.getByText(/Updated just now/)).toBeInTheDocument();
  });

  it('counts the live games beside the timestamp', () => {
    show(portfolio({ games: [slateGame()], live: live({ games: 2 }), slate_size: 16 }));
    expect(screen.getByText('2 games live')).toBeInTheDocument();
  });

  it('refetches when you ask it to', async () => {
    show(portfolio());
    await userEvent.click(screen.getByRole('button', { name: /refresh/i }));
    expect(state.refetch).toHaveBeenCalled();
  });

  it('keeps the page up while a refresh runs rather than blanking it', () => {
    const { container } = show(portfolio(), { isFetching: true });

    expect(screen.getByText('Your week, everywhere')).toBeInTheDocument();
    expect(screen.getByText('Updating…')).toBeInTheDocument();
    expect(container.querySelectorAll('.animate-pulse').length).toBe(0);
  });
});

describe('CrossLeagueGameCard', () => {
  it('names every league a player is in the game for', () => {
    // On one screen for four leagues, "who is he playing for" is the question.
    renderWithProviders(
      <CrossLeagueGameCard
        game={slateGame({
          players: [slatePlayer({
            for: [
              holding({ league_id: 1, league: 'ESPN League' }),
              holding({ league_id: 2, league: 'Sleeper League' }),
            ],
          })],
        })}
      />
    );

    expect(screen.getByText('ESPN League')).toBeInTheDocument();
    expect(screen.getByText('Sleeper League')).toBeInTheDocument();
  });

  it('marks a player who is on both sides of your Sunday', () => {
    renderWithProviders(
      <CrossLeagueGameCard
        game={slateGame({
          conflicts: 1,
          players: [slatePlayer({
            conflict: true,
            for: [holding({ league_id: 1, league: 'ESPN League' })],
            against: [holding({ league_id: 2, league: 'Sleeper League', team: 'Pain Train' })],
          })],
        })}
      />
    );

    expect(screen.getByText('Both ways')).toBeInTheDocument();
  });

  it('is one row per player, not one per league', () => {
    renderWithProviders(
      <CrossLeagueGameCard
        game={slateGame({
          players: [slatePlayer({
            conflict: true,
            for: [holding({ league_id: 1, league: 'ESPN League' })],
            against: [holding({ league_id: 2, league: 'Sleeper League' })],
          })],
        })}
      />
    );

    expect(screen.getAllByTestId('slate-player')).toHaveLength(1);
  });

  it("links a league chip to that league's game day", () => {
    renderWithProviders(<CrossLeagueGameCard game={slateGame()} />);
    expect(screen.getByRole('link', { name: /ESPN League/ })).toHaveAttribute(
      'href',
      '/leagues/1/gameday'
    );
  });

  it('shows points against projection while a game is running', () => {
    renderWithProviders(<CrossLeagueGameCard game={slateGame()} />);
    expect(screen.getByText('18.4')).toBeInTheDocument();
    expect(screen.getByText('/22.5')).toBeInTheDocument();
  });

  it('drops the projection once a game is final', () => {
    renderWithProviders(
      <CrossLeagueGameCard
        game={slateGame({
          state: 'post',
          detail: 'Final',
          players: [slatePlayer({ game_state: 'post' })],
        })}
      />
    );
    expect(screen.queryByText('/22.5')).toBeNull();
  });

  it('strikes through a player who has been ruled out', () => {
    renderWithProviders(
      <CrossLeagueGameCard
        game={slateGame({
          state: 'pre',
          players: [slatePlayer({ injury_status: 'OUT', game_state: 'pre' })],
        })}
      />
    );
    expect(screen.getByText(/Josh Allen/).className).toContain('line-through');
  });

  it('carries the reason the game matters', () => {
    renderWithProviders(<CrossLeagueGameCard game={slateGame({ why: '2 of yours · 1 cutting both ways' })} />);
    expect(screen.getByText('2 of yours · 1 cutting both ways')).toBeInTheDocument();
  });
});
