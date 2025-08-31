import api, { setAuthToken, removeAuthToken } from './api';
import { AuthResponse, LoginRequest, RegisterRequest, User } from '@/types';

export const authService = {
  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/login', credentials);
    const { access_token } = response.data;
    setAuthToken(access_token);
    return response.data;
  },

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    const response = await api.post<AuthResponse>('/auth/register', userData);
    const { access_token } = response.data;
    setAuthToken(access_token);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  async updateProfile(updates: {
    full_name?: string;
    current_password?: string;
    new_password?: string;
    espn_s2?: string;
    espn_swid?: string;
  }): Promise<User> {
    const response = await api.put<User>('/auth/me', updates);
    return response.data;
  },

  logout(): void {
    removeAuthToken();
  },

  isAuthenticated(): boolean {
    return Boolean(localStorage.getItem('access_token'));
  },
};