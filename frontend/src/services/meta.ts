import api from './api';

export interface AppMeta {
  mock_mode: boolean;
  app_name: string;
  version: string;
  demo_credentials?: {
    email: string;
    password: string;
  };
  /**
   * Google OAuth client id, served by the API rather than baked in at build
   * time so it can be rotated without rebuilding the frontend. Empty or
   * absent means Google sign-in is not configured, and the button is hidden.
   */
  google_client_id?: string;
}

export const metaService = {
  async getMeta(): Promise<AppMeta> {
    const response = await api.get<AppMeta>('/meta');
    return response.data;
  },
};
