import React, { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ArrowsRightLeftIcon,
  BoltIcon,
  InboxArrowDownIcon,
  LightBulbIcon,
  LinkIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { useLeague } from '@/hooks/useLeagues';
import {
  useConnectSleeperToken,
  useCounterOffers,
  useDisconnectSleeperToken,
  useEvaluateTrade,
  useTradeFinder,
  useTradeMarket,
  useTradeOffers,
} from '@/hooks/useTrades';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  LoadingSpinner,
  Select,
  Skeleton,
  SkeletonText,
  Tabs,
} from '@/components/ui';
import type { SelectOption, TabItem } from '@/components/ui';
import { CounterOffers } from '@/components/trades/CounterOffers';
import { OfferCard } from '@/components/trades/OfferCard';
import { PlayerNews } from '@/components/trades/PlayerNews';
import { PlayerPicker } from '@/components/trades/PlayerPicker';
import { TradeVerdictPanel } from '@/components/trades/TradeVerdictPanel';
import { PageContainer, PageHeader } from '@/components/layout/Page';
import {
  CounterOffer,
  CounterResult,
  LeagueTrade,
  MarketTeam,
  TradeEvaluation,
  TradeIdea,
} from '@/types';

type TabKey = 'offers' | 'machine' | 'finder';

export const TradeAnalyzerPage: React.FC = () => {
  const { leagueId } = useParams<{ leagueId: string }>();
  const id = parseInt(leagueId || '0', 10);
  const { data: league } = useLeague(id);

  const [tab, setTab] = useState<TabKey>('offers');
  const [pickedTeamAId, setTeamAId] = useState<number | null>(null);
  const [teamBId, setTeamBId] = useState<number | null>(null);
  const [aSends, setASends] = useState<string[]>([]);
  const [bSends, setBSends] = useState<string[]>([]);
  const [evaluation, setEvaluation] = useState<TradeEvaluation | null>(null);
  const [counters, setCounters] = useState<CounterResult | null>(null);

  const offers = useTradeOffers(id);
  const market = useTradeMarket(id);
  const finder = useTradeFinder(id, tab === 'finder');
  const evaluate = useEvaluateTrade(id);
  const counterOffers = useCounterOffers(id);

  // "Your side" defaults to the team you actually manage. Derived rather than
  // synced in an effect, so there is no render where it is briefly wrong.
  const teamAId = pickedTeamAId ?? market.data?.my_team_id ?? null;

  const teams = market.data?.teams ?? [];
  const teamA = teams.find((t) => t.team_id === teamAId) ?? null;
  const teamB = teams.find((t) => t.team_id === teamBId) ?? null;

  const teamOptions = (exclude: number | null): SelectOption[] =>
    teams
      .filter((t) => t.team_id !== exclude)
      .map((t) => ({
        value: String(t.team_id),
        label: `${t.team_name}${t.is_mine ? ' (You)' : ''} · ${t.record}`,
      }));

  const toggle = (
    list: string[],
    setList: (next: string[]) => void,
    playerId: string
  ) => {
    setEvaluation(null);
    setCounters(null);
    setList(
      list.includes(playerId) ? list.filter((p) => p !== playerId) : [...list, playerId]
    );
  };

  const canEvaluate =
    teamAId !== null && teamBId !== null && aSends.length > 0 && bSends.length > 0;

  const runEvaluation = async (
    a = teamAId,
    b = teamBId,
    sendsA = aSends,
    sendsB = bSends
  ) => {
    if (a === null || b === null || sendsA.length === 0 || sendsB.length === 0) return;
    setCounters(null);
    try {
      const result = await evaluate.mutateAsync({
        team_a_id: a,
        team_b_id: b,
        team_a_sends: sendsA,
        team_b_sends: sendsB,
      });
      setEvaluation(result);
    } catch {
      // surfaced by the mutation's toast
    }
  };

  /**
   * Work out counters to whatever is currently in the machine. Triggered by
   * the user, and available whatever the verdict was: a trade worth accepting
   * may still be worth improving, and a trade worth rejecting is the one most
   * likely to have a version worth taking.
   */
  const exploreCounters = async () => {
    if (teamAId === null || teamBId === null) return;
    if (aSends.length === 0 || bSends.length === 0) return;
    try {
      setCounters(
        await counterOffers.mutateAsync({
          team_a_id: teamAId,
          team_b_id: teamBId,
          team_a_sends: aSends,
          team_b_sends: bSends,
        })
      );
    } catch {
      // surfaced by the mutation's toast
    }
  };

  /** Load a counter into the machine as the live trade, then score it. */
  const analyzeCounter = (counter: CounterOffer) => {
    if (teamAId === null || teamBId === null) return;
    const give = counter.give.map((p) => p.player_id);
    const get = counter.receive.map((p) => p.player_id);
    setASends(give);
    setBSends(get);
    setEvaluation(null);
    setCounters(null);
    void runEvaluation(teamAId, teamBId, give, get);
  };

  /** Load a pending offer into the machine and score it in one go. */
  const analyzeOffer = (trade: LeagueTrade) => {
    const myTeamId = offers.data?.my_team_id ?? market.data?.my_team_id ?? null;
    const mine = trade.parties.find((p) => p.team_id === myTeamId);
    const other = trade.parties.find((p) => p.team_id !== myTeamId && p.team_id !== null);
    if (!mine || !other || other.team_id === null || myTeamId === null) return;

    const give = mine.sends.map((p) => p.player_id);
    const get = other.sends.map((p) => p.player_id);

    setTeamAId(myTeamId);
    setTeamBId(other.team_id);
    setASends(give);
    setBSends(get);
    setEvaluation(null);
    setCounters(null);
    setTab('machine');
    void runEvaluation(myTeamId, other.team_id, give, get);
  };

  /** Load a suggested trade into the machine and score it. */
  const analyzeIdea = (idea: TradeIdea) => {
    const myTeamId = market.data?.my_team_id ?? null;
    if (myTeamId === null) return;
    const give = idea.give.map((p) => p.player_id);
    const get = idea.receive.map((p) => p.player_id);

    setTeamAId(myTeamId);
    setTeamBId(idea.partner_team_id);
    setASends(give);
    setBSends(get);
    setEvaluation(null);
    setCounters(null);
    setTab('machine');
    void runEvaluation(myTeamId, idea.partner_team_id, give, get);
  };

  const pendingCount = offers.data?.pending.length ?? 0;

  const tabs: TabItem[] = useMemo(
    () => [
      {
        key: 'offers',
        label: pendingCount > 0 ? `Offers (${pendingCount})` : 'Offers',
        icon: InboxArrowDownIcon,
      },
      { key: 'machine', label: 'Trade Machine', icon: ArrowsRightLeftIcon },
      { key: 'finder', label: 'Find Trades', icon: LightBulbIcon },
    ],
    [pendingCount]
  );

  return (
    <PageContainer>
      <PageHeader
        backTo={`/leagues/${leagueId}`}
        backLabel="Back to League"
        title="Trades"
        subtitle={`Offers, analysis and trade targets in ${league?.name ?? 'your league'}`}
        media={<ArrowsRightLeftIcon className="h-8 w-8 text-brand" />}
        mediaDesktopOnly
      />

      <Tabs
        tabs={tabs}
        value={tab}
        onChange={(key) => setTab(key as TabKey)}
        aria-label="Trade sections"
        className="mb-6"
      />

      {tab === 'offers' && (
        <OffersTab
          leagueId={id}
          query={offers}
          onAnalyze={analyzeOffer}
        />
      )}

      {tab === 'machine' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 lg:gap-8">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Who is trading</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select
                  fullWidth
                  label="Your side"
                  placeholder="Select a team…"
                  value={teamAId ? String(teamAId) : ''}
                  options={teamOptions(teamBId)}
                  onChange={(value) => {
                    setTeamAId(parseInt(value, 10));
                    setASends([]);
                    setEvaluation(null);
                  }}
                />
                <Select
                  fullWidth
                  label="Their side"
                  placeholder="Select a team…"
                  value={teamBId ? String(teamBId) : ''}
                  options={teamOptions(teamAId)}
                  onChange={(value) => {
                    setTeamBId(parseInt(value, 10));
                    setBSends([]);
                    setEvaluation(null);
                  }}
                />
              </CardContent>
            </Card>

            {market.isLoading ? (
              <Card>
                <CardContent className="pt-6">
                  <SkeletonText lines={6} />
                </CardContent>
              </Card>
            ) : (
              <>
                {teamA && (
                  <RosterCard
                    title={`${teamA.team_name} gives up`}
                    team={teamA}
                    selected={aSends}
                    onToggle={(pid) => toggle(aSends, setASends, pid)}
                  />
                )}
                {teamB && (
                  <RosterCard
                    title={`${teamB.team_name} gives up`}
                    team={teamB}
                    selected={bSends}
                    onToggle={(pid) => toggle(bSends, setBSends, pid)}
                  />
                )}
              </>
            )}

            {teamA && teamB && (
              <div className="flex gap-3">
                <Button
                  onClick={() => void runEvaluation()}
                  disabled={!canEvaluate || evaluate.isLoading}
                  className="flex-1"
                >
                  {evaluate.isLoading ? (
                    <>
                      <LoadingSpinner size="sm" className="mr-2" />
                      Running the numbers…
                    </>
                  ) : (
                    'Analyze trade'
                  )}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setASends([]);
                    setBSends([]);
                    setEvaluation(null);
                    setCounters(null);
                  }}
                >
                  Clear
                </Button>
              </div>
            )}
          </div>

          <div aria-live="polite">
            {evaluate.isLoading ? (
              <Card>
                <CardHeader>
                  <CardTitle>Analyzing…</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <Skeleton className="h-16 w-full rounded-lg" />
                  <SkeletonText lines={3} />
                  <SkeletonText lines={4} />
                </CardContent>
              </Card>
            ) : evaluation ? (
              <div className="space-y-4">
                <TradeVerdictPanel evaluation={evaluation} />
                <PlayerNews
                  title="Latest on these players"
                  players={[
                    ...evaluation.players_you_get,
                    ...evaluation.players_you_send,
                  ]}
                  intel={evaluation.intel}
                />
                <CounterOffers
                  result={counters}
                  isLoading={counterOffers.isLoading}
                  onExplore={() => void exploreCounters()}
                  onAnalyze={analyzeCounter}
                />
              </div>
            ) : evaluate.isError ? (
              <Card>
                <EmptyState
                  icon={XCircleIcon}
                  variant="error"
                  title="Couldn't analyze that trade"
                  description="Check that every selected player is still on the roster shown, then try again."
                />
              </Card>
            ) : (
              <Card>
                <EmptyState
                  icon={ArrowsRightLeftIcon}
                  title="Build a trade"
                  description="Pick two teams, then tap the players moving each way. You'll get a fairness score, the change to your starting lineup, and how it moves your playoff odds."
                />
              </Card>
            )}
          </div>
        </div>
      )}

      {tab === 'finder' && <FinderTab query={finder} onAnalyze={analyzeIdea} />}
    </PageContainer>
  );
};

