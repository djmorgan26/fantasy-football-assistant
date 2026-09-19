import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MyRosterPage } from './MyRosterPage';
import { RosterPlayer } from '@/types';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useParams: () => ({ leagueId: '1' }) };
});

const league = {
  id: 1,
  name: 'AEPI 2022',
  espn_league_id: 1725275280,
  season_year: 2026,
  current_week: 1,
};

// The database id and the ESPN id differ deliberately: matchups are keyed by
// the database id, while links back to ESPN need the ESPN id.
const myTeam = {
  id: 42,
  espn_team_id: 9,
  name: 'Bein N Co.',
  owner_user_id: 1,
  wins: 0,
  losses: 0,
  ties: 0,
  points_for: 0,
};

/** Shaped exactly like the live ESPN week 1 payload for this team. */
const player = (over: Partial<RosterPlayer>): RosterPlayer => ({
  player_id: 1,
  full_name: 'Player One',
  position_id: 2,
  position_name: 'RB',
  lineup_slot_id: 2,
  lineup_slot_name: 'RB',
  is_starter: true,
  on_injured_reserve: false,
  pro_team_abbr: 'IND',
  eligible_slots: [2, 23, 20],
  injury_status: 'ACTIVE',
  is_injured: false,
  percent_owned: 99.9,
  positional_ranking: 4,
  applied_points: 0,
  projected_points: 10,
  season_points: 0,
  ...over,
});

const roster: RosterPlayer[] = [
  player({ player_id: 1, full_name: 'Jonathan Taylor', projected_points: 17.8 }),
  player({
    player_id: 2,
    full_name: 'A.J. Brown',
    position_name: 'WR',
    lineup_slot_id: 4,
    lineup_slot_name: 'WR',
    injury_status: 'INJURY_RESERVE',
    is_injured: true,
    applied_points: 5.6,
    projected_points: 14.2,
    season_points: 5.6,
  }),
  player({
    player_id: 3,
    full_name: 'Cam Skattebo',
    lineup_slot_name: 'RB',
    projected_points: 4.0,
  }),
  player({
    player_id: 4,
    full_name: 'Kenny Gainwell',
    lineup_slot_id: 20,
    lineup_slot_name: 'BENCH',
    is_starter: false,
    projected_points: 12.0,
    applied_points: 3.0,
  }),
  player({
    player_id: 5,
    full_name: 'Tank Dell',
    position_name: 'WR',
    lineup_slot_id: 21,
    lineup_slot_name: 'IR',
    is_starter: false,
    on_injured_reserve: true,
    injury_status: 'INJURY_RESERVE',
    projected_points: 0,
  }),
];

vi.mock('@/hooks/useLeagues', () => ({ useLeague: () => ({ data: league }) }));
// The primer card is its own feature with its own tests; here it just must not
// drag a live react-query client into this page's render.
vi.mock('@/hooks/useAssistant', () => ({
  useWeeklyPrimer: () => ({ data: undefined, isLoading: false, isError: true }),
}));
// Which team is mine takes two requests, and the page has to hold its tongue
// until both land, so both are switchable here.
const lookup = vi.hoisted(() => ({ teamsLoading: false, userLoading: false, teams: true }));

vi.mock('@/hooks/useAuth', () => ({
  useCurrentUser: () => ({
    data: lookup.userLoading ? undefined : { id: 1 },
    isLoading: lookup.userLoading,
  }),
}));
vi.mock('@/hooks/useTeams', () => ({
  useLeagueTeams: () => ({
    data: lookup.teamsLoading || !lookup.teams ? undefined : [myTeam],
    isLoading: lookup.teamsLoading,
  }),
  useTeamRoster: () => ({ data: { team_id: 9, week: 1, roster }, isLoading: false }),
}));

