import { describe, expect, it, vi, beforeEach } from 'vitest';

import { GameDayPage } from './GameDayPage';
import { GameCard } from '@/components/gameday/GameCard';
import { renderWithProviders, render, screen, within } from '@/test/render';
import { GameDay, GamedayGame, GamedayPlayer } from '@/types';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useParams: () => ({ leagueId: '1' }) };
});

vi.mock('@/hooks/useLeagues', () => ({
  useLeague: () => ({ data: { id: 1, name: 'The Sunday Scaries Dynasty' } }),
}));

const state = vi.hoisted(() => ({
  data: undefined as GameDay | undefined,
  isLoading: false,
  isError: false,
  error: undefined as { detail?: string } | undefined,
}));

vi.mock('@/hooks/useGameday', () => ({ useGameday: () => state }));

const player = (over: Partial<GamedayPlayer> = {}): GamedayPlayer => ({
  player_id: 1,
  name: 'Josh Allen',
  position: 'QB',
  slot: 'QB',
  team: 'BUF',
  projected: 22.5,
  points: 18.4,
  injury_status: null,
  game_state: 'in',
  ...over,
});

const game = (over: Partial<GamedayGame> = {}): GamedayGame => ({
  id: 'g1',
  state: 'in',
  detail: 'Q4 2:41',
  home: { abbr: 'MIA', name: 'Dolphins', score: '17' },
  away: { abbr: 'BUF', name: 'Bills', score: '24' },
  mine: [player()],
  theirs: [],
  why: 'You have Josh Allen',
  leverage: 100,
  ...over,
});

const dayOf = (over: Partial<GameDay> = {}): GameDay => ({
  week: 14,
  my_team: {
    name: 'Game of Throws',
    summary: {
      playing_now: 2, yet_to_play: 0, finished: 5,
      points: 120.4, points_in_play: 30.2, projected_total: 150.6,
    },
    players: [player()],
  },
  opponent: {
    name: 'Comeback Cats',
    summary: {
      playing_now: 1, yet_to_play: 3, finished: 3,
      points: 98.1, points_in_play: 62.5, projected_total: 160.6,
    },
    players: [player({ name: 'Joe Burrow' })],
  },
  games: [game()],
  slate_size: 16,
  ...over,
});

const show = (day?: GameDay, flags: Partial<typeof state> = {}) => {
  state.data = day;
  state.isLoading = false;
  state.isError = !day && !flags.isLoading;
  state.error = undefined;
  Object.assign(state, flags);
  return renderWithProviders(<GameDayPage />);
};

beforeEach(() => {
  state.data = undefined;
  state.isLoading = false;
  state.isError = false;
  state.error = undefined;
});

