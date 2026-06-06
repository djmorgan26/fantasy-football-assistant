import api from './api';

export interface AppMeta {
  mock_mode: boolean;
  app_name: string;
  version: string;
  demo_credentials?: {
    email: string;
    password: string;
  };
}

export const metaService = {
  async getMeta(): Promise<AppMeta> {
    const response = await api.get<AppMeta>('/meta');
    return response.data;
  },
};
