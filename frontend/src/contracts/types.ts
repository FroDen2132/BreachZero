export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'UNCLAIMED' | 'CLAIMED' | 'RESOLVED' | 'EXPIRED';
export type DecisionType = 'TP' | 'FP';
export type EnricherStatus = 'OK' | 'NOT_FOUND' | 'UNAVAILABLE';
export type VerdictSignal = 'BENIGN' | 'SUSPICIOUS' | 'MALICIOUS' | 'INFO';
export type SourceMode = 'mock' | 'cache' | 'live' | 'fallback';
export type RoomStatus = 'LOBBY' | 'ACTIVE' | 'PAUSED' | 'ENDED';
export type ClientRole = 'PLAYER' | 'HOST' | 'ADMIN';

export interface AlertEndpoint {
  ip?: string | null;
  port?: number | null;
  hostname?: string | null;
  vlan?: string | null;
}

export interface EvidenceCard {
  enricher_id: string;
  display_name: string;
  icon_id: string;
  status: EnricherStatus;
  verdict_signal: VerdictSignal;
  summary: string;
  details: Record<string, string | number | boolean | null>;
  query_cost_applied: number;
  source_mode: SourceMode;
  fetched_at_utc: string;
}

export interface PublicAlert {
  alert_id: string;
  incident_code: string;
  title: string;
  severity: AlertSeverity;
  timestamp_utc: string;
  sla_seconds: number;
  remaining_sla: number;
  status: AlertStatus;
  claimed_by_player_id?: string | null;
  claimed_by_nickname?: string | null;
  claimed_by_avatar_id?: string | null;
  source: AlertEndpoint;
  destination: AlertEndpoint;
  host: { hostname: string; os?: string | null };
  user: { name: string; department?: string | null };
  process?: { name: string; command_line?: string | null; parent_name?: string | null } | null;
  file?: { name?: string | null; sha256?: string | null } | null;
  raw_log: string;
  indicators: {
    ips: string[];
    hashes: string[];
    domains: string[];
    usernames: string[];
    hostnames: string[];
  };
  available_enrichers: string[];
  evidence_cards: EvidenceCard[];
}

export interface TeamPublicSummary {
  team_id: string;
  name: string;
  score: number;
  hp: number;
  streak: number;
  resolved_count: number;
  is_breached: boolean;
  queue: PublicAlert[];
}

export interface RoomStatePayload {
  room_code: string;
  status: RoomStatus;
  current_wave: number;
  total_waves: number;
  teams: TeamPublicSummary[];
}

export interface FeedEventPayload {
  event_id: string;
  severity: 'INFO' | 'SAFE' | 'WARN' | 'THREAT';
  team_name: string;
  message: string;
}

export interface DecisionResultPayload {
  alert_id: string;
  accepted: boolean;
  outcome: string;
  score_delta: number;
  hp_delta: number;
  new_score: number;
  new_hp: number;
  new_streak: number;
}

export interface DebriefStanding {
  rank: number;
  team_id: string;
  name: string;
  score: number;
  hp: number;
  is_breached: boolean;
}

export interface DebriefCaseSummary {
  alert_id: string;
  incident_code: string;
  title: string;
  ground_truth: DecisionType;
  mitre_attack: string[];
  debrief_explanation: string;
  team_outcomes: Record<string, string>;
}

export interface MatchDebriefPayload {
  standings: DebriefStanding[];
  cases: DebriefCaseSummary[];
}

export interface ScenarioSummary {
  alert_id: string;
  incident_code: string;
  title: string;
  severity: AlertSeverity;
  difficulty: string;
  estimated_wave: number;
  sla_seconds: number;
  available_enrichers: string[];
}

export interface SessionReadyPayload {
  session_token: string | null;
  player_id: string | null;
  team_id: string | null;
  role: ClientRole;
  reconnected: boolean;
  reconnect_grace_seconds: number;
}

export interface WsEnvelope<T = Record<string, unknown>> {
  type: string;
  request_id?: string | null;
  timestamp: string;
  payload: T;
}

export const ANALYST_AVATARS = [
  { id: 'analyst-ali', label: 'Ali' },
  { id: 'analyst-zeynep', label: 'Zeynep' },
  { id: 'analyst-kerem', label: 'Kerem' },
  { id: 'analyst-elif', label: 'Elif' },
] as const;

export const ENRICHER_LABELS: Record<string, { label: string; iconId: string }> = {
  ip_reputation: { label: '[IP İTİBAR]', iconId: 'tool-ip-radar' },
  hash_vt: { label: '[HASH / VT]', iconId: 'tool-hash-scanner' },
  internal_cmdb: { label: '[İÇ CMDB]', iconId: 'tool-cmdb-server' },
  whois: { label: '[WHOIS]', iconId: 'fallback-globe' },
};
