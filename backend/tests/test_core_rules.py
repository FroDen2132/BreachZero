"""Core automated tests verifying security boundaries, claim locking, evidence persistence, and scoring."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.room_manager import RoomError  # noqa: E402
from app.main import create_app  # noqa: E402

SPOILER_STRINGS = (
    "ground_truth",
    "server_only",
    "debrief_explanation",
    "mock_enrichment",
    "mitre_attack",
    "hp_penalty_on_miss",
)


def test_zero_server_only_leakage_across_rest_and_ws(tmp_path: Path) -> None:
    app = create_app(
        scenarios_dir=REPO_ROOT / "scenarios",
        cache_db_path=tmp_path / "cache.db",
        tick_interval_seconds=60.0,
    )
    with TestClient(app) as client:
        sc_resp = client.get("/api/scenarios")
        assert sc_resp.status_code == 200
        sc_text = sc_resp.text
        for secret in SPOILER_STRINGS:
            assert secret not in sc_text

        room_resp = client.post("/api/rooms", json={"total_waves": 2}).json()
        code = room_resp["room_code"]
        admin_token = room_resp["admin_token"]

        summary_resp = client.get(f"/api/rooms/{code}")
        assert summary_resp.status_code == 200
        for secret in SPOILER_STRINGS:
            assert secret not in summary_resp.text

        with client.websocket_connect(f"/ws/room/{code}") as ws_admin, client.websocket_connect(
            f"/ws/room/{code}"
        ) as ws_player:
            ws_admin.send_json(
                {
                    "type": "JOIN_ROOM",
                    "timestamp": "2026-11-25T14:00:00Z",
                    "payload": {"role": "ADMIN", "admin_token": admin_token},
                }
            )
            ws_admin.receive_json()  # SESSION_READY
            ws_admin.receive_json()  # ROOM_STATE_UPDATE

            ws_player.send_json(
                {
                    "type": "JOIN_ROOM",
                    "timestamp": "2026-11-25T14:00:00Z",
                    "payload": {"role": "PLAYER", "team_id": "team_1", "nickname": "Ali", "avatar_id": "analyst-ali"},
                }
            )
            ws_player.receive_json()  # SESSION_READY
            ws_player.receive_json()  # ROOM_STATE_UPDATE

            ws_admin.send_json(
                {
                    "type": "ADMIN_START_WAVE",
                    "timestamp": "2026-11-25T14:00:01Z",
                    "payload": {"scenario_ids": ["case_01_fp_backup", "case_02_tp_kerberoast"]},
                }
            )
            _ = ws_player.receive_json()  # FEED_EVENT
            state_msg = ws_player.receive_json()  # ROOM_STATE_UPDATE
            raw_state = json.dumps(state_msg, ensure_ascii=False)
            for secret in SPOILER_STRINGS:
                assert secret not in raw_state

            ws_player.send_json(
                {
                    "type": "CLAIM_ALERT",
                    "timestamp": "2026-11-25T14:00:02Z",
                    "payload": {"alert_id": "case_02_tp_kerberoast"},
                }
            )
            _ = ws_player.receive_json()  # ROOM_STATE_UPDATE

            ws_player.send_json(
                {
                    "type": "RUN_ENRICHER",
                    "timestamp": "2026-11-25T14:00:03Z",
                    "payload": {"alert_id": "case_02_tp_kerberoast", "enricher_id": "ip_reputation"},
                }
            )
            enriched_msg = ws_player.receive_json()  # ALERT_ENRICHED
            assert enriched_msg["type"] == "ALERT_ENRICHED"
            for secret in SPOILER_STRINGS:
                assert secret not in json.dumps(enriched_msg, ensure_ascii=False)
            _ = ws_player.receive_json()  # ROOM_STATE_UPDATE

            # End match -> MATCH_DEBRIEF reveals ground_truth & mitre_attack intentionally
            ws_admin.send_json({"type": "ADMIN_END_MATCH", "timestamp": "2026-11-25T14:00:04Z", "payload": {}})
            _ = ws_player.receive_json()  # ROOM_STATE_UPDATE
            debrief = ws_player.receive_json()
            assert debrief["type"] == "MATCH_DEBRIEF"
            assert debrief["payload"]["cases"][0]["ground_truth"] in ("TP", "FP")


def test_concurrent_claim_single_winner_and_owner_enforcement(tmp_path: Path) -> None:
    async def _run() -> None:
        app = create_app(
            scenarios_dir=REPO_ROOT / "scenarios",
            cache_db_path=tmp_path / "cache.db",
            tick_interval_seconds=60.0,
        )
        rm = app.state.room_manager
        room = rm.create_room()
        s1, _ = await rm.join_room(room.room_code, "PLAYER", None, team_id="team_1", nickname="Ali")
        s2, _ = await rm.join_room(room.room_code, "PLAYER", None, team_id="team_1", nickname="Zeynep")
        assert s1 and s2
        await rm.admin_start_wave(room.room_code, room.admin_token, ["case_02_tp_kerberoast"])

        # Unclaimed submit must fail with ALERT_NOT_CLAIMED
        try:
            await rm.submit_decision(room.room_code, s1.session_token, "case_02_tp_kerberoast", "TP")
            assert False, "Expected ALERT_NOT_CLAIMED"
        except RoomError as exc:
            assert exc.code == "ALERT_NOT_CLAIMED"

        # Two teammates race to claim the same alert concurrently
        results = await asyncio.gather(
            rm.claim_alert(room.room_code, s1.session_token, "case_02_tp_kerberoast"),
            rm.claim_alert(room.room_code, s2.session_token, "case_02_tp_kerberoast"),
            return_exceptions=True,
        )
        successes = [r for r in results if r is None]
        errors = [r for r in results if isinstance(r, RoomError)]
        assert len(successes) == 1
        assert len(errors) == 1 and errors[0].code == "ALERT_ALREADY_CLAIMED"

        alert = room.teams["team_1"].alerts["case_02_tp_kerberoast"]
        owner_tok = alert.claimed_by_session_token
        other_tok = s2.session_token if owner_tok == s1.session_token else s1.session_token

        # Non-owner cannot release or submit decision
        for fn in (
            rm.release_alert(room.room_code, other_tok, "case_02_tp_kerberoast"),
            rm.submit_decision(room.room_code, other_tok, "case_02_tp_kerberoast", "TP"),
        ):
            try:
                await fn
                assert False, "Expected NOT_CLAIM_OWNER"
            except RoomError as exc:
                assert exc.code == "NOT_CLAIM_OWNER"

    asyncio.run(_run())


def test_release_persists_evidence_and_zero_duplicate_cost(tmp_path: Path) -> None:
    async def _run() -> None:
        app = create_app(
            scenarios_dir=REPO_ROOT / "scenarios",
            cache_db_path=tmp_path / "cache.db",
            tick_interval_seconds=60.0,
        )
        rm = app.state.room_manager
        room = rm.create_room()
        s1, _ = await rm.join_room(room.room_code, "PLAYER", None, team_id="team_1", nickname="Ali")
        s2, _ = await rm.join_room(room.room_code, "PLAYER", None, team_id="team_1", nickname="Kerem")
        assert s1 and s2
        await rm.admin_start_wave(room.room_code, room.admin_token, ["case_01_fp_backup"])

        await rm.claim_alert(room.room_code, s1.session_token, "case_01_fp_backup")
        card1 = await rm.run_enricher(room.room_code, s1.session_token, "case_01_fp_backup", "internal_cmdb")
        assert card1.query_cost_applied == -10
        assert room.teams["team_1"].score == -10

        await rm.release_alert(room.room_code, s1.session_token, "case_01_fp_backup")
        await rm.claim_alert(room.room_code, s2.session_token, "case_01_fp_backup")

        alert = room.teams["team_1"].alerts["case_01_fp_backup"]
        assert len(alert.evidence_cards) == 1
        assert alert.evidence_cards[0].enricher_id == "internal_cmdb"

        # Running same enricher again on the same ticket costs 0
        card2 = await rm.run_enricher(room.room_code, s2.session_token, "case_01_fp_backup", "internal_cmdb")
        assert card2.query_cost_applied == 0
        assert room.teams["team_1"].score == -10

    asyncio.run(_run())


def test_fn_penalty_breach_meter_and_breached_lockout(tmp_path: Path) -> None:
    async def _run() -> None:
        app = create_app(
            scenarios_dir=REPO_ROOT / "scenarios",
            cache_db_path=tmp_path / "cache.db",
            tick_interval_seconds=60.0,
        )
        rm = app.state.room_manager
        room = rm.create_room()
        s1, _ = await rm.join_room(room.room_code, "PLAYER", None, team_id="team_1", nickname="Elif")
        assert s1
        await rm.admin_start_wave(room.room_code, room.admin_token, ["case_02_tp_kerberoast"])

        # case_02 has hp_penalty_on_miss = 40; FN => -250 score and -40 HP
        await rm.claim_alert(room.room_code, s1.session_token, "case_02_tp_kerberoast")
        res = await rm.submit_decision(room.room_code, s1.session_token, "case_02_tp_kerberoast", "FP")
        assert res["outcome"] == "FALSE_NEGATIVE"
        assert res["score_delta"] == -250
        assert res["hp_delta"] == -40
        assert room.teams["team_1"].hp == 60

        # Simulate two more TP timeouts (40 + 40 -> clamped to 0 HP => BREACHED)
        for wave in (2, 3):
            room.teams["team_1"].alerts.clear()
            await rm.admin_start_wave(room.room_code, room.admin_token, ["case_02_tp_kerberoast"], wave_number=wave)
            await rm.claim_alert(room.room_code, s1.session_token, "case_02_tp_kerberoast")
            await rm.submit_decision(room.room_code, s1.session_token, "case_02_tp_kerberoast", "FP")

        assert room.teams["team_1"].hp == 0
        assert room.teams["team_1"].is_breached is True

        # Breached team cannot claim new alerts
        try:
            await rm.claim_alert(room.room_code, s1.session_token, "case_02_tp_kerberoast")
            assert False, "Expected TEAM_BREACHED"
        except RoomError as exc:
            assert exc.code == "TEAM_BREACHED"

    asyncio.run(_run())


def test_admin_pause_freezes_sla_and_f5_reconnect_keeps_claim(tmp_path: Path) -> None:
    async def _run() -> None:
        app = create_app(
            scenarios_dir=REPO_ROOT / "scenarios",
            cache_db_path=tmp_path / "cache.db",
            reconnect_grace_seconds=0.15,
            tick_interval_seconds=60.0,
        )
        rm = app.state.room_manager
        room = rm.create_room()

        class DummyWS:
            async def send_json(self, _data: dict) -> None:
                return None

        ws1 = DummyWS()
        s1, _ = await rm.join_room(room.room_code, "PLAYER", ws1, team_id="team_1", nickname="Ali")  # type: ignore[arg-type]
        assert s1
        await rm.admin_start_wave(room.room_code, room.admin_token, ["case_01_fp_backup"])
        await rm.claim_alert(room.room_code, s1.session_token, "case_01_fp_backup")
        await rm.run_enricher(room.room_code, s1.session_token, "case_01_fp_backup", "internal_cmdb")

        initial_sla = room.teams["team_1"].alerts["case_01_fp_backup"].remaining_sla
        await rm.tick_once(room.room_code)
        assert room.teams["team_1"].alerts["case_01_fp_backup"].remaining_sla == initial_sla - 1

        # Pause freezes SLA and blocks mutations
        await rm.admin_pause_wave(room.room_code, room.admin_token, "Mola")
        await rm.tick_once(room.room_code)
        await rm.tick_once(room.room_code)
        assert room.teams["team_1"].alerts["case_01_fp_backup"].remaining_sla == initial_sla - 1

        try:
            await rm.submit_decision(room.room_code, s1.session_token, "case_01_fp_backup", "FP")
            assert False, "Expected ROOM_PAUSED"
        except RoomError as exc:
            assert exc.code == "ROOM_PAUSED"

        await rm.admin_resume_wave(room.room_code, room.admin_token)

        # Simulate F5 disconnect + fast reconnect within grace period
        await rm.handle_disconnect(room.room_code, ws1)  # type: ignore[arg-type]
        ws2 = DummyWS()
        re_sess, ready_msg = await rm.join_room(
            room.room_code,
            "PLAYER",
            ws2,  # type: ignore[arg-type]
            session_token=s1.session_token,
        )
        assert re_sess is s1
        assert ready_msg["payload"]["reconnected"] is True
        await asyncio.sleep(0.22)  # Grace timer cancelled, claim must still belong to Ali
        assert room.teams["team_1"].alerts["case_01_fp_backup"].status == "CLAIMED"
        assert room.teams["team_1"].alerts["case_01_fp_backup"].claimed_by_session_token == s1.session_token

        # Now disconnect without reconnecting -> auto-release after grace period, evidence kept
        await rm.handle_disconnect(room.room_code, ws2)  # type: ignore[arg-type]
        await asyncio.sleep(0.25)
        alert = room.teams["team_1"].alerts["case_01_fp_backup"]
        assert alert.status == "UNCLAIMED"
        assert len(alert.evidence_cards) == 1

    asyncio.run(_run())


def test_scenario_loader_skips_invalid_json(tmp_path: Path) -> None:
    sc_dir = tmp_path / "scenarios"
    sc_dir.mkdir()
    valid_src = (REPO_ROOT / "scenarios" / "case_01_fp_backup.json").read_text(encoding="utf-8")
    (sc_dir / "valid.json").write_text(valid_src, encoding="utf-8")
    (sc_dir / "broken.json").write_text('{"schema_version": "1.0", "bad": true}', encoding="utf-8")

    app = create_app(scenarios_dir=sc_dir, cache_db_path=tmp_path / "cache.db")
    loader = app.state.scenario_loader
    assert len(loader.list_all()) == 1
    assert loader.invalid_files == ["broken.json"]
