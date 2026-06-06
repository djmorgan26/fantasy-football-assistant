"""
Draft Service for Fantasy Football Draft Preparation

Builds a league-scoring-aware value board and a live draft assistant on top of
the free Sleeper API. The key idea: instead of generic rankings, we project
fantasy points using YOUR league's exact scoring settings, then convert those
projections into Value-Based Drafting (VBD) scores so picks reflect scarcity at
each position.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import structlog

from app.services.sleeper_service import SleeperService, SleeperError

logger = structlog.get_logger()

# Positions we build a value board for
DRAFTABLE_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}

# Default number of starting slots per position for a typical lineup.
# Used to compute replacement level when a league's roster_positions are unknown.
DEFAULT_STARTERS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}

# Positions eligible to fill a FLEX slot
FLEX_POSITIONS = ("RB", "WR", "TE")

# Default scoring weights when a league's custom scoring_settings are unavailable.
# Keys match Sleeper's stat naming so they dot-product cleanly against projections.
DEFAULT_SCORING = {
    "standard": {
        "pass_yd": 0.04, "pass_td": 4, "pass_int": -1,
        "rush_yd": 0.1, "rush_td": 6,
        "rec": 0.0, "rec_yd": 0.1, "rec_td": 6,
        "fum_lost": -2,
    },
    "half_ppr": {
        "pass_yd": 0.04, "pass_td": 4, "pass_int": -1,
        "rush_yd": 0.1, "rush_td": 6,
        "rec": 0.5, "rec_yd": 0.1, "rec_td": 6,
        "fum_lost": -2,
    },
    "ppr": {
        "pass_yd": 0.04, "pass_td": 4, "pass_int": -1,
        "rush_yd": 0.1, "rush_td": 6,
        "rec": 1.0, "rec_yd": 0.1, "rec_td": 6,
        "fum_lost": -2,
    },
}

# Precomputed Sleeper projection point fields, by scoring type, used as a fallback
PRECOMPUTED_POINTS_FIELD = {
    "standard": "pts_std",
    "half_ppr": "pts_half_ppr",
    "ppr": "pts_ppr",
}


class DraftService:
    """Builds value boards and live draft recommendations from Sleeper data."""

    def __init__(self):
        self.sleeper = SleeperService()
        # Cache the large all-players payload (~10MB) to avoid refetching constantly
        self._players_cache: Optional[Dict[str, Any]] = None
        self._players_cached_at: Optional[datetime] = None
        self._players_ttl = timedelta(hours=12)

    # ---------------------------------------------------------------- helpers

    async def _get_players(self) -> Dict[str, Any]:
        """Get all NFL players, cached in memory for a few hours."""
        now = datetime.utcnow()
        if (
            self._players_cache is not None
            and self._players_cached_at is not None
            and now - self._players_cached_at < self._players_ttl
        ):
            return self._players_cache

        players = await self.sleeper.get_all_players()
        self._players_cache = players
        self._players_cached_at = now
        return players

    @staticmethod
    def _resolve_scoring_weights(
        scoring_settings: Optional[Dict[str, Any]],
        scoring_type: str,
    ) -> Tuple[Dict[str, float], bool]:
        """
        Decide which scoring weights to use.

        Returns (weights, is_custom). If the league exposes real scoring_settings
        we use those (most accurate); otherwise we fall back to a default table
        keyed by scoring_type (standard / half_ppr / ppr).
        """
        if scoring_settings:
            # Sleeper scoring_settings is already stat -> points; keep numeric values
            weights = {
                k: float(v)
                for k, v in scoring_settings.items()
                if isinstance(v, (int, float))
            }
            if weights:
                return weights, True

        scoring_type = (scoring_type or "ppr").lower()
        if scoring_type not in DEFAULT_SCORING:
            scoring_type = "ppr"
        return DEFAULT_SCORING[scoring_type], False

    @staticmethod
    def _project_points(
        proj: Dict[str, Any],
        weights: Dict[str, float],
        is_custom: bool,
        scoring_type: str,
    ) -> float:
        """Project a single player's season fantasy points."""
        if is_custom:
            total = 0.0
            for stat, weight in weights.items():
                value = proj.get(stat)
                if isinstance(value, (int, float)):
                    total += value * weight
            return round(total, 1)

        # Fallback: prefer Sleeper's precomputed point field for the scoring type
        field = PRECOMPUTED_POINTS_FIELD.get(scoring_type, "pts_ppr")
        if isinstance(proj.get(field), (int, float)):
            return round(float(proj[field]), 1)

        # Last resort: dot-product the default weights against raw stats
        total = 0.0
        for stat, weight in weights.items():
            value = proj.get(stat)
            if isinstance(value, (int, float)):
                total += value * weight
        return round(total, 1)

    @staticmethod
    def _starters_from_roster_positions(
        roster_positions: Optional[List[str]],
    ) -> Tuple[Dict[str, int], int]:
        """
        Derive starting-slot counts per position plus the number of FLEX slots
        from a league's roster_positions list (Sleeper format).
        """
        if not roster_positions:
            return dict(DEFAULT_STARTERS), 1

        starters: Dict[str, int] = {p: 0 for p in DRAFTABLE_POSITIONS}
        flex = 0
        for slot in roster_positions:
            if slot in starters:
                starters[slot] += 1
            elif slot in ("FLEX", "WRRB_FLEX", "REC_FLEX", "WRRB", "SUPER_FLEX"):
                flex += 1
        # If the list had no recognizable starters, fall back to defaults
        if sum(starters.values()) == 0:
            return dict(DEFAULT_STARTERS), max(flex, 1)
        return starters, flex

    @classmethod
    def _replacement_ranks(
        cls,
        team_count: int,
        roster_positions: Optional[List[str]],
    ) -> Dict[str, int]:
        """
        Compute the replacement-level rank within each position. A player's value
        over this baseline (VBD) is what actually matters on draft day, because it
        reflects how much better they are than a freely available starter.
        """
        starters, flex = cls._starters_from_roster_positions(roster_positions)

        # Distribute FLEX slots across RB/WR/TE (roughly: most leagues flex RB/WR)
        flex_share = {"RB": 0.45, "WR": 0.45, "TE": 0.10}

        ranks: Dict[str, int] = {}
        for pos in DRAFTABLE_POSITIONS:
            base = starters.get(pos, 0)
            extra = flex * flex_share.get(pos, 0.0) if pos in FLEX_POSITIONS else 0.0
            replacement = round((base + extra) * team_count)
            # Guarantee at least one drafted player per position defines replacement
            ranks[pos] = max(replacement, team_count if pos in ("QB", "RB", "WR") else 1)
        return ranks

    @staticmethod
    def _assign_tiers(players: List[Dict[str, Any]]) -> None:
        """
        Assign positional tiers in place using gap-based clustering: a new tier
        starts whenever the projected-points drop to the next player is large
        relative to the spread of that position.
        """
        by_pos: Dict[str, List[Dict[str, Any]]] = {}
        for p in players:
            by_pos.setdefault(p["position"], []).append(p)

        for pos, group in by_pos.items():
            group.sort(key=lambda x: x["projected_points"], reverse=True)
            if not group:
                continue
            points = [p["projected_points"] for p in group]
            spread = (points[0] - points[-1]) or 1.0
            # A drop bigger than ~8% of the position's spread breaks a tier
            threshold = spread * 0.08
            tier = 1
            group[0]["tier"] = tier
            for i in range(1, len(group)):
                if points[i - 1] - points[i] > threshold:
                    tier += 1
                group[i]["tier"] = tier

    # ------------------------------------------------------------ value board

    async def build_value_board(
        self,
        season: int,
        scoring_settings: Optional[Dict[str, Any]] = None,
        scoring_type: str = "ppr",
        roster_positions: Optional[List[str]] = None,
        team_count: int = 12,
        limit: int = 200,
    ) -> Dict[str, Any]:
        """
        Build a full draft value board adjusted for league scoring.

        Returns players ranked by VBD (value over replacement), each annotated with
        projected points, positional rank, tier, and ADP for spotting value/reaches.
        """
        players = await self._get_players()
        projections = await self.sleeper.get_player_projections(season)

        weights, is_custom = self._resolve_scoring_weights(scoring_settings, scoring_type)
        replacement_ranks = self._replacement_ranks(team_count, roster_positions)

        scored: List[Dict[str, Any]] = []
        for player_id, proj in projections.items():
            meta = players.get(player_id)
            if not meta:
                continue

            position = meta.get("position") or (
                meta.get("fantasy_positions") or [None]
            )[0]
            if position not in DRAFTABLE_POSITIONS:
                continue

            points = self._project_points(proj, weights, is_custom, scoring_type)
            if points <= 0:
                continue

            # search_rank approximates ADP (lower = drafted earlier); huge = undrafted
            adp = meta.get("search_rank")
            if not isinstance(adp, (int, float)) or adp > 100000:
                adp = None

            scored.append({
                "player_id": player_id,
                "name": meta.get("full_name")
                or f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
                or (meta.get("last_name") or position),
                "position": position,
                "team": meta.get("team"),
                "projected_points": points,
                "adp": adp,
                "bye_week": (proj.get("gms_active") and None) or meta.get("bye_week"),
                "age": meta.get("age"),
                "injury_status": meta.get("injury_status"),
            })

        # Positional rank + VBD baseline per position
        by_pos: Dict[str, List[Dict[str, Any]]] = {}
        for p in scored:
            by_pos.setdefault(p["position"], []).append(p)

        for pos, group in by_pos.items():
            group.sort(key=lambda x: x["projected_points"], reverse=True)
            baseline_idx = min(replacement_ranks.get(pos, len(group)) - 1, len(group) - 1)
            baseline_idx = max(baseline_idx, 0)
            baseline = group[baseline_idx]["projected_points"] if group else 0.0
            for i, p in enumerate(group):
                p["position_rank"] = i + 1
                p["vbd"] = round(p["projected_points"] - baseline, 1)

        self._assign_tiers(scored)

        # Overall board sorted by VBD (value over replacement), then raw points
        scored.sort(key=lambda x: (x["vbd"], x["projected_points"]), reverse=True)
        for i, p in enumerate(scored):
            p["overall_rank"] = i + 1

        board = scored[:limit]
        return {
            "season": season,
            "scoring": "custom" if is_custom else scoring_type,
            "team_count": team_count,
            "replacement_ranks": replacement_ranks,
            "player_count": len(board),
            "players": board,
        }

    # ------------------------------------------------------- live draft assist

    async def get_draft_state(self, draft_id: str) -> Dict[str, Any]:
        """Fetch live draft metadata and picks made so far."""
        draft = await self.sleeper.get_draft(draft_id)
        picks = await self.sleeper.get_draft_picks(draft_id)
        return {"draft": draft, "picks": picks}

    async def recommend_picks(
        self,
        draft_id: str,
        user_id: Optional[str] = None,
        scoring_settings: Optional[Dict[str, Any]] = None,
        scoring_type: str = "ppr",
        roster_positions: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Recommend the best available players for a live (or mock) draft.

        Reads the picks already made, figures out the user's current roster and
        positional needs, then scores undrafted players by VBD plus a bonus for
        positions the user still needs to fill.
        """
        draft = await self.sleeper.get_draft(draft_id)
        picks = await self.sleeper.get_draft_picks(draft_id)

        settings = draft.get("settings", {}) or {}
        team_count = settings.get("teams") or 12
        draft_roster_positions = roster_positions or draft.get("metadata", {}).get(
            "roster_positions"
        )

        board = await self.build_value_board(
            season=int(draft.get("season") or datetime.utcnow().year),
            scoring_settings=scoring_settings,
            scoring_type=scoring_type,
            roster_positions=draft_roster_positions,
            team_count=team_count,
            limit=400,
        )

        drafted_ids = {p.get("player_id") for p in picks if p.get("player_id")}

        # Build the user's current roster from picks they've made
        user_positions: Dict[str, int] = {p: 0 for p in DRAFTABLE_POSITIONS}
        user_roster: List[Dict[str, Any]] = []
        if user_id:
            for pick in picks:
                if pick.get("picked_by") == user_id:
                    meta = pick.get("metadata", {}) or {}
                    pos = meta.get("position")
                    if pos in user_positions:
                        user_positions[pos] += 1
                    user_roster.append({
                        "name": f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip(),
                        "position": pos,
                        "team": meta.get("team"),
                        "round": pick.get("round"),
                    })

        starters, flex = self._starters_from_roster_positions(draft_roster_positions)

        # Need score: how far the user is from filling starting slots at a position
        def need_bonus(position: str) -> float:
            target = starters.get(position, 0)
            if position in FLEX_POSITIONS:
                target += 1  # flex makes RB/WR/TE more valuable to stack
            have = user_positions.get(position, 0)
            if have >= target:
                return 0.0
            # Larger bonus the more starting slots remain unfilled
            return (target - have) * 6.0

        available = [p for p in board["players"] if p["player_id"] not in drafted_ids]
        for p in available:
            p["need_bonus"] = round(need_bonus(p["position"]), 1)
            p["pick_score"] = round(p["vbd"] + p["need_bonus"], 1)

        available.sort(key=lambda x: (x["pick_score"], x["projected_points"]), reverse=True)

        return {
            "draft_id": draft_id,
            "status": draft.get("status"),
            "round": settings.get("rounds"),
            "picks_made": len(picks),
            "team_count": team_count,
            "scoring": board["scoring"],
            "user_roster": user_roster,
            "user_position_counts": user_positions,
            "recommendations": available[:limit],
        }


# Global instance
draft_service = DraftService()
