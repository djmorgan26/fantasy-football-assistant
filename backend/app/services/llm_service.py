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

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert fantasy football analyst. Provide detailed, actionable trade analysis in JSON format. Consider player performance, matchups, injury risk, playoff schedules, and team needs."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.info("Trade analysis completed", tokens_used=response.usage.total_tokens)

            return result

        except Exception as e:
            logger.error("LLM trade analysis failed", error=str(e))
            return self._fallback_trade_analysis(give_players, receive_players)

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

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert fantasy football strategist. Generate 3-5 actionable suggestions to improve the user's team. Return suggestions as a JSON array with fields: type (pickup/drop/trade/lineup), priority (high/medium/low), title, description, reasoning, potential_impact, confidence_score (0-1), and action_details."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.5,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            suggestions = result.get("suggestions", [])

            # Add IDs to suggestions
            for i, suggestion in enumerate(suggestions):
                suggestion["id"] = str(i + 1)

            logger.info("Strategic suggestions generated", count=len(suggestions), tokens_used=response.usage.total_tokens)

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

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fantasy football lineup optimizer. Analyze the current lineup and suggest changes based on matchups, player performance, and opponent strengths. Return as JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            logger.info("Lineup optimization completed", tokens_used=response.usage.total_tokens)

            return result

        except Exception as e:
            logger.error("LLM lineup optimization failed", error=str(e))
            return {"recommendations": [], "error": str(e)}

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
