import { describe, expect, it, vi, beforeEach } from 'vitest';

import { GamePlanPage } from './GamePlanPage';
import { renderWithProviders, screen, within } from '@/test/render';
import { ActionPlan, RosterAction } from '@/types';

const state = vi.hoisted(() => ({
  data: undefined as ActionPlan | undefined,
  isLoading: false,
  isError: false,
  error: undefined as { detail?: string } | undefined,
}));

vi.mock('@/hooks/useActionPlan', () => ({ useActionPlan: () => state }));
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<any>('react-router-dom')),
  useParams: () => ({ leagueId: '1' }),
}));

const action = (over: Partial<RosterAction> = {}): RosterAction => ({
  kind: 'lineup_hole',
  urgency: 'high',
  hole: {
    player: 'A.J. Brown', player_id: 1, position: 'WR', slot: 'WR',
    status: 'INJURY_RESERVE', points_lost: 15,
  },
  start_instead: {
    player: 'Jalen Coker', player_id: 2, position: 'WR',
    projected: 10.5, last_week: 33.8, team: 'CAR',
  },
  other_bench: [],
  waiver_targets: [{
    player: "Wan'Dale Robinson", player_id: 3, position: 'WR', team: 'NYG',
    projected: 9.4, added_by: 3100, contested: true,
  }],
  faab: {
    remaining: 100, total: 100, spent_pct: 0,
    suggested_bid: 20, max_sensible: 50, note: null,
  },
  trades: [{
    team: 'Mind Goblins', they_need: 'RB', they_can_spare: 'WR',
    your_surplus_points: 18.2,
  }],
  ...over,
});

const plan = (over: Partial<ActionPlan> = {}): ActionPlan => ({
  league_id: 1, league: 'AEPI 2022', team: 'Bein N Co.', week: 2,
  summary: 'Start Coker for Brown and bid on Robinson.',
  actions: [action()],
  risks: [],
  depth: {},
  budget: { remaining: 100, total: 100 },
  all_clear: false,
  ...over,
});

const show = (data?: ActionPlan, flags: Partial<typeof state> = {}) => {
  Object.assign(state, { data, isLoading: false, isError: false, error: undefined }, flags);
  return renderWithProviders(<GamePlanPage />);
};

beforeEach(() => {
  Object.assign(state, {
    data: undefined, isLoading: false, isError: false, error: undefined,
  });
});

describe('GamePlanPage', () => {
  it('names the problem in plain language', () => {
    show(plan());
    expect(screen.getByText(/A\.J\. Brown is injury reserve/i)).toBeInTheDocument();
    expect(screen.getByText(/Your WR slot scores 0/)).toBeInTheDocument();
  });

  it('recommends the bench replacement and says why', () => {
    show(plan());
    const card = screen.getByTestId('action-card');
    expect(within(card).getByText('Jalen Coker')).toBeInTheDocument();
    expect(within(card).getByText(/Scored 33\.8 last week/)).toBeInTheDocument();
  });

  it('says plainly when the bench cannot cover the slot', () => {
    // The worst case, and the one where the advice has to change entirely.
    show(plan({ actions: [action({ start_instead: null, urgency: 'critical' })] }));
    expect(screen.getByText(/Nobody on your bench can legally start/)).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('lists who is available to add', () => {
    show(plan());
    expect(screen.getByText("Wan'Dale Robinson")).toBeInTheDocument();
  });

  it('warns when a target is being added everywhere', () => {
    show(plan());
    expect(screen.getByText(/3,100 adds today/)).toBeInTheDocument();
  });

  it('gives a FAAB number, not just a nudge', () => {
    show(plan());
    expect(screen.getByText('$20')).toBeInTheDocument();
  });

  it('reports an exhausted budget instead of advising a bid', () => {
    show(plan({
      actions: [action({
        faab: {
          remaining: 0, total: 100, spent_pct: 100, suggested_bid: 0,
          max_sensible: 0, note: 'Nothing left to bid; this has to be a free-agent claim.',
        },
      })],
    }));
    expect(screen.getByText(/Nothing left to bid/)).toBeInTheDocument();
  });

  it('surfaces a trade angle', () => {
    show(plan());
    expect(screen.getByText(/is thin at RB and can spare a WR/)).toBeInTheDocument();
  });

  it('leads with the written summary', () => {
    show(plan());
    expect(screen.getByText(/Start Coker for Brown/)).toBeInTheDocument();
  });

  it('still renders the plan when the model wrote nothing', () => {
    show(plan({ summary: null }));
    expect(screen.getByTestId('action-card')).toBeInTheDocument();
  });

  it('says so when nothing is wrong', () => {
    show(plan({ actions: [], all_clear: true, summary: null }));
    expect(screen.getByText('Nothing to fix')).toBeInTheDocument();
    expect(screen.queryByTestId('action-card')).toBeNull();
  });

  it('separates questionable players from ruled-out ones', () => {
    show(plan({
      actions: [],
      risks: [{ player: 'Puka Nacua', slot: 'WR', status: 'QUESTIONABLE', projected: 14 }],
    }));
    expect(screen.getByText('Worth watching')).toBeInTheDocument();
    expect(screen.getByText('Puka Nacua')).toBeInTheDocument();
  });

  it('counts the problems in the header', () => {
    show(plan());
    expect(screen.getByText(/1 thing needs your attention/)).toBeInTheDocument();
  });

  it('shows placeholders while loading', () => {
    const { container } = show(undefined, { isLoading: true });
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('reports a failure rather than an empty page', () => {
    show(undefined, { isError: true, error: { detail: 'Upstream is down' } });
    expect(screen.getByText('Upstream is down')).toBeInTheDocument();
  });

  it('does not ask you to bid when there is nothing to claim', () => {
    // Moving your own bench player into the slot costs nothing. Showing a bid
    // under "nothing is available" reads as advice to bid on a player you
    // already own.
    show(plan({ actions: [action({ waiver_targets: [], faab: null })] }));

    expect(screen.getByText(/Nothing better than your bench is free/)).toBeInTheDocument();
    expect(screen.queryByText('What to bid')).toBeNull();
    expect(screen.queryByText(/\$20/)).toBeNull();
  });
});
