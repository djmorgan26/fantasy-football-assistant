import api from './api';
import { PlayerSearchRequest, PlayerSearchResponse, Player } from '@/types';

export const playersService = {
  async searchPlayers(searchRequest: PlayerSearchRequest): Promise<PlayerSearchResponse> {
    const response = await api.post<PlayerSearchResponse>('/players/search', searchRequest);
    return response.data;
  },

  async getAvailablePlayers(
    leagueId: number,
    week?: number,
    position?: string
  ): Promise<{
    players: Player[];
    total_count: number;
    week?: number;
    position_filter?: string;
  }> {
    const params: Record<string, any> = {};
    if (week) params.week = week;
    if (position) params.position = position;
    
    const response = await api.get(`/players/league/${leagueId}/available`, { params });
    return response.data;
  },
};