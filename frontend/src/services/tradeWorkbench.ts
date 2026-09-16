import api from './api';
import {
  CounterResult,
  TradeEvaluation,
  TradeEvaluationRequest,
  TradeFinderResult,
  TradeMarket,
  TradeOffers,
} from '@/types';

/**
 * The rebuilt trade endpoints. Kept separate from `services/trades.ts`, which
 * still serves the older ESPN-player-id analyzer and the saved-trade records.
 */
export const tradeWorkbenchService = {
  async getOffers(leagueId: number): Promise<TradeOffers> {
    const { data } = await api.get<TradeOffers>(`/trades/league/${leagueId}/offers`);
    return data;
  },

  async getMarket(leagueId: number): Promise<TradeMarket> {
    const { data } = await api.get<TradeMarket>(`/trades/league/${leagueId}/market`);
    return data;
  },

  async evaluate(
    leagueId: number,
    request: TradeEvaluationRequest
  ): Promise<TradeEvaluation> {
    const { data } = await api.post<TradeEvaluation>(
      `/trades/league/${leagueId}/evaluate`,
      request
    );
    return data;
  },

  async findTrades(leagueId: number, limit = 10): Promise<TradeFinderResult> {
    const { data } = await api.get<TradeFinderResult>(
      `/trades/league/${leagueId}/finder`,
      { params: { limit } }
    );
    return data;
  },

  /**
   * Counter-offers to an offer already on the table. Its own call rather than
   * part of the evaluation because the user triggers it deliberately, and it
   * is worth running whatever the verdict was.
   */
  async counters(
    leagueId: number,
    request: TradeEvaluationRequest & { limit?: number }
  ): Promise<CounterResult> {
    const { data } = await api.post<CounterResult>(
      `/trades/league/${leagueId}/counters`,
      request
    );
    return data;
  },

  async connectSleeperToken(leagueId: number, token: string): Promise<void> {
    await api.post(`/trades/league/${leagueId}/sleeper-token`, { token });
  },

  async disconnectSleeperToken(leagueId: number): Promise<void> {
    await api.delete(`/trades/league/${leagueId}/sleeper-token`);
  },
};
