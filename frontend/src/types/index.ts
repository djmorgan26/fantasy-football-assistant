// Auth types
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  has_espn_credentials: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  espn_s2?: string;
  espn_swid?: string;
}

// League types
export interface League {
  id: number;
  espn_league_id: number;
  name: string;
  season_year: number;
  size: number;
  scoring_type: string;
  current_week: number;
  is_public: boolean;
  is_active: boolean;
  roster_settings?: Record<string, any>;
  scoring_settings?: Record<string, any>;
  created_at: string;
  last_synced: string | null;
}

export interface LeagueConnectionRequest {
  league_id: number;
  espn_s2?: string;
  espn_swid?: string;
}

export interface LeagueConnectionResponse {
  success: boolean;
  message: string;
  league?: League;
  teams?: Team[];
}

// Team types
export interface Team {
  id: number;
  espn_team_id: number;
  name: string;
  location?: string;
  nickname?: string;
  abbreviation?: string;
  logo_url?: string;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  points_against: number;
  current_roster?: Player[];
}

export interface RosterResponse {
  team_id: number;
  week: number;
  roster: RosterPlayer[];
}

export interface RosterPlayer {
  player_id: number;
  full_name: string;
  position_id: number;
  position_name: string;
  lineup_slot_id: number;
  lineup_slot_name: string;
  pro_team_id?: number;
  eligible_slots: number[];
  stats?: PlayerStats;
}

// Player types
export interface Player {
  id: number;
  espn_player_id: number;
  full_name: string;
  first_name?: string;
  last_name?: string;
  position_id: number;
  position_name?: string;
  pro_team_id?: number;
  pro_team_abbr?: string;
  eligible_slots?: number[];
  is_active: boolean;
  injury_status?: string;
  season_stats?: Record<string, any>;
  last_week_points: number;
  season_points: number;
  average_points: number;
  latest_news?: string;
  news_updated?: string;
  projected_points?: number;
  ownership_percentage?: number;
}

export interface PlayerStats {
  actual?: Record<string, number>;
  projected?: Record<string, number>;
}

export interface PlayerSearchRequest {
  league_id: number;
  week?: number;
  position?: string;
  search_term?: string;
  available_only: boolean;
}

export interface PlayerSearchResponse {
  players: Player[];
  total_count: number;
}

// Trade types
export interface TradeAnalysisRequest {
  league_id: number;
  proposing_team_id: number;
  receiving_team_id: number;
  give_players: number[];
  receive_players: number[];
}

export interface TradeAnalysisResponse {
  is_valid: boolean;
  fairness_score?: number;
  value_difference?: number;
  analysis_summary: string;
  recommendations: string[];
  player_details: Record<string, any>;
}

export interface Trade {
  id: number;
  league_id: number;
  proposing_team_id: number;
  receiving_team_id: number;
  proposed_players: {
    give: number[];
    receive: number[];
  };
  status: 'pending' | 'accepted' | 'rejected' | 'expired' | 'cancelled';
  fairness_score?: number;
  value_difference?: number;
  analysis_summary?: string;
  created_at: string;
  expires_at?: string;
}

// API error types
export interface ApiError {
  detail: string;
  status?: number;
}

// UI state types
export interface LoadingState {
  isLoading: boolean;
  error?: string;
}

// Utility types
export type Position = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'D/ST' | 'FLEX' | 'BENCH' | 'IR';

export interface PositionLimits {
  [key: string]: {
    limit: number;
  };
}