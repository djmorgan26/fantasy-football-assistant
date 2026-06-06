import api from './api';
import { ValueBoardResponse, DraftAssistResponse } from '@/types';

export const draftService = {
  /** Value board tuned to a league's exact scoring settings. */
  async getLeagueValueBoard(leagueId: number, limit = 200): Promise<ValueBoardResponse> {
    const response = await api.get<ValueBoardResponse>(`/draft/value-board/${leagueId}`, {
      params: { limit },
    });
    return response.data;
  },

  /** Generic preset rankings (no league required). */
  async getGenericRankings(
    scoringType = 'ppr',
    teamCount = 12,
    limit = 200
  ): Promise<ValueBoardResponse> {
    const response = await api.get<ValueBoardResponse>('/draft/rankings', {
      params: { scoring_type: scoringType, team_count: teamCount, limit },
    });
    return response.data;
  },

  /**
   * Live draft assistant. Pass ai=false for the fast, pollable board; ai=true
   * only on demand (it runs the LLM and is slower).
   */
  async getDraftAssist(
    leagueId: number,
    ai = false,
    limit = 12
  ): Promise<DraftAssistResponse> {
    const response = await api.get<DraftAssistResponse>(`/draft/assist/${leagueId}`, {
      params: { ai, limit },
    });
    return response.data;
  },
};
