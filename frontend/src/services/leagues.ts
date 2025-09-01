import api from './api';
import { League, LeagueConnectionRequest, LeagueConnectionResponse, Matchup, TeamBudgetSummary } from '@/types';

export const leaguesService = {
  async connectLeague(connectionData: LeagueConnectionRequest): Promise<LeagueConnectionResponse> {
    const response = await api.post<LeagueConnectionResponse>('/leagues/connect', connectionData);
    return response.data;
  },

  async getUserLeagues(): Promise<League[]> {
    const response = await api.get<League[]>('/leagues/');
    return response.data;
  },

  async getLeague(leagueId: number): Promise<League> {
    const response = await api.get<League>(`/leagues/${leagueId}`);
    return response.data;
  },

  async disconnectLeague(leagueId: number): Promise<{ message: string }> {
    const response = await api.delete(`/leagues/${leagueId}`);
    return response.data;
  },

  async syncLeague(leagueId: number): Promise<LeagueConnectionResponse> {
    const response = await api.post<LeagueConnectionResponse>(`/leagues/${leagueId}/sync`);
    return response.data;
  },

  async getMatchups(leagueId: number, week?: number): Promise<Matchup[]> {
    const params = week ? { week } : {};
    const response = await api.get<Matchup[]>(`/leagues/${leagueId}/matchups`, { params });
    return response.data;
  },

  async getWaiverBudgets(leagueId: number): Promise<TeamBudgetSummary[]> {
    const response = await api.get<TeamBudgetSummary[]>(`/leagues/${leagueId}/waiver-budgets`);
    return response.data;
  },
};