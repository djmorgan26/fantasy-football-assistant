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

// Position color mapping — single source of truth across the app.
// Dark-mode aware. Keys cover ESPN + Sleeper position spellings.
const NEUTRAL_POSITION_COLOR =
  'bg-surface-sunken text-fg-muted dark:bg-surface-sunken dark:text-fg-muted';

const POSITION_COLORS: Record<string, string> = {
  QB: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  RB: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  WR: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  TE: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  K: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  FLEX: 'bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300',
};

// Defense spellings all resolve to a neutral chip (keep test: D/ST -> gray).
['DEF', 'DST', 'D/ST', 'D-ST'].forEach((k) => {
  POSITION_COLORS[k] = 'bg-gray-200 text-gray-700 dark:bg-gray-700/50 dark:text-gray-300';
});

export const getPositionColor = (position: string): string => {
  if (!position) return NEUTRAL_POSITION_COLOR;
  return POSITION_COLORS[position.toUpperCase()] || NEUTRAL_POSITION_COLOR;
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