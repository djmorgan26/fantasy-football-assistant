// Auth types
export interface User {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
  has_espn_credentials: boolean;
  has_password: boolean;
  has_google: boolean;
  avatar_url: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  /** Google sign-in only: whether this call linked, created or resumed an account. */
  outcome?: 'signed_in' | 'linked' | 'created';
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

// Platform types
export type PlatformType = 'espn' | 'sleeper' | 'yahoo';

// League types
export interface League {
  id: number;
  platform: PlatformType;
  espn_league_id?: number;
  sleeper_league_id?: string;
  sleeper_user_id?: string;
  yahoo_league_key?: string;
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

export interface SleeperLeagueConnectionRequest {
  league_id: string;
  sleeper_user_id: string;
}

export interface LeagueConnectionResponse {
  success: boolean;
  message: string;
  league?: League;
  teams?: Team[];
}

export interface SleeperLeagueConnectionResponse {
  success: boolean;
  message: string;
  league_id: number;
  sleeper_league_id: string;
  league_name: string;
  teams_synced: number;
}

export interface SleeperUserLeaguesResponse {
  user_id: string;
  username: string;
  season: number;
  leagues: Array<Record<string, any>>;
}

// Team types
export interface Team {
  id: number;
  league_id: number;
  espn_team_id?: number;
  sleeper_roster_id?: number;
  sleeper_owner_id?: string;
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
  owner_user_id?: number;
}

export interface RosterResponse {
  team_id: number;
  week: number;
  roster: RosterPlayer[];
}

export interface RosterPlayer {
  player_id: number;
  full_name: string;
  first_name?: string;
  last_name?: string;
  /** ESPN defaultPositionId. A different id space from lineup_slot_id. */
  position_id: number;
  position_name: string;
  lineup_slot_id: number;
  lineup_slot_name: string;
  is_starter?: boolean;
  on_injured_reserve?: boolean;
  pro_team_id?: number;
  pro_team_abbr?: string;
  eligible_slots: number[];
  eligible_slot_names?: string[];
  /** ACTIVE | QUESTIONABLE | DOUBTFUL | OUT | INJURY_RESERVE | SUSPENSION */
  injury_status?: string;
  is_injured?: boolean;
  acquisition_type?: string;
  percent_owned?: number;
  percent_started?: number;
  average_draft_position?: number;
  positional_ranking?: number | null;
  total_ranking?: number | null;
  /** Fantasy points scored in the selected week. */
  applied_points?: number;
  /** Fantasy points projected for the selected week. */
  projected_points?: number;
  season_points?: number;
  season_projected_points?: number;
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

// Matchup types
export interface Matchup {
  id: number;
  matchup_id: number;
  league_id: number;
  week: number;
  home_team_id?: number;
  away_team_id?: number;
  home_score: number;
  away_score: number;
  home_projected_score?: number;
  away_projected_score?: number;
  is_playoff: boolean;
  winner: 'HOME' | 'AWAY' | 'TIE' | 'UNDECIDED';
  created_at: string;
  updated_at: string;
  home_team_name?: string;
  away_team_name?: string;
  home_team_location?: string;
  away_team_location?: string;
  home_team_nickname?: string;
  away_team_nickname?: string;
}

// Waiver budget types
export interface WaiverBudget {
  id: number;
  league_id: number;
  team_id: number;
  total_budget: number;
  current_budget: number;
  spent_budget: number;
  season_year: number;
  created_at: string;
  updated_at: string;
}

export interface WaiverTransaction {
  id: number;
  league_id: number;
  team_id: number;
  player_id: number;
  player_name: string;
  transaction_type: 'ADD' | 'DROP' | 'TRADE';
  bid_amount: number;
  status: 'PENDING' | 'SUCCESSFUL' | 'FAILED';
  week: number;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface TeamBudgetSummary {
  team_id: number;
  team_name: string;
  current_budget: number;
  spent_budget: number;
  total_budget: number;
  recent_transactions: WaiverTransaction[];
}

// Strategic suggestions types
export interface StrategicSuggestion {
  id: string;
  type: 'pickup' | 'drop' | 'trade' | 'lineup';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  reasoning: string;
  potential_impact: string;
  confidence_score: number;
  action_details?: {
    player_id?: number;
    player_name?: string;
    suggested_bid?: number;
    trade_targets?: number[];
    lineup_changes?: Record<string, string>;
  };
  context?: {
    current_matchup?: Matchup;
    budget_remaining?: number;
    upcoming_matchups?: Matchup[];
  };
}

export interface SuggestionFilters {
  type?: 'pickup' | 'drop' | 'trade' | 'lineup';
  priority?: 'high' | 'medium' | 'low';
  week?: number;
}

// Utility types
export type Position = 'QB' | 'RB' | 'WR' | 'TE' | 'K' | 'D/ST' | 'FLEX' | 'BENCH' | 'IR';

export interface PositionLimits {
  [key: string]: {
    limit: number;
  };
}

// Draft preparation & live draft assistant types
export interface ValueBoardPlayer {
  player_id: string;
  name: string;
  position: string;
  team?: string | null;
  projected_points: number;
  vbd: number;
  overall_rank?: number | null;
  position_rank?: number | null;
  tier?: number | null;
  adp?: number | null;
  bye_week?: number | null;
  age?: number | null;
  injury_status?: string | null;
}

export interface ValueBoardResponse {
  season: number;
  scoring: string;
  team_count: number;
  player_count: number;
  replacement_ranks: Record<string, number>;
  players: ValueBoardPlayer[];
}

export interface DraftPickRecommendation extends ValueBoardPlayer {
  need_bonus?: number | null;
  pick_score?: number | null;
  adp_delta?: number | null;
  is_value: boolean;
}

export interface DraftAdvice {
  recommended_player?: string | null;
  alternatives: string[];
  reasoning: string;
  strategy_note: string;
}

export interface DraftRosterPick {
  name: string;
  position?: string | null;
  team?: string | null;
  round?: number | null;
}

export interface DraftAssistResponse {
  draft_id: string;
  status?: string | null;
  round?: number | null;
  picks_made: number;
  team_count: number;
  scoring: string;
  user_roster: DraftRosterPick[];
  user_position_counts: Record<string, number>;
  current_pick?: number | null;
  next_user_pick?: number | null;
  picks_until_next?: number | null;
  on_the_clock: boolean;
  positional_runs: Record<string, number>;
  recommendations: DraftPickRecommendation[];
  ai_advice?: DraftAdvice | null;
  live_pick_tracking?: boolean;
  note?: string | null;
}

// Content & humor engine types
export type ContentType = 'weekly_recap' | 'power_rankings' | 'awards' | 'season_recap';

export interface HumorExample {
  title?: string;
  text: string;
  year?: number;
}

export interface ManagerPersona {
  name: string;
  team_name?: string;
  notes?: string;
  bits: string[];
}

export interface ContentProfile {
  league_id: number;
  voice_guide?: string | null;
  humor_examples: HumorExample[];
  personas: ManagerPersona[];
}

export interface WeeklyNarrative {
  week: number;
  team_count: number;
  median_score: number;
  average_score: number;
  highest_scorer?: { team_name: string; points: number } | null;
  lowest_scorer?: { team_name: string; points: number } | null;
  biggest_blowout?: { winner: string; loser: string; margin: number } | null;
  closest_game?: { winner: string; loser: string; margin: number } | null;
  lucky_wins: Array<{ team_name: string; points: number }>;
  unlucky_losses: Array<{ team_name: string; points: number }>;
  bench_blunder?: {
    team_name: string;
    bench_points: number;
    top_bench?: { name: string; points: number } | null;
  } | null;
  results: Array<Record<string, any>>;
  teams: Array<Record<string, any>>;
}

export interface GeneratedContent {
  content: string;
  content_type: string;
  generated_by: string;
  week?: number | null;
  league_name?: string | null;
  narrative?: WeeklyNarrative | null;
}
// ── Content board ──────────────────────────────────────────────────────────
// Typed reactions, not a like/dislike binary: a binary records *that* a post
// landed, these record *how*, which is the part the voice profile learns from.
export type ReactionKind = 'savage' | 'funny' | 'brutal' | 'smart' | 'cold';

export type PostKind =
  | 'post'
  | 'weekly_recap'
  | 'power_rankings'
  | 'awards'
  | 'trash_talk'
  | 'season_recap'
  | 'digest';

export interface BoardComment {
  id: number;
  post_id: number;
  parent_id?: number | null;
  body: string;
  author_id?: number | null;
  author_name: string;
  is_mine: boolean;
  created_at?: string;
}

export interface BoardPost {
  id: number;
  league_id: number;
  kind: PostKind;
  title?: string | null;
  body: string;
  media_paths: string[];
  week?: number | null;
  /** Written by the assistant rather than a person. Rated the same way. */
  is_ai: boolean;
  generated_by?: string | null;
  allow_training: boolean;
  author_id?: number | null;
  author_name: string;
  is_mine: boolean;
  score: number;
  reactions: Record<ReactionKind, number>;
  my_reactions: ReactionKind[];
  comment_count: number;
  comments: BoardComment[];
  created_at?: string;
}

export interface VoiceSample {
  id: number;
  title?: string | null;
  text: string;
  score: number;
  tags: string[];
  author_name?: string | null;
}

export interface BoardStats {
  posts: number;
  comments: number;
  reactions: number;
  voice_samples: number;
  top_reaction?: ReactionKind | null;
}

// ── News ───────────────────────────────────────────────────────────────────
export interface NewsArticle {
  id: string;
  headline: string;
  description: string;
  byline: string;
  published?: string | null;
  image?: string | null;
  url?: string | null;
  athletes: string[];
  teams: string[];
  category: string;
  /** The fantasy team in this league that rosters the player involved. */
  rostered_by?: string | null;
}

export interface LeagueNews {
  articles: NewsArticle[];
  rostered_count: number;
  league_name: string;
}

export interface NewsDigest {
  digest: string;
  generated_by: string;
  items: NewsArticle[];
}

export interface TrendingPlayer {
  sleeper_id: string;
  name: string;
  position?: string | null;
  team?: string | null;
  count: number;
  headshot?: string | null;
}

export interface ScoreboardSide {
  abbr?: string;
  name?: string;
  logo?: string;
  score?: string;
}

export interface ScoreboardGame {
  id: string;
  state: string;
  detail: string;
  home: ScoreboardSide;
  away: ScoreboardSide;
}

// ── The Commissioner ───────────────────────────────────────────────────────
export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatReply {
  reply: string;
  generated_by: string;
  /** What the answer was grounded on, e.g. ["standings", "your roster"]. */
  grounded_on: string[];
}

export interface PrimerAlert {
  player: string;
  slot: string;
  status: string;
  severity: 'out' | 'questionable';
}

export interface PrimerSwap {
  start: string;
  sit: string;
  slot: string;
  gain: number;
}

export interface WeeklyPrimer {
  week: number;
  team_name: string;
  record: string;
  opponent?: string | null;
  projected: number;
  starters: number;
  alerts: PrimerAlert[];
  best_swap?: PrimerSwap | null;
  trash_talk?: string | null;
}

// ── Game day ───────────────────────────────────────────────────────────────
/** pre = not kicked off · in = on the field · post = done · null = no game */
export type GameState = 'pre' | 'in' | 'post' | null;

export interface GamedayPlayer {
  player_id: number;
  name: string;
  position: string;
  slot: string;
  team: string | null;
  projected: number;
  points: number;
  injury_status?: string | null;
  game_state: GameState;
}

export interface GamedaySummary {
  playing_now: number;
  yet_to_play: number;
  finished: number;
  points: number;
  /** Projected points still to come, on the field or not yet kicked off. */
  points_in_play: number;
  projected_total: number;
}

export interface GamedaySide {
  name: string | null;
  summary: GamedaySummary;
  players: GamedayPlayer[];
}

export interface GamedayGame {
  id: string;
  state: Exclude<GameState, null>;
  detail: string;
  home: ScoreboardSide;
  away: ScoreboardSide;
  /** Your starters in this game. */
  mine: GamedayPlayer[];
  /** Your opponent's starters in this game. */
  theirs: GamedayPlayer[];
  /** One line on why this game matters to your matchup. */
  why: string;
  /** How much this game decides the matchup; the feed is sorted by it. */
  leverage: number;
}

export interface GameDay {
  week: number;
  my_team: GamedaySide;
  opponent: GamedaySide | null;
  games: GamedayGame[];
  /** Total games on the NFL slate, including ones nobody here is in. */
  slate_size: number;
}

// ── Across leagues ─────────────────────────────────────────────────────────
/** One league's holding of a player: yours, or your opponent's. */
export interface PlayerHolding {
  league_id: number;
  league: string;
  team: string;
  starting: boolean;
  slot: string | null;
  projected: number;
  points: number;
}

export interface PlayerAcrossLeagues {
  name: string;
  position: string | null;
  team: string | null;
  player_id: number | string | null;
  for: PlayerHolding[];
  against: PlayerHolding[];
}

/** A player you are simultaneously rooting for and against. */
export interface PlayerConflict extends PlayerAcrossLeagues {
  for_count: number;
  against_count: number;
  net: number;
  verdict: string;
}

/** A player you own in more than one league. */
export interface PlayerExposure extends PlayerAcrossLeagues {
  leagues: number;
  starting_in: number;
  projected: number;
}

export interface LeagueWeek {
  league_id: number;
  league: string;
  platform: string | null;
  week: number;
  team: string;
  record: string;
  opponent: string | null;
  points: number;
  opponent_points: number;
  projected: number;
  opponent_projected: number;
  margin: number;
  status: 'comfortable' | 'tight' | 'behind';
  alerts: { player: string; slot: string; status: string }[];
}

export interface Portfolio {
  leagues: number;
  teams: number;
  /** Leagues you are in but have not claimed a team in, so the view can say why. */
  unclaimed: { league_id: number; name: string }[];
  weeks: LeagueWeek[];
  conflicts: PlayerConflict[];
  exposure: PlayerExposure[];
  totals: { points: number; projected: number; winning: number; alerts: number };
}

// ---------------------------------------------------------------- action plan

export type ActionUrgency = 'critical' | 'high' | 'medium' | 'low';

export interface LineupHole {
  player: string;
  player_id: number | string;
  position: string;
  slot: string;
  status: string;
  points_lost: number;
}

export interface BenchOption {
  player: string;
  player_id: number | string;
  position: string;
  projected: number;
  last_week: number;
  team: string | null;
}

export interface WaiverTarget {
  player: string;
  player_id: number | string;
  position: string;
  team: string | null;
  projected: number;
  added_by: number;
  contested: boolean;
}

export interface FaabAdvice {
  remaining: number;
  total: number;
  spent_pct: number;
  suggested_bid: number;
  max_sensible: number;
  note: string | null;
}

export interface TradeAngle {
  team: string;
  they_need: string;
  they_can_spare: string;
  your_surplus_points: number;
}

export interface RosterAction {
  kind: string;
  urgency: ActionUrgency;
  hole: LineupHole;
  start_instead: BenchOption | null;
  other_bench: BenchOption[];
  waiver_targets: WaiverTarget[];
  faab: FaabAdvice | null;
  trades: TradeAngle[];
}

export interface LineupRisk {
  player: string;
  slot: string;
  status: string;
  projected: number;
}

export interface ActionPlan {
  league_id: number;
  league: string;
  team: string;
  week: number;
  summary: string | null;
  actions: RosterAction[];
  risks: LineupRisk[];
  depth: Record<string, { count: number; starters: number; bench_points: number }>;
  budget: { remaining: number | null; total: number | null };
  all_clear: boolean;
}
