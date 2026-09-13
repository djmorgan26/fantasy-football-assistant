import api from './api';
import { Portfolio } from '@/types';

export const portfolioService = {
  async get(): Promise<Portfolio> {
    const response = await api.get<Portfolio>('/portfolio');
    return response.data;
  },
};
