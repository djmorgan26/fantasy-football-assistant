import api from './api';
import { TradeAnalysisRequest, TradeAnalysisResponse, Trade } from '@/types';

export const tradesService = {
  async analyzeTrade(analysisRequest: TradeAnalysisRequest): Promise<TradeAnalysisResponse> {
    const response = await api.post<TradeAnalysisResponse>('/trades/analyze', analysisRequest);
    return response.data;
  },

  async createTrade(tradeData: {
    league_id: number;
    proposing_team_id: number;
    receiving_team_id: number;
    give_players: number[];
    receive_players: number[];
  }): Promise<Trade> {
    const response = await api.post<Trade>('/trades/', tradeData);
    return response.data;
  },

  async getUserTrades(): Promise<Trade[]> {
    const response = await api.get<Trade[]>('/trades/');
    return response.data;
  },

  async getTrade(tradeId: number): Promise<Trade> {
    const response = await api.get<Trade>(`/trades/${tradeId}`);
    return response.data;
  },
};