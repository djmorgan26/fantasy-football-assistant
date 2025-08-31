import api from './api';
import { Team, RosterResponse } from '@/types';

export const teamsService = {
  async getLeagueTeams(leagueId: number): Promise<Team[]> {
    const response = await api.get<Team[]>(`/teams/league/${leagueId}`);
    return response.data;
  },

  async getTeam(teamId: number): Promise<Team> {
    const response = await api.get<Team>(`/teams/${teamId}`);
    return response.data;
  },

  async getTeamRoster(teamId: number, week?: number): Promise<RosterResponse> {
    const params = week ? { week } : {};
    const response = await api.get<RosterResponse>(`/teams/${teamId}/roster`, { params });
    return response.data;
  },
};