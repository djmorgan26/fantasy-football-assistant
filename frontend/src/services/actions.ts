import api from './api';
import { ActionPlan } from '@/types';

export const actionsService = {
  async get(leagueId: number): Promise<ActionPlan> {
    const response = await api.get<ActionPlan>(`/actions/${leagueId}`);
    return response.data;
  },
};