const RosterCard: React.FC<{
  title: string;
  team: MarketTeam;
  selected: string[];
  onToggle: (playerId: string) => void;
}> = ({ title, team, selected, onToggle }) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-base">{title}</CardTitle>
      {(team.needs.length > 0 || team.surplus.length > 0) && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {team.surplus.map((position) => (
            <Badge key={`s-${position}`} variant="success" size="sm">
              deep at {position}
            </Badge>
          ))}
          {team.needs.map((position) => (
            <Badge key={`n-${position}`} variant="warning" size="sm">
              needs {position}
            </Badge>
          ))}
        </div>
      )}
    </CardHeader>
    <CardContent>
      <PlayerPicker players={team.players} selected={selected} onToggle={onToggle} />
    </CardContent>
  </Card>
);

const OffersTab: React.FC<{
  leagueId: number;
  query: ReturnType<typeof useTradeOffers>;
  onAnalyze: (trade: LeagueTrade) => void;
}> = ({ leagueId, query, onAnalyze }) => {
  if (query.isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <SkeletonText lines={5} />
        </CardContent>
      </Card>
    );
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <EmptyState
          icon={XCircleIcon}
          variant="error"
          title="Couldn't load offers"
          description="The league's platform didn't answer. Try again in a moment."
        />
      </Card>
    );
  }

  const { pending, history, pending_available: available, pending_notice: notice } =
    query.data;

  return (
    <div className="space-y-6">
      {!available && notice && <SleeperConnectCard leagueId={leagueId} notice={notice} />}

      <section>
        <h2 className="mb-3 text-lg font-semibold text-fg">
          Pending {pending.length > 0 && <span className="text-fg-muted">({pending.length})</span>}
        </h2>
        {pending.length > 0 ? (
          <div className="space-y-4">
            {pending.map((trade) => (
              <OfferCard
                key={trade.trade_id}
                trade={trade}
                myTeamId={query.data.my_team_id}
                onAnalyze={onAnalyze}
              />
            ))}
          </div>
        ) : (
          <Card>
            <EmptyState
              icon={InboxArrowDownIcon}
              title={available ? 'No offers on the table' : 'Pending offers not visible'}
              description={
                available
                  ? 'Nobody has a trade waiting on you. Try the Find Trades tab to start one.'
                  : 'Connect Sleeper above to see offers waiting on you.'
              }
            />
          </Card>
        )}
      </section>

      {history.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-fg">Recent trades</h2>
          <div className="space-y-4">
            {history.map((trade) => (
              <OfferCard
                key={trade.trade_id}
                trade={trade}
                myTeamId={query.data.my_team_id}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
};

/**
 * Sleeper's public API returns completed transactions only, so a pending offer
 * is genuinely invisible without the manager's own token. Saying that plainly
 * beats an empty list, which would read as "nobody has offered you a trade".
 */
const SleeperConnectCard: React.FC<{ leagueId: number; notice: string }> = ({
  leagueId,
  notice,
}) => {
  const [token, setToken] = useState('');
  const connect = useConnectSleeperToken(leagueId);
  const disconnect = useDisconnectSleeperToken(leagueId);

  return (
    <Card className="border-brand">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <LinkIcon className="h-5 w-5 text-brand" aria-hidden="true" />
          Connect Sleeper to see pending offers
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-fg-muted">{notice}</p>
        <details className="text-sm">
          <summary className="cursor-pointer font-medium text-brand">
            Where do I find my token?
          </summary>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-fg-muted">
            <li>Open sleeper.com in your browser and sign in.</li>
            <li>Open developer tools and go to the Console tab.</li>
            <li>
              Run <code className="rounded bg-surface-sunken px-1">localStorage.token</code>{' '}
              and copy the value it prints.
            </li>
          </ol>
          <p className="mt-2 text-xs text-fg-muted">
            Stored encrypted, and only ever used to read this league's pending trades.
          </p>
        </details>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            fullWidth
            type="password"
            placeholder="Paste your Sleeper token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
          />
          <Button
            onClick={() => connect.mutate(token.trim())}
            disabled={token.trim().length < 10 || connect.isLoading}
          >
            {connect.isLoading ? <LoadingSpinner size="sm" /> : 'Connect'}
          </Button>
          <Button variant="ghost" onClick={() => disconnect.mutate()}>
            Remove
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const FinderTab: React.FC<{
  query: ReturnType<typeof useTradeFinder>;
  onAnalyze: (idea: TradeIdea) => void;
}> = ({ query, onAnalyze }) => {
  if (query.isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <SkeletonText lines={6} />
        </CardContent>
      </Card>
    );
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <EmptyState
          icon={XCircleIcon}
          variant="error"
          title="Couldn't find trades"
          description="Claim your team in this league, then try again."
        />
      </Card>
    );
  }

  const { ideas, needs, surplus } = query.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="pt-6">
          <h2 className="text-base font-semibold text-fg">Your roster shape</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {surplus.length === 0 && needs.length === 0 && (
              <p className="text-sm text-fg-muted">
                Your roster is balanced against your starting slots.
              </p>
            )}
            {surplus.map((position) => (
              <Badge key={`s-${position}`} variant="success" size="sm">
                surplus at {position}
              </Badge>
            ))}
            {needs.map((position) => (
              <Badge key={`n-${position}`} variant="warning" size="sm">
                thin at {position}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {ideas.length === 0 ? (
        <Card>
          <EmptyState
            icon={LightBulbIcon}
            title="No mutual upgrades right now"
            description="Every swap we scored made one of the two teams worse, so none of them would get accepted. Build something by hand in the Trade Machine."
          />
        </Card>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-fg-muted">
            Swaps where <strong className="text-fg">both</strong> starting lineups improve, so
            the other manager has a reason to say yes. Best for you first.
          </p>
          {ideas.map((idea, index) => (
            <Card key={`${idea.partner_team_id}-${index}`}>
              <CardContent className="pt-5">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <BoltIcon className="h-4 w-4 text-brand" aria-hidden="true" />
                  <span className="text-sm font-semibold text-fg">
                    {idea.partner_team_name}
                  </span>
                  <Badge variant="success" size="sm">
                    You {idea.my_lineup_delta >= 0 ? '+' : ''}
                    {idea.my_lineup_delta.toFixed(1)}/wk
                  </Badge>
                  <Badge variant="default" size="sm">
                    Them {idea.their_lineup_delta >= 0 ? '+' : ''}
                    {idea.their_lineup_delta.toFixed(1)}/wk
                  </Badge>
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <IdeaSide label="You give" players={idea.give} />
                  <IdeaSide label="You get" players={idea.receive} />
                </div>

                <Button
                  variant="secondary"
                  className="mt-4 w-full sm:w-auto"
                  onClick={() => onAnalyze(idea)}
                >
                  Analyze in full
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

const IdeaSide: React.FC<{ label: string; players: TradeIdea['give'] }> = ({
  label,
  players,
}) => (
  <div className="rounded-lg border border-border bg-surface-sunken p-3">
    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">
      {label}
    </p>
    <ul className="space-y-1.5">
      {players.map((player) => (
        <li key={player.player_id} className="flex items-center gap-2">
          <span className="w-9 shrink-0 rounded bg-surface-raised px-1 py-0.5 text-center text-[10px] font-bold text-fg-muted">
            {player.position}
          </span>
          <span className="min-w-0 flex-1 truncate text-sm font-medium text-fg">
            {player.full_name}
          </span>
          <span className="tabular shrink-0 text-xs text-fg-muted">
            {player.projected_points.toFixed(1)}
          </span>
        </li>
      ))}
    </ul>
  </div>
);
