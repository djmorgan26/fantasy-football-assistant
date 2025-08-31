import { clsx, type ClassValue } from 'clsx';

// Utility for conditional class names
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

// Format currency/points
export const formatPoints = (points: number): string => {
  return points.toFixed(1);
};

// Format dates
export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString();
};

export const formatDateTime = (dateString: string): string => {
  return new Date(dateString).toLocaleString();
};

// Position color mapping
export const getPositionColor = (position: string): string => {
  switch (position.toUpperCase()) {
    case 'QB':
      return 'text-red-600 bg-red-100';
    case 'RB':
      return 'text-green-600 bg-green-100';
    case 'WR':
      return 'text-blue-600 bg-blue-100';
    case 'TE':
      return 'text-yellow-600 bg-yellow-100';
    case 'K':
      return 'text-purple-600 bg-purple-100';
    case 'D/ST':
    case 'DST':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
};

// Injury status color mapping
export const getInjuryStatusColor = (status?: string): string => {
  if (!status || status === 'ACTIVE') return 'text-green-600';
  
  switch (status.toUpperCase()) {
    case 'QUESTIONABLE':
      return 'text-yellow-600';
    case 'DOUBTFUL':
      return 'text-orange-600';
    case 'OUT':
    case 'IR':
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
};

// Team record formatting
export const formatRecord = (wins: number, losses: number, ties: number = 0): string => {
  return ties > 0 ? `${wins}-${losses}-${ties}` : `${wins}-${losses}`;
};

// Calculate winning percentage
export const getWinPercentage = (wins: number, losses: number, ties: number = 0): number => {
  const totalGames = wins + losses + ties;
  if (totalGames === 0) return 0;
  return ((wins + ties * 0.5) / totalGames) * 100;
};

// Validate ESPN League ID
export const isValidESPNLeagueId = (leagueId: string): boolean => {
  const id = parseInt(leagueId);
  return !isNaN(id) && id > 0;
};

// Extract ESPN cookies from text
export const extractESPNCookies = (cookieText: string): { espn_s2?: string; swid?: string } => {
  const cookies: { espn_s2?: string; swid?: string } = {};
  
  // Extract espn_s2
  const s2Match = cookieText.match(/espn_s2=([^;]+)/i);
  if (s2Match) {
    cookies.espn_s2 = s2Match[1].trim();
  }
  
  // Extract SWID
  const swidMatch = cookieText.match(/SWID=([^;]+)/i);
  if (swidMatch) {
    cookies.swid = swidMatch[1].trim();
  }
  
  return cookies;
};

// Debounce function
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  delay: number
): ((...args: Parameters<T>) => void) => {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
};

// Local storage utilities
export const storage = {
  get: <T>(key: string, defaultValue: T): T => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },
  
  set: <T>(key: string, value: T): void => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Error saving to localStorage:', error);
    }
  },
  
  remove: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.error('Error removing from localStorage:', error);
    }
  },
};

// Error handling utilities
export const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return 'An unexpected error occurred';
};