beforeEach(() => {
  lookup.teamsLoading = false;
  lookup.userLoading = false;
  lookup.teams = true;
});
const currentMatchupCalls: number[] = [];
vi.mock('@/hooks/useMatchups', () => ({
  useCurrentMatchup: (_leagueId: number, teamId: number) => {
    currentMatchupCalls.push(teamId);
    return {
      opponent: { teamId: 10, teamName: 'Post-Coitus Cake Toss', score: 15.5 },
      myScore: 5.6,
      isLoading: false,
    };
  },
}));

const renderPage = () =>
  render(
    <MemoryRouter>
      <MyRosterPage />
    </MemoryRouter>
  );

const panel = (testId: string) => screen.getByTestId(testId);

describe('MyRosterPage', () => {
  it('splits starters from the bench instead of listing everyone as a starter', () => {
    renderPage();
    // Slot names arrive uppercase ("BENCH"); the old filter compared against
    // "Bench", so every player landed in the starting lineup. The count now
    // lives in the tool header alongside the scoring format.
    expect(screen.getByText(/3 starters/)).toBeInTheDocument();
    expect(within(panel('starters-panel')).getByText('Jonathan Taylor')).toBeInTheDocument();
    expect(within(panel('bench-panel')).getByText('Kenny Gainwell')).toBeInTheDocument();
    expect(within(panel('starters-panel')).queryByText('Kenny Gainwell')).toBeNull();
  });

  it('shows per-player week projections rather than raw stat dicts', () => {
    renderPage();
    // These come from projected_points; the page used to read stats.projected['0'],
    // which is a raw ESPN stat id and always rendered 0.0.
    expect(screen.getByText('17.8')).toBeInTheDocument();
    expect(screen.getByText('14.2')).toBeInTheDocument();
  });

  it('totals only the starters for the week score and projection', () => {
    renderPage();
    // Starters project 17.8 + 14.2 + 4.0 = 36.0, and the bench is reported apart.
    expect(screen.getByText('36.0')).toBeInTheDocument();
    expect(screen.getByText('points not started')).toBeInTheDocument();
  });

  it('warns when a starter cannot play', () => {
    renderPage();
    expect(screen.getByText('1 starter needs attention')).toBeInTheDocument();
    expect(screen.getByText(/is on injured reserve in your WR slot/)).toBeInTheDocument();
  });

  it('flags a bench player who out-projects a startable slot', () => {
    renderPage();
    // Gainwell projects 12.0 against Skattebo's 4.0 in an RB slot.
    expect(screen.getByText(/\+8\.0 proj over Cam Skattebo/)).toBeInTheDocument();
  });

  it('separates injured reserve from the bench', () => {
    renderPage();
    expect(within(panel('ir-panel')).getByText('Tank Dell')).toBeInTheDocument();
    expect(within(panel('bench-panel')).queryByText('Tank Dell')).not.toBeInTheDocument();
  });

  it('looks up the matchup by database team id, not the ESPN id', () => {
    currentMatchupCalls.length = 0;
    renderPage();
    expect(currentMatchupCalls).toContain(42);
    expect(currentMatchupCalls).not.toContain(9);
  });

  it('shows the live matchup and links out to ESPN to set the lineup', () => {
    renderPage();
    expect(screen.getByText('Post-Coitus Cake Toss')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Set lineup on ESPN/ })).toHaveAttribute(
      'href',
      'https://fantasy.espn.com/football/team?leagueId=1725275280&teamId=9&seasonId=2026'
    );
  });

  it('does not claim you have no team while it is still finding out', () => {
    // Two requests decide which team is mine. Rendering the "no team" state in
    // the meantime told every visitor they had not claimed one, a second
    // before showing them their roster.
    lookup.teamsLoading = true;
    const { container } = renderPage();

    expect(screen.queryByText('No Team Selected')).toBeNull();
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('waits on the user lookup too, not just the teams', () => {
    lookup.userLoading = true;
    renderPage();
    expect(screen.queryByText('No Team Selected')).toBeNull();
  });

  it('still says so once it knows there is no team', () => {
    lookup.teams = false;
    renderPage();
    expect(screen.getByText('No Team Selected')).toBeInTheDocument();
  });
});
