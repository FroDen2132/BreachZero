"""FastAPI REST endpoints and Native WebSocket gateway for BreachZero."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from app.core.room_manager import RoomError, RoomManager, _envelope
from app.models.contracts import CreateRoomRequest, CreateRoomResponse, ScenarioSummary

router = APIRouter()


def _get_manager(obj: Any) -> RoomManager:
    return obj.app.state.room_manager


@router.get("/api/health")
async def health_check(request: Request) -> dict[str, Any]:
    loader = request.app.state.scenario_loader
    return {
        "status": "ok",
        "scenarios_loaded": len(loader.list_all()),
        "invalid_scenarios": loader.invalid_files,
    }


@router.get("/api/scenarios", response_model=list[ScenarioSummary])
async def list_scenarios(request: Request) -> list[ScenarioSummary]:
    loader = request.app.state.scenario_loader
    return loader.list_summaries()


@router.post("/api/rooms", response_model=CreateRoomResponse)
async def create_room(body: CreateRoomRequest, request: Request) -> CreateRoomResponse:
    rm = _get_manager(request)
    room = rm.create_room(team_names=body.team_names, total_waves=body.total_waves)
    return CreateRoomResponse(
        room_code=room.room_code,
        admin_token=room.admin_token,
        teams=[{"team_id": t.team_id, "name": t.name} for t in room.teams.values()],
    )


@router.get("/api/rooms/{room_code}")
async def get_room_summary(room_code: str, request: Request) -> dict[str, Any]:
    rm = _get_manager(request)
    try:
        room = rm.get_room(room_code)
    except RoomError as exc:
        raise HTTPException(status_code=404, detail=exc.message) from exc
    return rm.build_room_state_payload(room, role="HOST", team_id=None)


@router.websocket("/ws/room/{room_code}")
async def room_websocket(websocket: WebSocket, room_code: str) -> None:
    await websocket.accept()
    rm = _get_manager(websocket)
    bound_session_token: Optional[str] = None
    bound_role: Optional[str] = None
    bound_admin_token: Optional[str] = None

    try:
        while True:
            raw_msg = await websocket.receive_json()
            msg_type = str(raw_msg.get("type", "")).upper()
            req_id = raw_msg.get("request_id")
            payload = raw_msg.get("payload") or {}

            try:
                if msg_type == "JOIN_ROOM":
                    role = str(payload.get("role", "PLAYER")).upper()
                    if role not in ("PLAYER", "HOST", "ADMIN"):
                        raise RoomError("INVALID_ROLE", f"Geçersiz rol: {role}")

                    sess, ready_msg = await rm.join_room(
                        room_code=room_code,
                        role=role,  # type: ignore[arg-type]
                        websocket=websocket,
                        team_id=payload.get("team_id"),
                        nickname=payload.get("nickname"),
                        avatar_id=payload.get("avatar_id") or "analyst-ali",
                        session_token=payload.get("session_token"),
                        admin_token=payload.get("admin_token"),
                        request_id=req_id,
                    )
                    bound_role = role
                    if sess is not None:
                        bound_session_token = sess.session_token
                    if role == "ADMIN":
                        bound_admin_token = payload.get("admin_token")

                    await websocket.send_json(ready_msg)
                    room = rm.get_room(room_code)
                    state_payload = rm.build_room_state_payload(
                        room,
                        role,  # type: ignore[arg-type]
                        sess.team_id if sess else None,
                    )
                    await websocket.send_json(_envelope("ROOM_STATE_UPDATE", state_payload))

                elif msg_type == "CLAIM_ALERT":
                    if not bound_session_token:
                        raise RoomError("INVALID_SESSION", "Önce JOIN_ROOM ile odaya katılın.")
                    await rm.claim_alert(room_code, bound_session_token, str(payload.get("alert_id", "")))

                elif msg_type == "RELEASE_ALERT":
                    if not bound_session_token:
                        raise RoomError("INVALID_SESSION", "Önce JOIN_ROOM ile odaya katılın.")
                    await rm.release_alert(room_code, bound_session_token, str(payload.get("alert_id", "")))

                elif msg_type == "RUN_ENRICHER":
                    if not bound_session_token:
                        raise RoomError("INVALID_SESSION", "Önce JOIN_ROOM ile odaya katılın.")
                    await rm.run_enricher(
                        room_code=room_code,
                        session_token=bound_session_token,
                        alert_id=str(payload.get("alert_id", "")),
                        enricher_id=str(payload.get("enricher_id", "")),
                        ioc_value=payload.get("ioc_value"),
                        request_id=req_id,
                    )

                elif msg_type == "SUBMIT_DECISION":
                    if not bound_session_token:
                        raise RoomError("INVALID_SESSION", "Önce JOIN_ROOM ile odaya katılın.")
                    decision = str(payload.get("decision", "")).upper()
                    if decision not in ("TP", "FP"):
                        raise RoomError("INVALID_DECISION", "Karar yalnızca TP veya FP olabilir.")
                    await rm.submit_decision(
                        room_code=room_code,
                        session_token=bound_session_token,
                        alert_id=str(payload.get("alert_id", "")),
                        decision=decision,  # type: ignore[arg-type]
                        request_id=req_id,
                    )

                elif msg_type == "ADMIN_START_WAVE":
                    if bound_role != "ADMIN" or not bound_admin_token:
                        raise RoomError("INVALID_SESSION", "Yalnızca yetkili ADMIN dalga başlatabilir.")
                    await rm.admin_start_wave(
                        room_code=room_code,
                        admin_token=bound_admin_token,
                        scenario_ids=payload.get("scenario_ids"),
                        wave_number=payload.get("wave_number"),
                    )

                elif msg_type == "ADMIN_PAUSE_WAVE":
                    if bound_role != "ADMIN" or not bound_admin_token:
                        raise RoomError("INVALID_SESSION", "Yalnızca yetkili ADMIN duraklatabilir.")
                    await rm.admin_pause_wave(
                        room_code=room_code,
                        admin_token=bound_admin_token,
                        reason=str(payload.get("reason", "")),
                    )

                elif msg_type == "ADMIN_RESUME_WAVE":
                    if bound_role != "ADMIN" or not bound_admin_token:
                        raise RoomError("INVALID_SESSION", "Yalnızca yetkili ADMIN devam ettirebilir.")
                    await rm.admin_resume_wave(room_code=room_code, admin_token=bound_admin_token)

                elif msg_type == "ADMIN_END_MATCH":
                    if bound_role != "ADMIN" or not bound_admin_token:
                        raise RoomError("INVALID_SESSION", "Yalnızca yetkili ADMIN maçı bitirebilir.")
                    await rm.admin_end_match(room_code=room_code, admin_token=bound_admin_token)

                else:
                    raise RoomError("UNKNOWN_MESSAGE", f"Bilinmeyen mesaj tipi: {msg_type}")

            except RoomError as err:
                await websocket.send_json(
                    _envelope("ERROR", {"code": err.code, "message": err.message}, request_id=req_id)
                )

    except WebSocketDisconnect:
        await rm.handle_disconnect(room_code, websocket)
    except Exception:
        await rm.handle_disconnect(room_code, websocket)
