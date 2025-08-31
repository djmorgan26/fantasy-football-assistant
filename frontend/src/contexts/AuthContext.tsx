import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, LoginRequest, RegisterRequest, AuthResponse, ApiError } from '@/types';
import { authService } from '@/services/auth';
import toast from 'react-hot-toast';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  updateProfile: (updates: {
    full_name?: string;
    current_password?: string;
    new_password?: string;
    espn_s2?: string;
    espn_swid?: string;
  }) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = Boolean(user);

  // Check if user is logged in on app start
  useEffect(() => {
    const checkAuthStatus = async () => {
      if (authService.isAuthenticated()) {
        try {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        } catch (error) {
          // Token might be expired or invalid
          authService.logout();
        }
      }
      setIsLoading(false);
    };

    checkAuthStatus();
  }, []);

  const login = async (credentials: LoginRequest): Promise<void> => {
    try {
      setIsLoading(true);
      const response: AuthResponse = await authService.login(credentials);
      setUser(response.user);
      toast.success('Login successful!');
    } catch (error) {
      const apiError = error as ApiError;
      toast.error(apiError.detail || 'Login failed');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterRequest): Promise<void> => {
    try {
      setIsLoading(true);
      const response: AuthResponse = await authService.register(userData);
      setUser(response.user);
      toast.success('Registration successful!');
    } catch (error) {
      const apiError = error as ApiError;
      toast.error(apiError.detail || 'Registration failed');
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = (): void => {
    authService.logout();
    setUser(null);
    toast.success('Logged out successfully');
  };

  const updateProfile = async (updates: {
    full_name?: string;
    current_password?: string;
    new_password?: string;
    espn_s2?: string;
    espn_swid?: string;
  }): Promise<void> => {
    try {
      const updatedUser = await authService.updateProfile(updates);
      setUser(updatedUser);
      toast.success('Profile updated successfully!');
    } catch (error) {
      const apiError = error as ApiError;
      toast.error(apiError.detail || 'Profile update failed');
      throw error;
    }
  };

  const refreshUser = async (): Promise<void> => {
    try {
      if (authService.isAuthenticated()) {
        const userData = await authService.getCurrentUser();
        setUser(userData);
      }
    } catch (error) {
      console.error('Failed to refresh user data:', error);
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    updateProfile,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};