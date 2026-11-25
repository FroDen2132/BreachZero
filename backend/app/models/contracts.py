"""Frozen Day-1 Pydantic v2 contracts matching docs/CONTRACTS.md."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

AlertSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AlertStatus = Literal["UNCLAIMED", "CLAIMED", "RESOLVED", "EXPIRED"]
DecisionType = Literal["TP", "FP"]
EnricherStatus = Literal["OK", "NOT_FOUND", "UNAVAILABLE"]
VerdictSignal = Literal["BENIGN", "SUSPICIOUS", "MALICIOUS", "INFO"]
SourceMode = Literal["mock", "cache", "live", "fallback"]
RoomStatus = Literal["LOBBY", "ACTIVE", "PAUSED", "ENDED"]
ClientRole = Literal["PLAYER", "HOST", "ADMIN"]
IocType = Literal["ip", "hash", "domain", "hostname", "username"]


class AlertEndpoint(BaseModel):
    ip: Optional[str] = None
    port: Optional[int] = None
    hostname: Optional[str] = None
    vlan: Optional[str] = None


class AlertHost(BaseModel):
    hostname: str
    os: Optional[str] = None


class AlertUser(BaseModel):
    name: str
    department: Optional[str] = None


class AlertProcess(BaseModel):
    name: str
    command_line: Optional[str] = None
    parent_name: Optional[str] = None


class AlertFile(BaseModel):
    name: Optional[str] = None
    sha256: Optional[str] = None


class AlertIndicators(BaseModel):
    ips: list[str] = Field(default_factory=list)
    hashes: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    usernames: list[str] = Field(default_factory=list)
    hostnames: list[str] = Field(default_factory=list)


class EvidenceCard(BaseModel):
    enricher_id: str
    display_name: str
    icon_id: str
    status: EnricherStatus = "OK"
    verdict_signal: VerdictSignal = "INFO"
    summary: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    query_cost_applied: int = 0
    source_mode: SourceMode = "live"
    fetched_at_utc: str


class PublicAlert(BaseModel):
    """Outbound-safe alert payload sent to /play; strictly excludes server_only fields."""

    model_config = ConfigDict(extra="forbid")

    alert_id: str
    incident_code: str
    title: str
    severity: AlertSeverity
    timestamp_utc: str
    sla_seconds: int = Field(gt=0)
    remaining_sla: int = Field(ge=0)
    status: AlertStatus = "UNCLAIMED"
    claimed_by_player_id: Optional[str] = None
    claimed_by_nickname: Optional[str] = None
    claimed_by_avatar_id: Optional[str] = None
    source: AlertEndpoint
    destination: AlertEndpoint
    host: AlertHost
    user: AlertUser
    process: Optional[AlertProcess] = None
    file: Optional[AlertFile] = None
    raw_log: str
    indicators: AlertIndicators
    available_enrichers: list[str] = Field(default_factory=list)
    evidence_cards: list[EvidenceCard] = Field(default_factory=list)


class ScenarioMeta(BaseModel):
    pack_id: str
    difficulty: Literal["EASY", "MEDIUM", "HARD"] = "MEDIUM"
    estimated_wave: int = Field(default=1, ge=1)
    author: str = "kulup-senaryo-ekibi"


class ScenarioPublicAlertSpec(BaseModel):
    alert_id: str
    incident_code: str
    title: str
    severity: AlertSeverity
    timestamp_utc: str
    sla_seconds: int = Field(gt=0)
    source: AlertEndpoint
    destination: AlertEndpoint
    host: AlertHost
    user: AlertUser
    process: Optional[AlertProcess] = None
    file: Optional[AlertFile] = None
    raw_log: str
    indicators: AlertIndicators
    available_enrichers: list[str] = Field(default_factory=list)


class MockEnrichmentCard(BaseModel):
    enricher_id: str
    display_name: str
    icon_id: str
    status: EnricherStatus = "OK"
    verdict_signal: VerdictSignal = "INFO"
    summary: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    source_mode: SourceMode = "mock"


class ScenarioServerOnly(BaseModel):
    ground_truth: DecisionType
    hp_penalty_on_miss: int = Field(ge=0)
    mitre_attack: list[str] = Field(default_factory=list)
    category: str
    required_evidence_hints: list[str] = Field(default_factory=list)
    debrief_explanation: str = Field(min_length=10)
    mock_enrichment: dict[str, MockEnrichmentCard] = Field(default_factory=dict)


class ScenarioFile(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    meta: ScenarioMeta
    public_alert: ScenarioPublicAlertSpec
    server_only: ScenarioServerOnly

    @model_validator(mode="after")
    def _validate_cross_fields(self) -> "ScenarioFile":
        avail = set(self.public_alert.available_enrichers)
        mocks = set(self.server_only.mock_enrichment.keys())
        if avail != mocks:
            raise ValueError(
                f"available_enrichers ({sorted(avail)}) must match mock_enrichment keys ({sorted(mocks)})"
            )
        if self.server_only.ground_truth == "FP" and self.server_only.hp_penalty_on_miss != 0:
            raise ValueError("FP scenario must have hp_penalty_on_miss == 0")
        return self


class ScenarioSummary(BaseModel):
    """Non-spoiler scenario metadata exposed to /admin before match start."""

    alert_id: str
    incident_code: str
    title: str
    severity: AlertSeverity
    difficulty: str
    estimated_wave: int
    sla_seconds: int
    available_enrichers: list[str]


class TeamPublicSummary(BaseModel):
    team_id: str
    name: str
    score: int
    hp: int
    streak: int
    resolved_count: int
    is_breached: bool
    queue: list[PublicAlert] = Field(default_factory=list)


class RoomStatePayload(BaseModel):
    room_code: str
    status: RoomStatus
    current_wave: int
    total_waves: int
    teams: list[TeamPublicSummary]


class FeedEventPayload(BaseModel):
    event_id: str
    severity: Literal["INFO", "SAFE", "WARN", "THREAT"]
    team_name: str
    message: str


class DebriefStanding(BaseModel):
    rank: int
    team_id: str
    name: str
    score: int
    hp: int
    is_breached: bool


class DebriefCaseSummary(BaseModel):
    alert_id: str
    incident_code: str
    title: str
    ground_truth: DecisionType
    mitre_attack: list[str]
    debrief_explanation: str
    team_outcomes: dict[str, str]


class MatchDebriefPayload(BaseModel):
    standings: list[DebriefStanding]
    cases: list[DebriefCaseSummary]


class CreateRoomRequest(BaseModel):
    team_names: Optional[list[str]] = None
    total_waves: int = Field(default=2, ge=1, le=10)


class CreateRoomResponse(BaseModel):
    room_code: str
    admin_token: str
    teams: list[dict[str, str]]


class WsEnvelope(BaseModel):
    type: str
    request_id: Optional[str] = None
    timestamp: str
    payload: dict[str, Any] = Field(default_factory=dict)
