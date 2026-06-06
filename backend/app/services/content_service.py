"""
Content & Humor Engine.

Two halves:

1. Narrative extraction (pure, data-driven, no AI): turns a week of Sleeper data
   into concrete "story hooks" — blowouts, nail-biters, points left on the bench,
   the should've-started guy, lucky/unlucky wins, top performances. Funny content
   lives or dies on specifics, so we compute the specifics first.

2. Generation: assembles those facts + the league's voice profile (tone, manager
   personas, and a corpus of past write-ups) into a prompt and calls the LLM.
   Works with an empty profile (sensible default voice) and degrades gracefully
   to a facts-based draft when no LLM is configured.
"""
from typing import Dict, List, Any, Optional, Tuple
import statistics
import json
import structlog

from app.services.sleeper_service import SleeperService, SleeperError
from app.services.draft_service import draft_service
from app.services.llm_service import llm_service

logger = structlog.get_logger()

CONTENT_TYPES = ("weekly_recap", "power_rankings", "awards", "season_recap")

DEFAULT_VOICE = (
    "Brutally funny, sharp, and personal — like the loudest friend in the group chat "
    "roasting everyone after Sunday's games. Confident, a little mean to the losers, "
    "celebratory of dominance, heavy on specific callouts and over-the-top metaphors. "
    "Never generic or corporate."
)


