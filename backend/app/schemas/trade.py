from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# ESPN player IDs are integers; mock mode (and some other sources) use string
# IDs like "p0001". The trade endpoints only compare IDs, so accept both.
PlayerId = Union[int, str]


class TradeStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TradeCreate(BaseModel):
    league_id: int = Field(gt=0, description="League ID must be positive")
    proposing_team_id: int = Field(gt=0, description="Proposing team ID must be positive")
    receiving_team_id: int = Field(gt=0, description="Receiving team ID must be positive")
    give_players: List[PlayerId] = Field(min_length=1, max_length=10, description="Player IDs being given away (1-10 players)")
    receive_players: List[PlayerId] = Field(min_length=1, max_length=10, description="Player IDs being received (1-10 players)")

    @staticmethod
    def validate_different_teams(proposing_team_id: int, receiving_team_id: int) -> None:
        if proposing_team_id == receiving_team_id:
            raise ValueError("Cannot trade with yourself")

    def model_post_init(self, __context):
        self.validate_different_teams(self.proposing_team_id, self.receiving_team_id)


class TradeAnalysisRequest(BaseModel):
    league_id: int = Field(gt=0, description="League ID must be positive")
    proposing_team_id: int = Field(gt=0, description="Proposing team ID must be positive")
    receiving_team_id: int = Field(gt=0, description="Receiving team ID must be positive")
    give_players: List[PlayerId] = Field(min_length=1, max_length=10, description="1-10 players to give")
    receive_players: List[PlayerId] = Field(min_length=1, max_length=10, description="1-10 players to receive")

    @staticmethod
    def validate_different_teams(proposing_team_id: int, receiving_team_id: int) -> None:
        if proposing_team_id == receiving_team_id:
            raise ValueError("Cannot analyze trade with same team")

    def model_post_init(self, __context):
        self.validate_different_teams(self.proposing_team_id, self.receiving_team_id)


class TradeResponse(BaseModel):
    id: int
    league_id: int
    proposing_team_id: int
    receiving_team_id: int
    proposed_players: Dict[str, List[PlayerId]]
    status: TradeStatusEnum
    fairness_score: Optional[float] = None
    value_difference: Optional[float] = None
    analysis_summary: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TradeAnalysisResponse(BaseModel):
    is_valid: bool
    fairness_score: Optional[float] = None
    value_difference: Optional[float] = None
    analysis_summary: str
    recommendations: List[str] = []
    player_details: Dict[str, Any] = {}

# ---------------------------------------------------------------------------
# The trade workbench
#
# These back the rebuilt Trades page. They deliberately address players and
# teams by *our* database ids rather than a platform's, so the same request
# shape works for an ESPN league and a Sleeper one. The older
# TradeAnalysisRequest above still speaks ESPN team ids and is kept for the
# existing /analyze endpoint.
# ---------------------------------------------------------------------------


class TradePlayer(BaseModel):
    """A player as a trade card shows him."""

    player_id: str
    full_name: str
    position: str
    pro_team: Optional[str] = None
    projected_points: float = 0.0
    injury_status: Optional[str] = None


class TradePartySchema(BaseModel):
    team_id: Optional[int] = None
    team_name: str
    platform_team_id: Optional[Union[int, str]] = None
    sends: List[TradePlayer] = []
    has_consented: bool = False


class LeagueTrade(BaseModel):
    """A pending or historical trade, normalized across platforms."""

    trade_id: str
    status: str
    direction: str  # incoming | outgoing | other
    parties: List[TradePartySchema]
    proposed_at: Optional[str] = None
    week: Optional[int] = None
    source: str


class TradeOffersResponse(BaseModel):
    league_id: int
    platform: str
    my_team_id: Optional[int] = None
    pending: List[LeagueTrade] = []
    history: List[LeagueTrade] = []
    # Why the pending list might be empty, when it is empty for a reason the
    # user can do something about.
    pending_available: bool = True
    pending_notice: Optional[str] = None


class PositionDepth(BaseModel):
    rostered: int
    startable: int
    required: int
    surplus: int
    best: float


