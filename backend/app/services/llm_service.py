"""
LLM Service for Fantasy Football AI Analysis
Uses GROQ API (free tier) for fast, high-quality LLM inference
"""
from groq import Groq
from typing import List, Dict, Any, Optional
import structlog
from app.core.config import settings
import json

logger = structlog.get_logger()


class LLMEmptyResponse(RuntimeError):
    """The model returned no usable text (usually the whole budget went to reasoning)."""


class LLMService:
    """Service for interacting with LLM via GROQ API"""

    def __init__(self):
        if not settings.groq_api_key:
            logger.warning("GROQ API key not configured - LLM features will not work")
            self.client = None
        else:
            self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model

    def is_available(self) -> bool:
        """Check if LLM service is available"""
        return self.client is not None

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        purpose: str,
        json_mode: bool = False,
    ) -> str:
        """One way in and out of the model, so no call can fail quietly.

        Token budgets here have to be generous: the default Groq model reasons
        before it answers, and that reasoning is billed against max_tokens. Too
        small a budget does not shorten the answer, it truncates it mid-sentence,
        and in JSON mode that truncation used to surface as a canned fallback
        with nothing in the logs to say why.
        """
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

        choice = response.choices[0]
        content = choice.message.content or ""

        if choice.finish_reason == "length":
            logger.warning(
                "LLM response hit the token ceiling and was cut off",
                purpose=purpose,
                model=self.model,
                max_tokens=max_tokens,
                completion_tokens=response.usage.completion_tokens,
            )
        if not content.strip():
            raise LLMEmptyResponse(
                f"{self.model} returned no content for {purpose} "
                f"(finish_reason={choice.finish_reason}, "
                f"completion_tokens={response.usage.completion_tokens})"
            )

        logger.info(
            "LLM call completed",
            purpose=purpose,
            model=self.model,
            tokens_used=response.usage.total_tokens,
        )
        return content

    def complete_json(self, **kwargs) -> Dict[str, Any]:
        """complete() for the JSON endpoints, with the parse in the same place."""
        return json.loads(self.complete(json_mode=True, **kwargs))

    async def analyze_trade(
        self,
        give_players: List[Dict[str, Any]],
        receive_players: List[Dict[str, Any]],
        user_roster: List[Dict[str, Any]],
        opponent_roster: List[Dict[str, Any]],
        league_settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze a trade using LLM for sophisticated analysis

        Args:
            give_players: List of players being given away
            receive_players: List of players being received
            user_roster: Current user's roster
            opponent_roster: Opponent's roster
            league_settings: League scoring settings

        Returns:
            Dict with analysis, recommendations, and insights
        """
        if not self.is_available():
            return self._fallback_trade_analysis(give_players, receive_players)

        try:
            prompt = self._build_trade_analysis_prompt(
                give_players, receive_players, user_roster, opponent_roster, league_settings
            )

            result = self.complete_json(
                system=(
                    "You are an expert fantasy football analyst. Provide detailed, actionable "
                    "trade analysis in JSON format. Reason only from the roster and scoring data "
                    "in the prompt: judge players by the stats you are shown, and if something "
                    "you would normally weigh (injury status, bye weeks, playoff schedule) is "
                    "not in the data, say the data does not cover it instead of guessing. Never "
                    "state a stat, ranking or news item that is not in the prompt."
                ),
                prompt=prompt,
                temperature=0.3,
                max_tokens=2500,
                purpose="trade_analysis",
            )

            return result

        except Exception as e:
            logger.error("LLM trade analysis failed", error=str(e))
            return self._fallback_trade_analysis(give_players, receive_players)

    async def trade_verdict(
        self,
        *,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Narrate a trade the engine has already scored.

        The division of labour is the point. Every number here (lineup deltas,
        playoff odds, value over replacement, depth) is computed by
        `trade_engine` from real projections *before* the model is called. The
        model's only job is to explain what those numbers mean and suggest a
        counter. It is told, in as many words, that the numbers are given and
        that inventing any others is the failure mode.

        This matters because an earlier version of this app let a model reason
        about a trade from raw rosters and it confidently described a league
        that did not exist. Grounding it in pre-computed figures is what keeps
        the write-up honest.

        Returns {} when the model is unavailable or misbehaves; the caller
        renders the engine's own verdict and nothing is lost but prose.
        """
        if not self.is_available():
            return {}

        try:
            return self.complete_json(
                system=(
                    "You are a fantasy football trade analyst writing for the manager "
                    "deciding on this trade. Every figure you need has already been "
                    "computed and is given in the prompt. Use ONLY those figures. Do not "
                    "invent statistics, rankings, injuries, news, or anything about a "
                    "player not listed. Do not recompute or contradict the given numbers; "
                    "explain what they mean. If something a manager would weigh is absent "
                    "from the data, say it is not covered rather than guessing. "
                    'Return JSON: {"summary": "2-3 sentences of plain assessment", '
                    '"points": ["3-5 short bullets, each tied to a given number"], '
                    '"counter": "one concrete counter-offer or next step, or null"}'
                ),
                prompt=json.dumps(context, indent=2, default=str),
                temperature=0.3,
                max_tokens=2000,
                purpose="trade_verdict",
            )
        except Exception as e:
            logger.warning("LLM trade verdict failed", error=str(e))
            return {}

    async def generate_strategic_suggestions(
        self,
        roster: List[Dict[str, Any]],
        league_info: Dict[str, Any],
        recent_matchups: List[Dict[str, Any]],
        available_players: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate strategic suggestions for team improvement

        Args:
            roster: Current team roster
            league_info: League settings and standings
            recent_matchups: Recent game results
            available_players: Available free agents (optional)

        Returns:
            List of strategic suggestions
        """
        if not self.is_available():
            return self._fallback_suggestions()

        try:
            prompt = self._build_suggestions_prompt(roster, league_info, recent_matchups, available_players)

            result = self.complete_json(
                system=(
                    "You are an expert fantasy football strategist. Generate 3-5 actionable "
                    "suggestions to improve the user's team. Return suggestions as a JSON array "
                    "with fields: type (pickup/drop/trade/lineup), priority (high/medium/low), "
                    "title, description, reasoning, potential_impact, confidence_score (0-1), "
                    "and action_details. Every player you name must appear in the roster or free "
                    "agent lists in the prompt, and every number you cite must come from that "
                    "data. Do not invent injuries, transactions, or news."
                ),
                prompt=prompt,
                temperature=0.5,
                max_tokens=3000,
                purpose="strategic_suggestions",
            )
            suggestions = result.get("suggestions", [])

            # Add IDs to suggestions
            for i, suggestion in enumerate(suggestions):
                suggestion["id"] = str(i + 1)

            logger.info("Strategic suggestions generated", count=len(suggestions))

            return suggestions

        except Exception as e:
            logger.error("LLM suggestion generation failed", error=str(e))
            return self._fallback_suggestions()

    async def analyze_lineup_optimization(
        self,
        roster: List[Dict[str, Any]],
        current_lineup: Dict[str, Any],
        opponent_team: Dict[str, Any],
        week_matchups: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze lineup and suggest optimizations for the current week

        Args:
            roster: Full roster
            current_lineup: Current lineup configuration
            opponent_team: This week's opponent
            week_matchups: Matchup data for the week

        Returns:
            Dict with lineup recommendations
        """
        if not self.is_available():
            return {"recommendations": [], "notes": "LLM service not available"}

        try:
            prompt = self._build_lineup_prompt(roster, current_lineup, opponent_team, week_matchups)

            result = self.complete_json(
                system=(
                    "You are a fantasy football lineup optimizer. Analyze the current lineup and "
                    "suggest changes based on the projections and performance data you are given. "
                    "Only move players who appear on the supplied roster, and base every claim on "
                    "the supplied numbers rather than outside knowledge of the season."
                ),
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000,
                purpose="lineup_optimization",
            )

            return result

        except Exception as e:
            logger.error("LLM lineup optimization failed", error=str(e))
            return {"recommendations": [], "error": str(e)}

    async def analyze_draft_pick(
        self,
        round_number: int,
        user_roster: List[Dict[str, Any]],
        position_needs: Dict[str, int],
        top_available: List[Dict[str, Any]],
        scoring: str,
    ) -> Dict[str, Any]:
        """
        Give a natural-language draft recommendation for the current pick.

        Args:
            round_number: Current draft round
            user_roster: Players already drafted by the user
            position_needs: Current counts by position
            top_available: Best available players (already VBD-ranked)
            scoring: League scoring description (e.g. "ppr" or "custom")

        Returns:
            Dict with a recommended pick and reasoning
        """
        if not self.is_available():
            return self._fallback_draft_advice(top_available)

        try:
            prompt = f"""You are an elite fantasy football draft strategist. It is round {round_number} of a {scoring} league draft.

MY ROSTER SO FAR:
{json.dumps(user_roster, indent=2) if user_roster else "Empty - this is an early pick"}

CURRENT POSITION COUNTS:
{json.dumps(position_needs, indent=2)}

BEST AVAILABLE PLAYERS (already ranked by value over replacement; higher vbd/pick_score = better value):
{json.dumps(top_available[:12], indent=2)}

Recommend who to draft. Balance best-player-available against roster construction and positional scarcity. Return JSON with:
- recommended_player: the name of your top pick
- alternatives: array of 1-2 other strong options
- reasoning: 2-3 sentences explaining the pick (value, scarcity, roster fit)
- strategy_note: one sentence on what to target in the next round or two
"""
            result = self.complete_json(
                system=(
                    "You are an expert fantasy football draft strategist. Give sharp, specific "
                    "draft advice grounded in value-based drafting and roster construction. "
                    "Recommend only players from the supplied available list, named exactly as "
                    "they appear there, and justify the pick from the supplied values. Respond in JSON."
                ),
                prompt=prompt,
                temperature=0.4,
                max_tokens=2000,
                purpose="draft_advice",
            )
            return result

        except Exception as e:
            logger.error("LLM draft advice failed", error=str(e))
            return self._fallback_draft_advice(top_available)

    def _fallback_draft_advice(self, top_available: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deterministic draft advice when the LLM is unavailable."""
        if not top_available:
            return {
                "recommended_player": None,
                "alternatives": [],
                "reasoning": "No available players to evaluate.",
                "strategy_note": "Configure GROQ_API_KEY for AI-powered draft reasoning.",
            }
        top = top_available[0]
        alts = [p.get("name") for p in top_available[1:3]]
        return {
            "recommended_player": top.get("name"),
            "alternatives": alts,
            "reasoning": (
                f"{top.get('name')} ({top.get('position')}) offers the best value over "
                f"replacement on the board (VBD {top.get('vbd')}, ~{top.get('projected_points')} projected points)."
            ),
            "strategy_note": "Best value by VBD. Add GROQ_API_KEY for fuller AI reasoning.",
        }

    def _build_trade_analysis_prompt(
        self,
        give_players: List[Dict[str, Any]],
        receive_players: List[Dict[str, Any]],
        user_roster: List[Dict[str, Any]],
        opponent_roster: List[Dict[str, Any]],
        league_settings: Dict[str, Any]
    ) -> str:
        """Build prompt for trade analysis"""
        return f"""Analyze this fantasy football trade:

GIVING AWAY:
{json.dumps(give_players, indent=2)}

RECEIVING:
{json.dumps(receive_players, indent=2)}

MY ROSTER:
{json.dumps(user_roster[:15], indent=2)}

OPPONENT'S ROSTER:
{json.dumps(opponent_roster[:15], indent=2)}

LEAGUE SETTINGS:
{json.dumps(league_settings, indent=2)}

Provide a comprehensive trade analysis in JSON format with these fields:
- overall_verdict: "accept", "decline", or "negotiate"
- fairness_score: 0-100
- value_difference: estimated point difference per week
- analysis_summary: 2-3 sentence overview
- pros: array of benefits
- cons: array of drawbacks
- recommendations: array of specific advice
- risk_assessment: injury/performance risk analysis
- team_fit_analysis: how players fit your roster needs
"""

    def _build_suggestions_prompt(
        self,
        roster: List[Dict[str, Any]],
        league_info: Dict[str, Any],
        recent_matchups: List[Dict[str, Any]],
        available_players: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Build prompt for strategic suggestions"""
        available_text = ""
        if available_players:
            available_text = f"\n\nTOP AVAILABLE FREE AGENTS:\n{json.dumps(available_players[:20], indent=2)}"

        return f"""Analyze this fantasy football team and generate strategic suggestions:

MY ROSTER:
{json.dumps(roster[:15], indent=2)}

LEAGUE INFO:
{json.dumps(league_info, indent=2)}

RECENT PERFORMANCE:
{json.dumps(recent_matchups[:5], indent=2)}
{available_text}

Generate 3-5 actionable suggestions to improve this team. Return as JSON with this structure:
{{
  "suggestions": [
    {{
      "type": "pickup" | "drop" | "trade" | "lineup",
      "priority": "high" | "medium" | "low",
      "title": "short title",
      "description": "brief description",
      "reasoning": "why this helps",
      "potential_impact": "expected benefit",
      "confidence_score": 0.0-1.0,
      "action_details": {{}}
    }}
  ]
}}

Focus on high-impact moves that address weaknesses or capitalize on opportunities.
"""

    def _build_lineup_prompt(
        self,
        roster: List[Dict[str, Any]],
        current_lineup: Dict[str, Any],
        opponent_team: Dict[str, Any],
        week_matchups: Dict[str, Any]
    ) -> str:
        """Build prompt for lineup optimization"""
        return f"""Optimize this fantasy football lineup for this week:

MY ROSTER:
{json.dumps(roster[:15], indent=2)}

CURRENT LINEUP:
{json.dumps(current_lineup, indent=2)}

OPPONENT:
{json.dumps(opponent_team, indent=2)}

MATCHUPS:
{json.dumps(week_matchups, indent=2)}

Analyze and return JSON with:
- recommendations: array of lineup changes
- reasoning: why each change helps
- projected_impact: point swing estimate
"""

    def _fallback_trade_analysis(
        self,
        give_players: List[Dict[str, Any]],
        receive_players: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Fallback analysis when LLM is unavailable"""
        give_count = len(give_players)
        receive_count = len(receive_players)

        return {
            "overall_verdict": "manual_review",
            "fairness_score": 50.0,
            "value_difference": 0.0,
            "analysis_summary": f"Trade involves {give_count} player(s) for {receive_count} player(s). LLM analysis unavailable - manual evaluation recommended.",
            "pros": ["Manual evaluation needed"],
            "cons": ["LLM service not configured"],
            "recommendations": ["Review player stats and rankings manually", "Consider recent performance trends"],
            "risk_assessment": "Unable to assess without LLM service",
            "team_fit_analysis": "Manual analysis required"
        }

    def _fallback_suggestions(self) -> List[Dict[str, Any]]:
        """Fallback suggestions when LLM is unavailable"""
        return [
            {
                "id": "1",
                "type": "lineup",
                "priority": "medium",
                "title": "Review Your Lineup",
                "description": "Manually check your lineup for optimal player placement",
                "reasoning": "LLM service not available for automated analysis",
                "potential_impact": "Ensure best players are starting",
                "confidence_score": 0.5,
                "action_details": {}
            }
        ]


# Global instance
llm_service = LLMService()
