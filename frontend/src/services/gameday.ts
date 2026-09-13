import api from './api';
import { GameDay } from '@/types';

export const gamedayService = {
  async get(leagueId: number): Promise<GameDay> {
    const response = await api.get<GameDay>(`/gameday/${leagueId}`);
    return response.data;
  },
};
