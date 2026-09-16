import { describe, expect, it, vi, beforeEach } from 'vitest';
import userEvent from '@testing-library/user-event';

import { TradeAnalyzerPage } from './TradeAnalyzerPage';
import { renderWithProviders, screen } from '@/test/render';
import {
  CounterResult,
  LeagueTrade,
  MarketTeam,
  TradeEvaluation,
  TradeFinderResult,
  TradeMarket,
  TradeOffers,
} from '@/types';

const state = vi.hoisted(() => ({
  offers: {
    data: undefined as TradeOffers | undefined,
    isLoading: false,
    isError: false,
  },
  market: {
    data: undefined as TradeMarket | undefined,
    isLoading: false,
    isError: false,
  },
  finder: {
    data: undefined as TradeFinderResult | undefined,
    isLoading: false,
    isError: false,
  },
  evaluate: {
    mutateAsync: vi.fn(),
    isLoading: false,
    isError: false,
  },
  connect: { mutate: vi.fn(), isLoading: false },
  disconnect: { mutate: vi.fn(), isLoading: false },
  counters: { mutateAsync: vi.fn(), isLoading: false },
}));

vi.mock('@/hooks/useTrades', () => ({
  useTradeOffers: () => state.offers,
  useTradeMarket: () => state.market,
  useTradeFinder: () => state.finder,
  useEvaluateTrade: () => state.evaluate,
  useConnectSleeperToken: () => state.connect,
  useDisconnectSleeperToken: () => state.disconnect,
  useCounterOffers: () => state.counters,
}));
vi.mock('@/hooks/useLeagues', () => ({
  useLeague: () => ({ data: { id: 1, name: 'Cen10' } }),
}));
vi.mock('react-router-dom', async () => ({
  ...(await vi.importActual<any>('react-router-dom')),
  useParams: () => ({ leagueId: '1' }),
}));

const marketPlayer = (id: string, name: string, position: string, points: number) => ({
  player_id: id,
  full_name: name,
  position,
  pro_team: 'MIN',
  projected_points: points,
  injury_status: null,
  value: points - 5,
  is_starter: true,
  on_injured_reserve: false,
});

const team = (over: Partial<MarketTeam> = {}): MarketTeam => ({
  team_id: 1,
  team_name: 'Bein N Co.',
  is_mine: true,
  record: '1-0',
  lineup_points: 120,
  needs: ['TE'],
  surplus: ['RB'],
  players: [
    marketPlayer('4199', 'Aaron Jones', 'RB', 14.2),
    marketPlayer('9999', 'Some Guy', 'WR', 8.1),
  ],
  ...over,
});

const market = (over: Partial<TradeMarket> = {}): TradeMarket => ({
  league_id: 1,
  my_team_id: 1,
  replacement_levels: { RB: 8, WR: 7 },
  starting_slots: { QB: 1, RB: 2, WR: 2, TE: 1, FLEX: 1 },
  teams: [
    team(),
    team({
      team_id: 2,
      team_name: 'jcannon12',
      is_mine: false,
      record: '0-1',
      needs: ['RB'],
      surplus: ['TE'],
      players: [marketPlayer('6806', 'J.K. Dobbins', 'RB', 15.6)],
    }),
  ],
  ...over,
});

const incomingOffer = (): LeagueTrade => ({
  trade_id: 'tx-1',
  status: 'proposed',
  direction: 'incoming',
  proposed_at: new Date(Date.now() - 86_400_000).toISOString(),
  week: 2,
  source: 'sleeper',
  parties: [
    {
      team_id: 1,
      team_name: 'Bein N Co.',
      platform_team_id: 2,
      has_consented: false,
      sends: [
        {
          player_id: '4199',
          full_name: 'Aaron Jones',
          position: 'RB',
          pro_team: 'MIN',
          projected_points: 14.2,
          injury_status: null,
        },
      ],
    },
    {
      team_id: 2,
      team_name: 'jcannon12',
      platform_team_id: 1,
      has_consented: true,
      sends: [
        {
          player_id: '6806',
          full_name: 'J.K. Dobbins',
          position: 'RB',
          pro_team: 'DEN',
          projected_points: 15.6,
          injury_status: null,
        },
      ],
    },
  ],
});

