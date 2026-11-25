"""In-memory RoomManager with asyncio.Lock, F5 reconnect grace, SLA loop, and anti-cheat isolation."""

from __future__ import annotations

import asyncio
import logging
import secrets
import string
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket

from app.core.scenario_loader import ScenarioLoader
from app.core.scoring import evaluate_decision, evaluate_timeout
from app.enrichers.registry import EnricherRegistry, pick_ioc_for_enricher
from app.models.contracts import (
    ClientRole,
    DebriefCaseSummary,
    DebriefStanding,
    DecisionType,
    EvidenceCard,
    FeedEventPayload,
    MatchDebriefPayload,
    PublicAlert,
    RoomStatePayload,
    RoomStatus,
    ScenarioFile,
    TeamPublicSummary,
)

logger = logging.getLogger("breachzero.room")

DEFAULT_TEAM_NAMES = ["ALPHA SQUAD", "SİBER KURTLAR", "ZERO-DAY EKİBİ"]


class RoomError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class TeamAlertState:
    scenario: ScenarioFile
    remaining_sla: int
    status: str = "UNCLAIMED"  # UNCLAIMED | CLAIMED | RESOLVED | EXPIRED
    claimed_by_session_token: Optional[str] = None
    claimed_by_player_id: Optional[str] = None
    claimed_by_nickname: Optional[str] = None
    claimed_by_avatar_id: Optional[str] = None
    evidence_cards: list[EvidenceCard] = field(default_factory=list)
    outcome: Optional[str] = None

    def to_public_alert(self) -> PublicAlert:
        p = self.scenario.public_alert
        return PublicAlert(
            alert_id=p.alert_id,
            incident_code=p.incident_code,
            title=p.title,
            severity=p.severity,
            timestamp_utc=p.timestamp_utc,
            sla_seconds=p.sla_seconds,
            remaining_sla=self.remaining_sla,
            status=self.status,  # type: ignore[arg-type]
            claimed_by_player_id=self.claimed_by_player_id,
            claimed_by_nickname=self.claimed_by_nickname,
            claimed_by_avatar_id=self.claimed_by_avatar_id,
            source=p.source,
            destination=p.destination,
            host=p.host,
            user=p.user,
            process=p.process,
            file=p.file,
            raw_log=p.raw_log,
            indicators=p.indicators,
            available_enrichers=list(p.available_enrichers),
            evidence_cards=list(self.evidence_cards),
        )


@dataclass
class TeamState:
    team_id: str
    name: str
    score: int = 0
    hp: int = 100
    streak: int = 0
    resolved_count: int = 0
    is_breached: bool = False
    alerts: dict[str, TeamAlertState] = field(default_factory=dict)


@dataclass
class PlayerSession:
    session_token: str
    player_id: str
    team_id: str
    nickname: str
    avatar_id: str
    websocket: Optional[WebSocket] = None
    grace_task: Optional[asyncio.Task[Any]] = None


@dataclass
class ObserverConnection:
    role: LiteralRole
    websocket: WebSocket


LiteralRole = ClientRole


@dataclass
class RoomState:
    room_code: str
    admin_token: str
    status: RoomStatus = "LOBBY"
    current_wave: int = 0
    total_waves: int = 2
    teams: dict[str, TeamState] = field(default_factory=dict)
    sessions: dict[str, PlayerSession] = field(default_factory=dict)
    observers: list[tuple[ClientRole, WebSocket]] = field(default_factory=list)
    played_scenario_ids: list[str] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    tick_task: Optional[asyncio.Task[Any]] = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _envelope(msg_type: str, payload: dict[str, Any], request_id: Optional[str] = None) -> dict[str, Any]:
    return {
        "type": msg_type,
        "request_id": request_id,
        "timestamp": _utc_now(),
        "payload": payload,
    }