class ContentService:
    """Generates league-personalized written content from real weekly data."""

    def __init__(self):
        self.sleeper = SleeperService()

    # ----------------------------------------------------- name resolution

    @staticmethod
    def _player_name(players_meta: Dict[str, Any], player_id: str) -> str:
        meta = players_meta.get(player_id) or {}
        return (
            meta.get("full_name")
            or f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip()
            or meta.get("last_name")
            or str(player_id)
        )

    # ----------------------------------------------- narrative extraction

    @classmethod
    def extract_sleeper_narrative(
        cls,
        matchups: List[Dict[str, Any]],
        rosters: List[Dict[str, Any]],
        users: List[Dict[str, Any]],
        players_meta: Dict[str, Any],
        week: int,
    ) -> Dict[str, Any]:
        """
        Build structured story hooks from a week of Sleeper data. Pure function —
        no network or LLM — so it is fully testable.
        """
        # roster_id -> display team name
        users_by_id = {u.get("user_id"): u for u in users}
        roster_team_name: Dict[int, str] = {}
        for r in rosters:
            rid = r.get("roster_id")
            owner = users_by_id.get(r.get("owner_id")) or {}
            team_name = (owner.get("metadata") or {}).get("team_name")
            roster_team_name[rid] = team_name or owner.get("display_name") or f"Team {rid}"

        # Per-team performance for the week
        teams: List[Dict[str, Any]] = []
        for m in matchups:
            rid = m.get("roster_id")
            points = round(float(m.get("points") or 0), 2)
            starters = m.get("starters") or []
            players_points = m.get("players_points") or {}

            bench_points = None
            top_bench = None
            best_starter = None
            if players_points:
                total = sum(float(v) for v in players_points.values())
                bench_points = round(total - points, 2)
                starter_set = set(starters)
                bench_scores = [
                    (pid, float(pts))
                    for pid, pts in players_points.items()
                    if pid not in starter_set
                ]
                starter_scores = [
                    (pid, float(players_points.get(pid, 0))) for pid in starters if pid
                ]
                if bench_scores:
                    pid, pts = max(bench_scores, key=lambda x: x[1])
                    top_bench = {"name": cls._player_name(players_meta, pid), "points": round(pts, 2)}
                if starter_scores:
                    pid, pts = max(starter_scores, key=lambda x: x[1])
                    best_starter = {"name": cls._player_name(players_meta, pid), "points": round(pts, 2)}

            teams.append({
                "roster_id": rid,
                "matchup_id": m.get("matchup_id"),
                "team_name": roster_team_name.get(rid, f"Team {rid}"),
                "points": points,
                "bench_points": bench_points,
                "best_starter": best_starter,
                "top_bench": top_bench,
            })

        # Matchup results (pair teams sharing a matchup_id)
        groups: Dict[Any, List[Dict[str, Any]]] = {}
        for t in teams:
            groups.setdefault(t["matchup_id"], []).append(t)

        results: List[Dict[str, Any]] = []
        for mid, pair in groups.items():
            if len(pair) != 2:
                continue
            a, b = pair
            winner, loser = (a, b) if a["points"] >= b["points"] else (b, a)
            margin = round(winner["points"] - loser["points"], 2)
            results.append({
                "winner": winner["team_name"],
                "loser": loser["team_name"],
                "winner_score": winner["points"],
                "loser_score": loser["points"],
                "margin": margin,
                "is_blowout": margin >= 40,
                "is_nailbiter": margin <= 5,
            })

        scores = [t["points"] for t in teams if t["points"] > 0]
        median = round(statistics.median(scores), 2) if scores else 0.0

        # Lucky / unlucky: won below the median, or lost above it
        loser_names = {r["loser"] for r in results}
        winner_names = {r["winner"] for r in results}
        lucky, unlucky = [], []
        for t in teams:
            if t["team_name"] in winner_names and t["points"] < median:
                lucky.append({"team_name": t["team_name"], "points": t["points"]})
            if t["team_name"] in loser_names and t["points"] > median:
                unlucky.append({"team_name": t["team_name"], "points": t["points"]})

        # Biggest bench blunder across the league (most points stranded on bench)
        bench_blunder = None
        bench_candidates = [t for t in teams if t.get("bench_points") is not None]
        if bench_candidates:
            worst = max(bench_candidates, key=lambda t: t["bench_points"])
            if worst["bench_points"] and worst["bench_points"] > 0:
                bench_blunder = {
                    "team_name": worst["team_name"],
                    "bench_points": worst["bench_points"],
                    "top_bench": worst.get("top_bench"),
                }

        ranked = sorted(teams, key=lambda t: t["points"], reverse=True)
        return {
            "week": week,
            "team_count": len(teams),
            "median_score": median,
            "average_score": round(statistics.mean(scores), 2) if scores else 0.0,
            "highest_scorer": ranked[0] if ranked else None,
            "lowest_scorer": ranked[-1] if ranked else None,
            "biggest_blowout": max(results, key=lambda r: r["margin"]) if results else None,
            "closest_game": min(results, key=lambda r: r["margin"]) if results else None,
            "lucky_wins": lucky,
            "unlucky_losses": unlucky,
            "bench_blunder": bench_blunder,
            "results": results,
            "teams": ranked,
        }

    async def get_weekly_narrative(self, league_id_str: str, week: int) -> Dict[str, Any]:
        """Fetch Sleeper data for a week and extract narrative facts."""
        matchups = await self.sleeper.get_matchups(league_id_str, week)
        rosters = await self.sleeper.get_rosters(league_id_str)
        users = await self.sleeper.get_league_users(league_id_str)
        players_meta = await draft_service.get_players_cached()
        return self.extract_sleeper_narrative(matchups, rosters, users, players_meta, week)

    async def get_standings(self, league_id_str: str) -> List[Dict[str, Any]]:
        """Season standings derived from roster settings (wins/losses/points)."""
        rosters = await self.sleeper.get_rosters(league_id_str)
        users = await self.sleeper.get_league_users(league_id_str)
        users_by_id = {u.get("user_id"): u for u in users}
        standings = []
        for r in rosters:
            s = r.get("settings") or {}
            owner = users_by_id.get(r.get("owner_id")) or {}
            name = (owner.get("metadata") or {}).get("team_name") or owner.get("display_name") or f"Team {r.get('roster_id')}"
            fpts = float(s.get("fpts", 0)) + float(s.get("fpts_decimal", 0)) / 100
            standings.append({
                "team_name": name,
                "wins": s.get("wins", 0),
                "losses": s.get("losses", 0),
                "ties": s.get("ties", 0),
                "points_for": round(fpts, 2),
            })
        standings.sort(key=lambda t: (t["wins"], t["points_for"]), reverse=True)
        return standings

    # -------------------------------------------------- prompt assembly

    @staticmethod
    def _voice_block(profile: Optional[Dict[str, Any]]) -> str:
        """Render the league voice/persona/corpus context for the prompt."""
        profile = profile or {}
        voice = (profile.get("voice_guide") or "").strip() or DEFAULT_VOICE
        parts = [f"LEAGUE VOICE & TONE:\n{voice}"]

        personas = profile.get("personas") or []
        if personas:
            lines = []
            for p in personas:
                bits = ", ".join(p.get("bits") or [])
                team = f" (team: {p['team_name']})" if p.get("team_name") else ""
                note = p.get("notes") or ""
                line = f"- {p.get('name', 'Unknown')}{team}: {note}"
                if bits:
                    line += f" Running bits: {bits}."
                lines.append(line)
            parts.append("MANAGER PERSONALITIES (use real names/jokes where relevant):\n" + "\n".join(lines))

        examples = profile.get("humor_examples") or []
        if examples:
            shown = examples[:3]
            ex_text = "\n\n".join(
                f"EXAMPLE {i + 1}{' — ' + e.get('title') if e.get('title') else ''}:\n{(e.get('text') or '')[:1500]}"
                for i, e in enumerate(shown)
            )
            parts.append(
                "PAST WRITE-UPS FROM THIS LEAGUE — match this exact voice, humor, and "
                "rhythm (do not copy them, write fresh):\n" + ex_text
            )
        else:
            parts.append(
                "NOTE: No past write-ups provided yet. Use the league voice above and lean "
                "into the specific facts to keep it from sounding generic."
            )
        return "\n\n".join(parts)

    @staticmethod
    def _facts_block(narrative: Dict[str, Any]) -> str:
        return "WEEKLY FACTS (use these specifics — names, scores, margins):\n" + json.dumps(
            narrative, indent=2, default=str
        )

    def _build_prompt(
        self,
        content_type: str,
        league_name: str,
        week: int,
        profile: Optional[Dict[str, Any]],
        narrative: Optional[Dict[str, Any]],
        standings: Optional[List[Dict[str, Any]]],
    ) -> str:
        voice = self._voice_block(profile)

        instructions = {
            "weekly_recap": (
                f"Write the Week {week} recap for \"{league_name}\". 3-4 punchy paragraphs. "
                "Roast the losers (especially anyone who lost ugly or left points on the bench), "
                "celebrate the blowouts, highlight the closest game and any lucky/unlucky results, "
                "and end with a spicy callout for next week. Reference specific teams and scores."
            ),
            "power_rankings": (
                f"Write Week {week} power rankings for \"{league_name}\". Rank every team 1 to N "
                "with a witty 1-2 sentence blurb each, blending record, points, and this week's "
                "performance. Be funny and a little savage toward the bottom of the table."
            ),
            "awards": (
                f"Hand out Week {week} awards for \"{league_name}\". Invent 4-6 funny award titles "
                "tied to the actual facts (e.g. bench blunder, lucky duck, beatdown of the week, "
                "stud of the week, biggest letdown). One sharp sentence per award with the team/player."
            ),
            "season_recap": (
                f"Write a season-in-review feature for \"{league_name}\" — the kind of long-form "
                "piece a league member submits once a year. 5-7 paragraphs. Crown the champ, roast "
                "the also-rans, hand out season superlatives, and capture the running storylines. "
                "Make it personal and quotable."
            ),
        }.get(content_type, f"Write fun content for \"{league_name}\".")

        blocks = [voice, "", instructions, ""]
        if narrative:
            blocks.append(self._facts_block(narrative))
        if standings:
            blocks.append("SEASON STANDINGS:\n" + json.dumps(standings, indent=2, default=str))
        return "\n".join(blocks)

    # -------------------------------------------------------- generation

    async def generate(
        self,
        content_type: str,
        league_name: str,
        week: int,
        profile: Optional[Dict[str, Any]] = None,
        narrative: Optional[Dict[str, Any]] = None,
        standings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate a piece of content. Falls back to a facts summary without an LLM."""
        prompt = self._build_prompt(content_type, league_name, week, profile, narrative, standings)

        if not llm_service.is_available():
            return {
                "content": self._fallback_content(content_type, narrative, standings),
                "content_type": content_type,
                "generated_by": "fallback",
            }

        try:
            response = llm_service.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the resident comedian and writer for a fantasy football league. "
                            "You write hilarious, personal, specific content that members screenshot and "
                            "share. Match the league's voice exactly. Never be generic or corporate."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                model=llm_service.model,
                temperature=0.85,
                max_tokens=1600,
            )
            content = response.choices[0].message.content
            logger.info(
                "Content generated",
                content_type=content_type,
                tokens=response.usage.total_tokens,
            )
            return {
                "content": content,
                "content_type": content_type,
                "generated_by": llm_service.model,
            }
        except Exception as e:
            logger.error("Content generation failed", error=str(e), content_type=content_type)
            return {
                "content": self._fallback_content(content_type, narrative, standings),
                "content_type": content_type,
                "generated_by": "fallback",
            }

    @staticmethod
    def _fallback_content(
        content_type: str,
        narrative: Optional[Dict[str, Any]],
        standings: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Readable facts-based draft when the LLM is unavailable."""
        lines = ["(AI writer unavailable — here are the raw story facts to work from.)", ""]
        if narrative:
            hs = narrative.get("highest_scorer") or {}
            ls = narrative.get("lowest_scorer") or {}
            bb = narrative.get("biggest_blowout") or {}
            cg = narrative.get("closest_game") or {}
            blunder = narrative.get("bench_blunder")
            lines.append(f"Week {narrative.get('week')}: avg {narrative.get('average_score')} pts")
            if hs:
                lines.append(f"- Top scorer: {hs.get('team_name')} ({hs.get('points')})")
            if ls:
                lines.append(f"- Low scorer: {ls.get('team_name')} ({ls.get('points')})")
            if bb:
                lines.append(f"- Biggest blowout: {bb.get('winner')} beat {bb.get('loser')} by {bb.get('margin')}")
            if cg:
                lines.append(f"- Closest game: {cg.get('winner')} edged {cg.get('loser')} by {cg.get('margin')}")
            if blunder:
                tb = blunder.get("top_bench") or {}
                extra = f" (benched {tb.get('name')} for {tb.get('points')})" if tb else ""
                lines.append(f"- Bench blunder: {blunder.get('team_name')} left {blunder.get('bench_points')} pts on the bench{extra}")
        if standings:
            lines.append("\nStandings:")
            for i, t in enumerate(standings, 1):
                lines.append(f"  {i}. {t['team_name']} ({t['wins']}-{t['losses']}, {t['points_for']} PF)")
        return "\n".join(lines)


# Global instance
content_service = ContentService()