const offers = (over: Partial<TradeOffers> = {}): TradeOffers => ({
  league_id: 1,
  platform: 'sleeper',
  my_team_id: 1,
  pending: [incomingOffer()],
  history: [],
  pending_available: true,
  pending_notice: null,
  ...over,
});

const evaluation = (over: Partial<TradeEvaluation> = {}): TradeEvaluation => ({
  verdict: 'lean_accept',
  headline: 'Nudges your playoff odds +3.2 points.',
  fairness_score: 88,
  you: {
    team_id: 1,
    team_name: 'Bein N Co.',
    lineup_before: 120.5,
    lineup_after: 121.9,
    lineup_delta: 1.4,
    value_out: 6.2,
    value_in: 7.6,
    value_delta: 1.4,
    depth_before: { RB: { rostered: 4, startable: 3, required: 2, surplus: 1, best: 14.2 } },
    depth_after: { RB: { rostered: 4, startable: 4, required: 2, surplus: 2, best: 15.6 } },
  },
  them: {
    team_id: 2,
    team_name: 'jcannon12',
    lineup_before: 110,
    lineup_after: 109,
    lineup_delta: -1,
    value_out: 7.6,
    value_in: 6.2,
    value_delta: -1.4,
    depth_before: {},
    depth_after: {},
  },
  playoff_odds: {
    before: 44.5,
    after: 47.7,
    delta: 3.2,
    iterations: 2000,
    weeks_simulated: 13,
    playoff_spots: 6,
    schedule_source: 'platform',
  },
  risks: [],
  ai_summary: 'A modest upgrade at running back that your lineup can actually use.',
  ai_points: ['Dobbins projects 1.4 points a week higher in your starting lineup.'],
  counter_suggestion: null,
  players_you_send: [],
  players_you_get: [],
  intel: {},
  ...over,
});

const counterResult = (over: Partial<CounterResult> = {}): CounterResult => ({
  league_id: 1,
  original_verdict: 'neutral',
  original_lineup_delta: 0,
  original_headline: 'Close to a wash.',
  summary: '2 counters beat accepting as written.',
  ai_summary: 'Ask for the tight end instead; it is where your lineup is thin.',
  counters: [
    {
      kind: 'different_target',
      give: [
        {
          player_id: '4199', full_name: 'Aaron Jones', position: 'RB',
          pro_team: 'MIN', projected_points: 14.2, injury_status: null,
        },
      ],
      receive: [
        {
          player_id: '7777', full_name: 'Some Tight End', position: 'TE',
          pro_team: 'DEN', projected_points: 12.9, injury_status: null,
        },
      ],
      my_lineup_delta: 3.1,
      their_lineup_delta: 0.4,
      fairness: 84,
      gain_vs_original: 3.1,
      cost_to_them: 0.6,
      likelihood: 'fair_ask',
      likelihood_reason: 'Slightly worse for them than their own offer',
      rationale: 'Same price, ask for Some Tight End instead. TE is where you are thinnest.',
    },
    {
      kind: 'ask_for_more',
      give: [
        {
          player_id: '4199', full_name: 'Aaron Jones', position: 'RB',
          pro_team: 'MIN', projected_points: 14.2, injury_status: null,
        },
      ],
      receive: [
        {
          player_id: '6806', full_name: 'J.K. Dobbins', position: 'RB',
          pro_team: 'DEN', projected_points: 15.6, injury_status: null,
        },
        {
          player_id: '8888', full_name: 'Spare Receiver', position: 'WR',
          pro_team: 'LAR', projected_points: 9.4, injury_status: null,
        },
      ],
      my_lineup_delta: 1.2,
      their_lineup_delta: -2.2,
      fairness: 61,
      gain_vs_original: 1.2,
      cost_to_them: 5.9,
      likelihood: 'unlikely',
      likelihood_reason: 'Much worse for them than their own offer',
      rationale: 'Same deal, but ask for Spare Receiver on top.',
    },
  ],
  ...over,
});

const show = () => renderWithProviders(<TradeAnalyzerPage />);

beforeEach(() => {
  state.offers = { data: offers(), isLoading: false, isError: false };
  state.market = { data: market(), isLoading: false, isError: false };
  state.finder = { data: undefined, isLoading: false, isError: false };
  state.evaluate = {
    mutateAsync: vi.fn().mockResolvedValue(evaluation()),
    isLoading: false,
    isError: false,
  };
  state.connect = { mutate: vi.fn(), isLoading: false };
  state.disconnect = { mutate: vi.fn(), isLoading: false };
  state.counters = { mutateAsync: vi.fn().mockResolvedValue(counterResult()), isLoading: false };
});