class RoomManager:
    """Manages active game rooms, WebSocket broadcasts, locking, and SLA ticks."""

    def __init__(
        self,
        scenario_loader: ScenarioLoader,
        enricher_registry: EnricherRegistry,
        reconnect_grace_seconds: float = 15.0,
        tick_interval_seconds: float = 1.0,
    ) -> None:
        self.scenario_loader = scenario_loader
        self.enricher_registry = enricher_registry
        self.reconnect_grace_seconds = reconnect_grace_seconds
        self.tick_interval_seconds = tick_interval_seconds
        self.rooms: dict[str, RoomState] = {}

    def _generate_room_code(self) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "BZ" + "".join(secrets.choice(chars) for _ in range(4))
            if code not in self.rooms:
                return code

    def create_room(
        self,
        team_names: Optional[list[str]] = None,
        total_waves: int = 2,
    ) -> RoomState:
        room_code = self._generate_room_code()
        admin_token = f"adm_{secrets.token_hex(16)}"
        names = [n.strip() for n in (team_names or DEFAULT_TEAM_NAMES) if n.strip()]
        if not names:
            names = list(DEFAULT_TEAM_NAMES)

        teams: dict[str, TeamState] = {}
        for idx, name in enumerate(names, start=1):
            tid = f"team_{idx}"
            teams[tid] = TeamState(team_id=tid, name=name)

        room = RoomState(
            room_code=room_code,
            admin_token=admin_token,
            total_waves=total_waves,
            teams=teams,
        )
        self.rooms[room_code] = room
        return room

    def get_room(self, room_code: str) -> RoomState:
        code = room_code.strip().upper()
        room = self.rooms.get(code)
        if not room:
            raise RoomError("ROOM_NOT_FOUND", f"Oda bulunamadı: {code}")
        return room

    def build_room_state_payload(
        self,
        room: RoomState,
        role: ClientRole,
        team_id: Optional[str] = None,
    ) -> dict[str, Any]:
        team_summaries: list[TeamPublicSummary] = []
        for t in room.teams.values():
            queue: list[PublicAlert] = []
            if role == "PLAYER" and team_id == t.team_id:
                queue = [a.to_public_alert() for a in t.alerts.values()]
            team_summaries.append(
                TeamPublicSummary(
                    team_id=t.team_id,
                    name=t.name,
                    score=t.score,
                    hp=t.hp,
                    streak=t.streak,
                    resolved_count=t.resolved_count,
                    is_breached=t.is_breached,
                    queue=queue,
                )
            )
        return RoomStatePayload(
            room_code=room.room_code,
            status=room.status,
            current_wave=room.current_wave,
            total_waves=room.total_waves,
            teams=team_summaries,
        ).model_dump()

    async def _send_safe(self, ws: Optional[WebSocket], data: dict[str, Any]) -> None:
        if ws is None:
            return
        try:
            await ws.send_json(data)
        except Exception:
            pass

    async def broadcast_room_state(self, room: RoomState) -> None:
        for sess in list(room.sessions.values()):
            if sess.websocket is not None:
                payload = self.build_room_state_payload(room, "PLAYER", sess.team_id)
                await self._send_safe(sess.websocket, _envelope("ROOM_STATE_UPDATE", payload))

        obs_payload = self.build_room_state_payload(room, "HOST", None)
        obs_msg = _envelope("ROOM_STATE_UPDATE", obs_payload)
        for _, ws in list(room.observers):
            await self._send_safe(ws, obs_msg)

    async def broadcast_feed(
        self,
        room: RoomState,
        severity: str,
        team_name: str,
        message: str,
    ) -> None:
        evt = FeedEventPayload(
            event_id=f"evt_{secrets.token_hex(4)}",
            severity=severity,  # type: ignore[arg-type]
            team_name=team_name,
            message=message,
        ).model_dump()
        msg = _envelope("FEED_EVENT", evt)
        for sess in list(room.sessions.values()):
            await self._send_safe(sess.websocket, msg)
        for _, ws in list(room.observers):
            await self._send_safe(ws, msg)

    async def broadcast_team(self, room: RoomState, team_id: str, msg: dict[str, Any]) -> None:
        for sess in list(room.sessions.values()):
            if sess.team_id == team_id and sess.websocket is not None:
                await self._send_safe(sess.websocket, msg)

    async def join_room(
        self,
        room_code: str,
        role: ClientRole,
        websocket: Optional[WebSocket],
        team_id: Optional[str] = None,
        nickname: Optional[str] = None,
        avatar_id: str = "analyst-ali",
        session_token: Optional[str] = None,
        admin_token: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> tuple[Optional[PlayerSession], dict[str, Any]]:
        room = self.get_room(room_code)
        async with room.lock:
            if role in ("HOST", "ADMIN"):
                if role == "ADMIN" and admin_token != room.admin_token:
                    raise RoomError("INVALID_SESSION", "Geçersiz admin_token.")
                if websocket is not None:
                    room.observers.append((role, websocket))
                ready = _envelope(
                    "SESSION_READY",
                    {
                        "session_token": admin_token if role == "ADMIN" else None,
                        "player_id": None,
                        "team_id": None,
                        "role": role,
                        "reconnected": False,
                        "reconnect_grace_seconds": int(self.reconnect_grace_seconds),
                    },
                    request_id=request_id,
                )
                return None, ready

            # PLAYER role
            if session_token and session_token in room.sessions:
                existing = room.sessions[session_token]
                if existing.grace_task and not existing.grace_task.done():
                    existing.grace_task.cancel()
                existing.grace_task = None
                existing.websocket = websocket
                ready = _envelope(
                    "SESSION_READY",
                    {
                        "session_token": existing.session_token,
                        "player_id": existing.player_id,
                        "team_id": existing.team_id,
                        "role": "PLAYER",
                        "reconnected": True,
                        "reconnect_grace_seconds": int(self.reconnect_grace_seconds),
                    },
                    request_id=request_id,
                )
                return existing, ready

            chosen_team = team_id or next(iter(room.teams.keys()))
            if chosen_team not in room.teams:
                raise RoomError("TEAM_NOT_FOUND", f"Takım bulunamadı: {chosen_team}")

            clean_nick = (nickname or "Analist").strip()[:24] or "Analist"
            new_token = f"tok_{secrets.token_hex(16)}"
            player_id = f"plr_{secrets.token_hex(4)}"
            session = PlayerSession(
                session_token=new_token,
                player_id=player_id,
                team_id=chosen_team,
                nickname=clean_nick,
                avatar_id=avatar_id or "analyst-ali",
                websocket=websocket,
            )
            room.sessions[new_token] = session
            ready = _envelope(
                "SESSION_READY",
                {
                    "session_token": new_token,
                    "player_id": player_id,
                    "team_id": chosen_team,
                    "role": "PLAYER",
                    "reconnected": False,
                    "reconnect_grace_seconds": int(self.reconnect_grace_seconds),
                },
                request_id=request_id,
            )
            return session, ready

    async def handle_disconnect(self, room_code: str, websocket: WebSocket) -> None:
        room = self.rooms.get(room_code.strip().upper())
        if not room:
            return
        async with room.lock:
            room.observers = [(r, ws) for (r, ws) in room.observers if ws is not websocket]
            for sess in room.sessions.values():
                if sess.websocket is websocket:
                    sess.websocket = None
                    if sess.grace_task and not sess.grace_task.done():
                        sess.grace_task.cancel()
                    sess.grace_task = asyncio.create_task(
                        self._grace_release_worker(room.room_code, sess.session_token)
                    )
                    break

    async def _grace_release_worker(self, room_code: str, session_token: str) -> None:
        try:
            await asyncio.sleep(self.reconnect_grace_seconds)
        except asyncio.CancelledError:
            return

        room = self.rooms.get(room_code)
        if not room:
            return

        released_alerts: list[tuple[str, str]] = []
        async with room.lock:
            sess = room.sessions.get(session_token)
            if not sess or sess.websocket is not None:
                return
            team = room.teams.get(sess.team_id)
            if not team:
                return
            for alert in team.alerts.values():
                if alert.status == "CLAIMED" and alert.claimed_by_session_token == session_token:
                    alert.status = "UNCLAIMED"
                    alert.claimed_by_session_token = None
                    alert.claimed_by_player_id = None
                    alert.claimed_by_nickname = None
                    alert.claimed_by_avatar_id = None
                    released_alerts.append((team.name, alert.scenario.public_alert.incident_code))

        if released_alerts:
            for team_name, code in released_alerts:
                await self.broadcast_feed(
                    room,
                    "WARN",
                    team_name,
                    f"{code} bileti bağlantı koptuğu için kuyruğa otomatik iade edildi (kanıtlar korundu).",
                )
            await self.broadcast_room_state(room)

    def _require_player(self, room: RoomState, session_token: Optional[str]) -> tuple[PlayerSession, TeamState]:
        if not session_token or session_token not in room.sessions:
            raise RoomError("INVALID_SESSION", "Geçersiz veya süresi dolmuş oturum.")
        sess = room.sessions[session_token]
        team = room.teams[sess.team_id]
        if team.is_breached:
            raise RoomError("TEAM_BREACHED", "Takımınızın Breach Meter değeri 0 HP; yeni işlem yapılamaz.")
        return sess, team

    def _require_active_room(self, room: RoomState) -> None:
        if room.status == "PAUSED":
            raise RoomError("ROOM_PAUSED", "Oyun moderatör tarafından duraklatıldı.")
        if room.status != "ACTIVE":
            raise RoomError("ROOM_NOT_ACTIVE", "Aktif dalga henüz başlatılmadı veya oyun sona erdi.")

    async def claim_alert(self, room_code: str, session_token: str, alert_id: str) -> None:
        room = self.get_room(room_code)
        async with room.lock:
            self._require_active_room(room)
            sess, team = self._require_player(room, session_token)
            alert = team.alerts.get(alert_id)
            if not alert:
                raise RoomError("ALERT_NOT_FOUND", f"Alarm bulunamadı: {alert_id}")
            if alert.status == "CLAIMED":
                raise RoomError("ALERT_ALREADY_CLAIMED", f"Bu bilet zaten {alert.claimed_by_nickname} tarafından kilitli.")
            if alert.status != "UNCLAIMED":
                raise RoomError("ALERT_NOT_CLAIMABLE", "Bu bilet zaten sonuçlandırılmış.")

            alert.status = "CLAIMED"
            alert.claimed_by_session_token = sess.session_token
            alert.claimed_by_player_id = sess.player_id
            alert.claimed_by_nickname = sess.nickname
            alert.claimed_by_avatar_id = sess.avatar_id

        await self.broadcast_room_state(room)

    async def release_alert(self, room_code: str, session_token: str, alert_id: str) -> None:
        room = self.get_room(room_code)
        async with room.lock:
            self._require_active_room(room)
            sess, team = self._require_player(room, session_token)
            alert = team.alerts.get(alert_id)
            if not alert:
                raise RoomError("ALERT_NOT_FOUND", f"Alarm bulunamadı: {alert_id}")
            if alert.status != "CLAIMED":
                raise RoomError("ALERT_NOT_CLAIMED", "Bilet şu anda kimseye zimmetli değil.")
            if alert.claimed_by_session_token != sess.session_token:
                raise RoomError("NOT_CLAIM_OWNER", "Bu bileti yalnızca üstlenen analist serbest bırakabilir.")

            alert.status = "UNCLAIMED"
            alert.claimed_by_session_token = None
            alert.claimed_by_player_id = None
            alert.claimed_by_nickname = None
            alert.claimed_by_avatar_id = None
            # Note: alert.evidence_cards are intentionally preserved for the team!

        await self.broadcast_room_state(room)

    async def run_enricher(
        self,
        room_code: str,
        session_token: str,
        alert_id: str,
        enricher_id: str,
        ioc_value: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> EvidenceCard:
        room = self.get_room(room_code)
        async with room.lock:
            self._require_active_room(room)
            sess, team = self._require_player(room, session_token)
            alert = team.alerts.get(alert_id)
            if not alert:
                raise RoomError("ALERT_NOT_FOUND", f"Alarm bulunamadı: {alert_id}")
            if alert.status != "CLAIMED":
                raise RoomError("ALERT_NOT_CLAIMED", "Kanıt çekmek için önce bileti CLAIM etmelisiniz.")
            if alert.claimed_by_session_token != sess.session_token:
                raise RoomError("NOT_CLAIM_OWNER", "Bu bileti yalnızca üstlenen analist inceleyebilir.")
            if enricher_id not in alert.scenario.public_alert.available_enrichers:
                raise RoomError("ENRICHER_NOT_AVAILABLE", f"Bu senaryoda '{enricher_id}' aracı aktif değil.")

            existing_cards = list(alert.evidence_cards)
            scenario = alert.scenario
            ioc_type, default_ioc = pick_ioc_for_enricher(scenario, enricher_id)
            chosen_ioc = (ioc_value or default_ioc).strip()

        # Execute external/cache/mock lookup without blocking other rooms, then commit atomically
        card, cost = await self.enricher_registry.execute(
            enricher_id=enricher_id,
            ioc_type=ioc_type,
            ioc_value=chosen_ioc,
            scenario=scenario,
            existing_cards=existing_cards,
        )

        async with room.lock:
            alert_now = team.alerts[alert_id]
            already_has = any(c.enricher_id == enricher_id for c in alert_now.evidence_cards)
            if not already_has:
                if card.status != "UNAVAILABLE":
                    alert_now.evidence_cards.append(card)
                team.score += cost
            else:
                cost = 0
                card = card.model_copy(update={"query_cost_applied": 0})
            updated_score = team.score

        await self.broadcast_team(
            room,
            team.team_id,
            _envelope(
                "ALERT_ENRICHED",
                {
                    "alert_id": alert_id,
                    "team_score": updated_score,
                    "evidence_card": card.model_dump(),
                },
                request_id=request_id,
            ),
        )
        await self.broadcast_room_state(room)
        return card

    async def submit_decision(
        self,
        room_code: str,
        session_token: str,
        alert_id: str,
        decision: DecisionType,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        room = self.get_room(room_code)
        async with room.lock:
            self._require_active_room(room)
            sess, team = self._require_player(room, session_token)
            alert = team.alerts.get(alert_id)
            if not alert:
                raise RoomError("ALERT_NOT_FOUND", f"Alarm bulunamadı: {alert_id}")
            if alert.status != "CLAIMED":
                raise RoomError("ALERT_NOT_CLAIMED", "Karar vermek için önce bileti CLAIM etmelisiniz.")
            if alert.claimed_by_session_token != sess.session_token:
                raise RoomError("NOT_CLAIM_OWNER", "Bu bilet başka bir analiste zimmetli; karar veremezsiniz.")

            pub = alert.scenario.public_alert
            srv = alert.scenario.server_only
            ev = evaluate_decision(
                ground_truth=srv.ground_truth,
                decision=decision,
                remaining_sla=alert.remaining_sla,
                sla_seconds=pub.sla_seconds,
                current_streak=team.streak,
                hp_penalty_on_miss=srv.hp_penalty_on_miss,
            )

            team.score += ev.score_delta
            team.hp = max(0, team.hp + ev.hp_delta)
            team.streak = 0 if ev.reset_streak else (team.streak + 1)
            team.resolved_count += 1
            if team.hp == 0:
                team.is_breached = True

            alert.status = "RESOLVED"
            alert.outcome = ev.outcome
            alert.claimed_by_session_token = None
            alert.claimed_by_player_id = None
            alert.claimed_by_nickname = None
            alert.claimed_by_avatar_id = None

            result_payload = {
                "alert_id": alert_id,
                "accepted": True,
                "outcome": ev.outcome,
                "score_delta": ev.score_delta,
                "hp_delta": ev.hp_delta,
                "new_score": team.score,
                "new_hp": team.hp,
                "new_streak": team.streak,
            }

            if ev.outcome == "FALSE_NEGATIVE":
                feed_sev = "THREAT"
                feed_msg = f"{team.name}, {pub.incident_code} gerçek saldırısını yanlışlıkla kapattı! ({ev.score_delta} Puan, {ev.hp_delta} HP)"
            elif ev.outcome == "FALSE_POSITIVE":
                feed_sev = "WARN"
                feed_msg = f"{team.name}, {pub.incident_code} zararsız alarmını yanlışlıkla eskale etti! ({ev.score_delta} Puan)"
            else:
                feed_sev = "SAFE"
                feed_msg = f"{team.name}, {pub.incident_code} biletini doğru çözdü (+{ev.score_delta} Puan)."

            breach_notice = team.is_breached
            team_name = team.name

        await self.broadcast_team(room, team.team_id, _envelope("DECISION_RESULT", result_payload, request_id=request_id))
        await self.broadcast_feed(room, feed_sev, team_name, feed_msg)
        if breach_notice:
            await self.broadcast_feed(room, "THREAT", team_name, f"{team_name} 0 HP ile BREACHED oldu ve elendi!")
        await self.broadcast_room_state(room)
        return result_payload

    async def admin_start_wave(
        self,
        room_code: str,
        admin_token: str,
        scenario_ids: Optional[list[str]] = None,
        wave_number: Optional[int] = None,
    ) -> None:
        room = self.get_room(room_code)
        async with room.lock:
            if admin_token != room.admin_token:
                raise RoomError("INVALID_SESSION", "Geçersiz admin_token.")

            if scenario_ids:
                chosen = [self.scenario_loader.get(sid) for sid in scenario_ids]
                scenarios = [s for s in chosen if s is not None]
            else:
                scenarios = self.scenario_loader.list_all()

            if not scenarios:
                raise RoomError("NO_SCENARIOS", "Dalga başlatmak için geçerli senaryo bulunamadı.")

            room.current_wave = wave_number if wave_number is not None else (room.current_wave + 1)
            room.status = "ACTIVE"

            for sc in scenarios:
                sid = sc.public_alert.alert_id
                if sid not in room.played_scenario_ids:
                    room.played_scenario_ids.append(sid)

            for team in room.teams.values():
                if team.is_breached:
                    continue
                for sc in scenarios:
                    sid = sc.public_alert.alert_id
                    if sid not in team.alerts:
                        team.alerts[sid] = TeamAlertState(
                            scenario=sc,
                            remaining_sla=sc.public_alert.sla_seconds,
                        )

            if room.tick_task is None or room.tick_task.done():
                room.tick_task = asyncio.create_task(self._sla_tick_loop(room.room_code))

        await self.broadcast_feed(room, "INFO", "SYSTEM", f"DALGA {room.current_wave} başlatıldı ({len(scenarios)} alarm kuyruğa eklendi).")
        await self.broadcast_room_state(room)

    async def admin_pause_wave(self, room_code: str, admin_token: str, reason: str = "") -> None:
        room = self.get_room(room_code)
        async with room.lock:
            if admin_token != room.admin_token:
                raise RoomError("INVALID_SESSION", "Geçersiz admin_token.")
            room.status = "PAUSED"

        note = f" ({reason})" if reason else ""
        await self.broadcast_feed(room, "WARN", "SYSTEM", f"Oyun duraklatıldı{note} — tüm SLA sayaçları donduruldu.")
        await self.broadcast_room_state(room)

    async def admin_resume_wave(self, room_code: str, admin_token: str) -> None:
        room = self.get_room(room_code)
        async with room.lock:
            if admin_token != room.admin_token:
                raise RoomError("INVALID_SESSION", "Geçersiz admin_token.")
            room.status = "ACTIVE"

        await self.broadcast_feed(room, "INFO", "SYSTEM", "Oyun devam ediyor — SLA sayaçları yeniden aktif.")
        await self.broadcast_room_state(room)

    async def admin_end_match(self, room_code: str, admin_token: str) -> dict[str, Any]:
        room = self.get_room(room_code)
        async with room.lock:
            if admin_token != room.admin_token:
                raise RoomError("INVALID_SESSION", "Geçersiz admin_token.")
            room.status = "ENDED"
            if room.tick_task and not room.tick_task.done():
                room.tick_task.cancel()
            for sess in room.sessions.values():
                if sess.grace_task and not sess.grace_task.done():
                    sess.grace_task.cancel()

            sorted_teams = sorted(room.teams.values(), key=lambda t: (t.score, t.hp), reverse=True)
            standings = [
                DebriefStanding(
                    rank=idx,
                    team_id=t.team_id,
                    name=t.name,
                    score=t.score,
                    hp=t.hp,
                    is_breached=t.is_breached,
                )
                for idx, t in enumerate(sorted_teams, start=1)
            ]

            cases: list[DebriefCaseSummary] = []
            for sid in room.played_scenario_ids:
                sc = self.scenario_loader.get(sid)
                if not sc:
                    continue
                outcomes = {
                    t.team_id: (t.alerts[sid].outcome or "UNRESOLVED")
                    for t in room.teams.values()
                    if sid in t.alerts
                }
                cases.append(
                    DebriefCaseSummary(
                        alert_id=sid,
                        incident_code=sc.public_alert.incident_code,
                        title=sc.public_alert.title,
                        ground_truth=sc.server_only.ground_truth,
                        mitre_attack=list(sc.server_only.mitre_attack),
                        debrief_explanation=sc.server_only.debrief_explanation,
                        team_outcomes=outcomes,
                    )
                )

            debrief_payload = MatchDebriefPayload(standings=standings, cases=cases).model_dump()

        await self.broadcast_room_state(room)
        debrief_msg = _envelope("MATCH_DEBRIEF", debrief_payload)
        for sess in list(room.sessions.values()):
            await self._send_safe(sess.websocket, debrief_msg)
        for _, ws in list(room.observers):
            await self._send_safe(ws, debrief_msg)
        return debrief_payload

    async def tick_once(self, room_code: str) -> None:
        """Advances SLA timers by 1 second when room status is ACTIVE (frozen when PAUSED)."""
        room = self.rooms.get(room_code)
        if not room:
            return

        events: list[tuple[str, str, str]] = []
        changed = False
        async with room.lock:
            if room.status != "ACTIVE":
                return
            for team in room.teams.values():
                if team.is_breached:
                    continue
                for alert in team.alerts.values():
                    if alert.status not in ("UNCLAIMED", "CLAIMED"):
                        continue
                    if alert.remaining_sla > 0:
                        alert.remaining_sla -= 1
                        changed = True
                    if alert.remaining_sla == 0:
                        alert.status = "EXPIRED"
                        alert.claimed_by_session_token = None
                        alert.claimed_by_player_id = None
                        alert.claimed_by_nickname = None
                        alert.claimed_by_avatar_id = None

                        srv = alert.scenario.server_only
                        pub = alert.scenario.public_alert
                        ev = evaluate_timeout(srv.ground_truth, srv.hp_penalty_on_miss)
                        alert.outcome = ev.outcome
                        team.score += ev.score_delta
                        team.hp = max(0, team.hp + ev.hp_delta)
                        team.streak = 0
                        if team.hp == 0:
                            team.is_breached = True
                            events.append(("THREAT", team.name, f"{team.name} SLA aşımı sonrası 0 HP ile BREACHED oldu!"))
                        else:
                            sev = "THREAT" if srv.ground_truth == "TP" else "WARN"
                            events.append((sev, team.name, f"{team.name} — {pub.incident_code} SLA süresi doldu! ({ev.score_delta} Puan, {ev.hp_delta} HP)"))

        for sev, tname, msg in events:
            await self.broadcast_feed(room, sev, tname, msg)
        if changed:
            await self.broadcast_room_state(room)

    async def _sla_tick_loop(self, room_code: str) -> None:
        try:
            while True:
                await asyncio.sleep(self.tick_interval_seconds)
                room = self.rooms.get(room_code)
                if not room or room.status == "ENDED":
                    break
                await self.tick_once(room_code)
        except asyncio.CancelledError:
            return