describe('GameDayPage', () => {
  it('leads with both scores', () => {
    show(dayOf());
    // The row holding both columns, found via the "vs" separator between them.
    const scoreboard = screen.getByText('vs').parentElement!;

    expect(within(scoreboard).getByText('120.4')).toBeInTheDocument();
    expect(within(scoreboard).getByText('98.1')).toBeInTheDocument();
    expect(within(scoreboard).getByText('Game of Throws')).toBeInTheDocument();
    // Also a column label on every game card, hence the scope.
    expect(within(scoreboard).getByText('Comeback Cats')).toBeInTheDocument();
  });

  it('shows how many each side has left, which is what settles the argument', () => {
    // A lead with nobody left to play is a loss; the scoreline alone hides that.
    show(dayOf());
    expect(screen.getByText('Yet to play')).toBeInTheDocument();
    expect(screen.getByText('Playing now')).toBeInTheDocument();
  });

  it('reports how much is still in play for each side', () => {
    show(dayOf());
    expect(screen.getByText(/30\.2 still in play/)).toBeInTheDocument();
    expect(screen.getByText(/62\.5 still in play/)).toBeInTheDocument();
  });

  it('counts the live games in the header', () => {
    show(dayOf());
    expect(screen.getByText(/1 of your games is live right now/)).toBeInTheDocument();
  });

  it('says plainly when nothing has kicked off', () => {
    show(dayOf({ games: [game({ state: 'pre', detail: 'Sun 4:05 PM ET' })] }));
    expect(screen.getByText(/Nothing kicked off right now/)).toBeInTheDocument();
  });

  it('groups games by whether they are live, upcoming or done', () => {
    show(dayOf({
      games: [
        game({ id: 'a', state: 'in' }),
        game({ id: 'b', state: 'pre' }),
        game({ id: 'c', state: 'post', detail: 'Final' }),
      ],
    }));

    expect(screen.getByText('Watch now')).toBeInTheDocument();
    expect(screen.getByText('Still to come')).toBeInTheDocument();
    expect(screen.getByText('Finished')).toBeInTheDocument();
  });

  it('omits a group with no games in it', () => {
    show(dayOf({ games: [game({ state: 'in' })] }));
    expect(screen.queryByText('Finished')).toBeNull();
  });

  it('explains an empty slate', () => {
    show(dayOf({ games: [], slate_size: 0 }));
    expect(screen.getByText(/slate isn't up yet/i)).toBeInTheDocument();
  });

  it('distinguishes an empty slate from nobody playing in it', () => {
    show(dayOf({ games: [], slate_size: 16 }));
    expect(screen.getByText(/None of your starters or theirs/i)).toBeInTheDocument();
  });

  it('handles a bye week with no opponent', () => {
    show(dayOf({ opponent: null }));
    expect(screen.getByText(/No opponent this week/)).toBeInTheDocument();
  });

  it('asks you to claim a team when the API says so', () => {
    show(undefined, {
      isError: true,
      error: { detail: 'Claim your team first to see game day.' },
    });
    expect(screen.getByText(/Claim your team first/)).toBeInTheDocument();
  });

  it('shows placeholders while loading', () => {
    const { container } = show(undefined, { isLoading: true });
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });
});

describe('GameCard', () => {
  it('shows the scoreline and the clock', () => {
    render(<GameCard game={game()} />);
    expect(screen.getByText('BUF')).toBeInTheDocument();
    expect(screen.getByText('MIA')).toBeInTheDocument();
    expect(screen.getByText(/Live · Q4 2:41/)).toBeInTheDocument();
  });

  it('hides the score before kickoff and shows the time instead', () => {
    render(<GameCard game={game({ state: 'pre', detail: 'Sun 4:05 PM ET' })} />);
    expect(screen.getByText('Sun 4:05 PM ET')).toBeInTheDocument();
    expect(screen.queryByText('24')).toBeNull();
  });

  it('splits the players by whose they are', () => {
    render(
      <GameCard
        game={game({ theirs: [player({ name: 'Joe Burrow', slot: 'QB' })] })}
        opponentName="Comeback Cats"
      />
    );

    expect(screen.getByText('Yours')).toBeInTheDocument();
    expect(screen.getByText('Comeback Cats')).toBeInTheDocument();
    expect(screen.getByText('Josh Allen')).toBeInTheDocument();
    expect(screen.getByText('Joe Burrow')).toBeInTheDocument();
  });

  it('says "Nobody" rather than leaving a side blank', () => {
    render(<GameCard game={game({ theirs: [] })} />);
    expect(screen.getByText('Nobody')).toBeInTheDocument();
  });

  it('shows points against projection while a game is running', () => {
    render(<GameCard game={game()} />);
    expect(screen.getByText('18.4')).toBeInTheDocument();
    expect(screen.getByText('/22.5')).toBeInTheDocument();
  });

  it('drops the projection once a game is final', () => {
    // Nothing is pending any more, so the number to the right is noise.
    render(<GameCard game={game({ state: 'post', detail: 'Final', mine: [player({ game_state: 'post' })] })} />);
    expect(screen.getByText('18.4')).toBeInTheDocument();
    expect(screen.queryByText('/22.5')).toBeNull();
  });

  it('strikes through a player who has been ruled out', () => {
    render(
      <GameCard
        game={game({ mine: [player({ injury_status: 'OUT', game_state: 'pre' })] })}
      />
    );
    expect(screen.getByText('Josh Allen').className).toContain('line-through');
  });

  it('carries the reason the game matters', () => {
    render(<GameCard game={game({ why: 'You have 2 starters against their Joe Burrow' })} />);
    expect(
      screen.getByText('You have 2 starters against their Joe Burrow')
    ).toBeInTheDocument();
  });

  it('labels each player with his lineup slot', () => {
    render(<GameCard game={game({ mine: [player({ slot: 'FLEX' })] })} />);
    expect(screen.getByText('FLEX')).toBeInTheDocument();
  });
});