describe('Offers tab', () => {
  it('shows a pending offer with both sides named', () => {
    show();
    expect(screen.getByText('Aaron Jones')).toBeInTheDocument();
    expect(screen.getByText('J.K. Dobbins')).toBeInTheDocument();
    // The side I am on is labelled from my point of view, not by team name.
    expect(screen.getByText('You give')).toBeInTheDocument();
    expect(screen.getByText('jcannon12 gives')).toBeInTheDocument();
  });

  it('marks an incoming offer and counts it on the tab', () => {
    show();
    expect(screen.getByText('Incoming')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Offers \(1\)/ })).toBeInTheDocument();
  });

  it('shows which side has already agreed', () => {
    show();
    // Only the proposer has consented, which is what makes it *my* decision.
    expect(screen.getByText('accepted')).toBeInTheDocument();
  });

  it('says nothing is pending when nothing is', () => {
    state.offers.data = offers({ pending: [] });
    show();
    expect(screen.getByText(/No offers on the table/)).toBeInTheDocument();
  });

  it('explains the Sleeper gap instead of showing a bare empty list', () => {
    state.offers.data = offers({
      pending: [],
      pending_available: false,
      pending_notice:
        "Sleeper's public API only returns completed trades. Connect your Sleeper token to see offers waiting on you.",
    });
    show();
    expect(screen.getByText(/Connect Sleeper to see pending offers/)).toBeInTheDocument();
    expect(screen.getByText(/only returns completed trades/)).toBeInTheDocument();
  });

  it('saves a pasted Sleeper token', async () => {
    const user = userEvent.setup();
    state.offers.data = offers({
      pending: [],
      pending_available: false,
      pending_notice: 'Connect your Sleeper token.',
    });
    show();

    await user.type(screen.getByPlaceholderText(/Paste your Sleeper token/), 'a-real-looking-token');
    await user.click(screen.getByRole('button', { name: 'Connect' }));

    expect(state.connect.mutate).toHaveBeenCalledWith('a-real-looking-token');
  });

  it('renders completed trades separately from pending ones', () => {
    state.offers.data = offers({
      pending: [],
      history: [{ ...incomingOffer(), trade_id: 'tx-old', status: 'executed', direction: 'other' }],
    });
    show();
    expect(screen.getByText('Recent trades')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
  });
});

describe('Trade machine', () => {
  const openMachine = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(screen.getByRole('tab', { name: /Trade Machine/ }));
  };

  it('lets you pick players by name rather than by platform id', async () => {
    const user = userEvent.setup();
    show();
    await openMachine(user);

    // Regression: this page used to ask for "ESPN Player ID 1/2/3" in number
    // inputs, which made the feature unusable without reading an API by hand.
    expect(screen.queryByPlaceholderText(/ESPN Player ID/)).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Aaron Jones/ })).toBeInTheDocument();
  });

  it('defaults your side to the team you manage', async () => {
    const user = userEvent.setup();
    show();
    await openMachine(user);
    expect(screen.getByText(/Bein N Co\. gives up/)).toBeInTheDocument();
  });

  it('analyzing a pending offer loads it into the machine and scores it', async () => {
    const user = userEvent.setup();
    show();

    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));
    await screen.findByText('Lean accept');

    expect(state.evaluate.mutateAsync).toHaveBeenCalledWith({
      team_a_id: 1,
      team_b_id: 2,
      team_a_sends: ['4199'],
      team_b_sends: ['6806'],
    });
  });

  it('renders the verdict, odds delta and lineup change', async () => {
    const user = userEvent.setup();
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText('Lean accept')).toBeInTheDocument();
    expect(screen.getByText('45% → 48%')).toBeInTheDocument();
    expect(screen.getByText('+3.2')).toBeInTheDocument();
    expect(screen.getByText('120.5 → 121.9')).toBeInTheDocument();
    expect(screen.getByText('+1.4')).toBeInTheDocument();
    expect(screen.getByText(/Fairness 88\/100/)).toBeInTheDocument();
  });

  it('shows the AI read below the computed numbers', async () => {
    const user = userEvent.setup();
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText(/modest upgrade at running back/)).toBeInTheDocument();
    expect(screen.getByText(/projects 1\.4 points a week higher/)).toBeInTheDocument();
  });

  it('surfaces data-derived risks when there are any', async () => {
    const user = userEvent.setup();
    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(
      evaluation({ risks: ['J.K. Dobbins is listed Questionable.'] })
    );
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText('Watch out')).toBeInTheDocument();
    expect(screen.getByText(/listed Questionable/)).toBeInTheDocument();
  });

  it('says so when a reject is a reject', async () => {
    const user = userEvent.setup();
    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(
      evaluation({
        verdict: 'reject',
        headline: 'Costs you 9.1 points of playoff odds.',
        playoff_odds: {
          before: 44.5, after: 35.4, delta: -9.1, iterations: 2000,
          weeks_simulated: 13, playoff_spots: 6, schedule_source: 'platform',
        },
      })
    );
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText('Reject')).toBeInTheDocument();
    expect(screen.getByText('-9.1')).toBeInTheDocument();
  });

  it('handles a league with no games left to simulate', async () => {
    const user = userEvent.setup();
    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(
      evaluation({ playoff_odds: null })
    );
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText('Not simulated')).toBeInTheDocument();
  });
});