class TradeSide(BaseModel):
    team_id: int
    team_name: str
    lineup_before: float
    lineup_after: float
    lineup_delta: float
    value_out: float
    value_in: float
    value_delta: float
    depth_before: Dict[str, PositionDepth] = {}
    depth_after: Dict[str, PositionDepth] = {}


class PlayoffOdds(BaseModel):
    before: float
    after: float
    delta: float
    iterations: int
    weeks_simulated: int
    playoff_spots: int
    schedule_source: str  # "platform" when the real remaining schedule was used


class TradeEvaluationRequest(BaseModel):
    """Evaluate a trade between two teams, addressed by our own ids."""

    team_a_id: int = Field(gt=0, description="Your team")
    team_b_id: int = Field(gt=0, description="The other team")
    team_a_sends: List[str] = Field(
        min_length=1, max_length=10, description="Player ids team A gives up"
    )
    team_b_sends: List[str] = Field(
        min_length=1, max_length=10, description="Player ids team B gives up"
    )
    include_odds: bool = True
    include_ai: bool = True

    def model_post_init(self, __context):
        if self.team_a_id == self.team_b_id:
            raise ValueError("Cannot trade with yourself")


class TradeEvaluation(BaseModel):
    verdict: str  # accept | lean_accept | neutral | lean_reject | reject
    headline: str
    fairness_score: float
    you: TradeSide
    them: TradeSide
    playoff_odds: Optional[PlayoffOdds] = None
    risks: List[str] = []
    ai_summary: Optional[str] = None
    ai_points: List[str] = []
    counter_suggestion: Optional[str] = None
    players_you_send: List[TradePlayer] = []
    players_you_get: List[TradePlayer] = []
    # Sourced facts per player id: depth-chart role, injury detail, recent
    # headlines. Empty when the wire and the player index are both unavailable.
    intel: Dict[str, Any] = {}


class TradeIdeaSchema(BaseModel):
    partner_team_id: int
    partner_team_name: str
    give: List[TradePlayer]
    receive: List[TradePlayer]
    my_lineup_delta: float
    their_lineup_delta: float
    mutual_gain: float
    fairness: float


class TradeFinderResponse(BaseModel):
    league_id: int
    my_team_id: int
    ideas: List[TradeIdeaSchema] = []
    needs: List[str] = []
    surplus: List[str] = []


class SleeperTokenRequest(BaseModel):
    """Connect a Sleeper token so pending offers become visible."""

    token: str = Field(min_length=10, max_length=4096)


class CounterOfferSchema(BaseModel):
    """An alternative package, scored against the offer already on the table."""

    kind: str  # ask_for_more | different_target | give_less | different_piece | swap_both
    give: List[TradePlayer]
    receive: List[TradePlayer]
    my_lineup_delta: float
    their_lineup_delta: float
    fairness: float
    # What separates a counter from a fresh idea: both are measured against
    # the original offer rather than against nothing.
    gain_vs_original: float
    cost_to_them: float
    likelihood: str  # easy_ask | fair_ask | big_ask | unlikely
    likelihood_reason: str
    rationale: str


class CounterRequest(BaseModel):
    """Explore counters to an offer. The offer itself is the baseline."""

    team_a_id: int = Field(gt=0, description="Your team")
    team_b_id: int = Field(gt=0, description="The team that made the offer")
    team_a_sends: List[str] = Field(min_length=1, max_length=10)
    team_b_sends: List[str] = Field(min_length=1, max_length=10)
    limit: int = Field(default=6, ge=1, le=12)
    include_ai: bool = True

    def model_post_init(self, __context):
        if self.team_a_id == self.team_b_id:
            raise ValueError("Cannot counter yourself")


class CounterResponse(BaseModel):
    league_id: int
    # The verdict on the offer as written, so the counters have a baseline the
    # user can see rather than one they have to remember.
    original_verdict: str
    original_lineup_delta: float
    original_headline: str
    counters: List[CounterOfferSchema] = []
    # Said plainly when there is nothing better, which is itself an answer.
    summary: str
    ai_summary: Optional[str] = None
