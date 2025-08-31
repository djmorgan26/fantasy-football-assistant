import axios, { AxiosResponse, AxiosError } from 'axios';
import { ApiError } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth token management
const getAuthToken = (): string | null => {
  return localStorage.getItem('access_token');
};

const setAuthToken = (token: string): void => {
  localStorage.setItem('access_token', token);
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
};

const removeAuthToken = (): void => {
  localStorage.removeItem('access_token');
  delete api.defaults.headers.common['Authorization'];
};

// Initialize auth token if it exists
const token = getAuthToken();
if (token) {
  api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      removeAuthToken();
      // Redirect to login if not already there
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    
    // Transform error to our ApiError type
    const apiError: ApiError = {
      detail: error.response?.data?.detail || error.message || 'An unexpected error occurred',
      status: error.response?.status,
    };
    
    return Promise.reject(apiError);
  }
);

export { api, setAuthToken, removeAuthToken, getAuthToken };
export default api;