describe('Trade finder', () => {
  it('lists mutual upgrades with both deltas', async () => {
    const user = userEvent.setup();
    state.finder.data = {
      league_id: 1,
      my_team_id: 1,
      needs: ['TE'],
      surplus: ['RB'],
      ideas: [
        {
          partner_team_id: 2,
          partner_team_name: 'jcannon12',
          give: [
            {
              player_id: '4199', full_name: 'Aaron Jones', position: 'RB',
              pro_team: 'MIN', projected_points: 14.2, injury_status: null,
            },
          ],
          receive: [
            {
              player_id: '6806', full_name: 'J.K. Dobbins', position: 'RB',
              pro_team: 'DEN', projected_points: 15.6, injury_status: null,
            },
          ],
          my_lineup_delta: 2.3,
          their_lineup_delta: 1.1,
          mutual_gain: 3.4,
          fairness: 91,
        },
      ],
    };
    show();
    await user.click(screen.getByRole('tab', { name: /Find Trades/ }));

    expect(screen.getByText('You +2.3/wk')).toBeInTheDocument();
    expect(screen.getByText('Them +1.1/wk')).toBeInTheDocument();
    expect(screen.getByText('surplus at RB')).toBeInTheDocument();
    expect(screen.getByText('thin at TE')).toBeInTheDocument();
  });

  it('is honest when there is nothing worth proposing', async () => {
    const user = userEvent.setup();
    state.finder.data = {
      league_id: 1, my_team_id: 1, ideas: [], needs: [], surplus: [],
    };
    show();
    await user.click(screen.getByRole('tab', { name: /Find Trades/ }));

    expect(screen.getByText(/No mutual upgrades right now/)).toBeInTheDocument();
  });
});

describe('Counter-offers', () => {
  const analyzeOffer = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));
    await screen.findByText('Lean accept');
  };

  it('offers to explore counters without being asked for a verdict first', async () => {
    const user = userEvent.setup();
    show();
    await analyzeOffer(user);

    // Available whatever the verdict was, which is the point: a trade worth
    // accepting may still be worth improving.
    expect(screen.getByRole('button', { name: 'Explore counters' })).toBeInTheDocument();
  });

  it('runs on demand and lists the counters with their reasons', async () => {
    const user = userEvent.setup();
    show();
    await analyzeOffer(user);
    await user.click(screen.getByRole('button', { name: 'Explore counters' }));

    expect(state.counters.mutateAsync).toHaveBeenCalledWith({
      team_a_id: 1,
      team_b_id: 2,
      team_a_sends: ['4199'],
      team_b_sends: ['6806'],
    });

    expect(await screen.findByText(/2 counters beat accepting/)).toBeInTheDocument();
    expect(screen.getByText(/ask for Some Tight End instead/)).toBeInTheDocument();
    expect(screen.getByText(/ask for Spare Receiver on top/)).toBeInTheDocument();
  });

  it('labels how big an ask each counter is', async () => {
    const user = userEvent.setup();
    show();
    await analyzeOffer(user);
    await user.click(screen.getByRole('button', { name: 'Explore counters' }));

    // Graded against the offer they themselves made, not against nothing.
    expect(await screen.findByText('Fair ask')).toBeInTheDocument();
    expect(screen.getByText('Long shot')).toBeInTheDocument();
    expect(screen.getByText('+3.1/wk vs accepting')).toBeInTheDocument();
  });

  it('loads a counter back into the machine to score it', async () => {
    const user = userEvent.setup();
    show();
    await analyzeOffer(user);
    await user.click(screen.getByRole('button', { name: 'Explore counters' }));
    await screen.findByText(/2 counters beat accepting/);

    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(evaluation());
    await user.click(screen.getAllByRole('button', { name: 'Analyze this' })[0]);

    expect(state.evaluate.mutateAsync).toHaveBeenCalledWith({
      team_a_id: 1,
      team_b_id: 2,
      team_a_sends: ['4199'],
      team_b_sends: ['7777'],
    });
  });

  it('says plainly when nothing beats accepting', async () => {
    const user = userEvent.setup();
    state.counters.mutateAsync = vi.fn().mockResolvedValue(
      counterResult({
        counters: [],
        ai_summary: null,
        summary: 'Nothing built from these two rosters beats simply accepting or declining.',
      })
    );
    show();
    await analyzeOffer(user);
    await user.click(screen.getByRole('button', { name: 'Explore counters' }));

    expect(await screen.findByText(/Nothing built from these two rosters/)).toBeInTheDocument();
  });
});

describe('Player news', () => {
  const withIntel = () =>
    evaluation({
      players_you_get: [
        {
          player_id: '6806', full_name: 'J.K. Dobbins', position: 'RB',
          pro_team: 'DEN', projected_points: 15.6, injury_status: null,
        },
      ],
      players_you_send: [
        {
          player_id: '4199', full_name: 'Aaron Jones', position: 'RB',
          pro_team: 'MIN', projected_points: 14.2, injury_status: null,
        },
      ],
      intel: {
        '6806': {
          full_name: 'J.K. Dobbins',
          role: 'Starting RB',
          injury: null,
          age: 27,
          years_exp: 6,
          nfl_team: 'DEN',
          headlines: [
            {
              headline: 'Dobbins expects a full workload Sunday',
              description: null,
              published: new Date(Date.now() - 3_600_000).toISOString(),
              category: 'News',
              url: 'https://example.com/dobbins',
            },
          ],
        },
        '4199': {
          full_name: 'Aaron Jones',
          role: 'RB2 on the depth chart',
          injury: {
            status: 'Questionable',
            body_part: 'Hamstring',
            notes: null,
            practice: 'Limited Participation in Practice',
          },
          age: 31,
          years_exp: 9,
          nfl_team: 'MIN',
          headlines: [],
        },
      },
    });

  it('shows depth-chart role, which a projection cannot express', async () => {
    const user = userEvent.setup();
    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(withIntel());
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText('Starting RB')).toBeInTheDocument();
    expect(screen.getByText('RB2 on the depth chart')).toBeInTheDocument();
  });

  it('shows the injury designation and practice status', async () => {
    const user = userEvent.setup();
    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(withIntel());
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    expect(await screen.findByText(/Questionable · Hamstring/)).toBeInTheDocument();
    expect(
      screen.getByText(/Practice: Limited Participation in Practice/)
    ).toBeInTheDocument();
  });

  it('links recent headlines out to the source', async () => {
    const user = userEvent.setup();
    state.evaluate.mutateAsync = vi.fn().mockResolvedValue(withIntel());
    show();
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));

    const link = await screen.findByRole('link', {
      name: /Dobbins expects a full workload/,
    });
    expect(link).toHaveAttribute('href', 'https://example.com/dobbins');
    expect(screen.getByText('1h ago')).toBeInTheDocument();
  });

  it('stays out of the way when there is nothing to report', async () => {
    const user = userEvent.setup();
    show(); // default evaluation has intel: {}
    await user.click(screen.getByRole('button', { name: /Analyze this offer/ }));
    await screen.findByText('Lean accept');

    expect(screen.queryByText('Latest on these players')).not.toBeInTheDocument();
  });
});
