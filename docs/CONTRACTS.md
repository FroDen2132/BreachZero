# BreachZero — Day-1 Veri Sözleşmeleri ve Protokoller (`CONTRACTS.md`)

> **DONDURULMUŞ KONTRAT:** Sprint 1 başladığında Backend, Enricher, Frontend ve Senaryo ekipleri bu dosyadaki JSON şemalarına, WebSocket zarflarına ve `BaseEnricher` arayüzüne birebir uymak zorundadır. Bu dosyada yapılacak her değişiklik tüm ekip liderlerinin onayını gerektirir.

---

## 1. Hafifletilmiş OCSF/ECS Uyumlu `PublicAlert` ve `EvidenceCard` Şemaları

### 1.1 `PublicAlert` (İstemciye Gönderilen Güvenli Alarm Nesnesi)
Bu nesne `/play` ve `/host` ekranlarına gönderilebilen **tek** alarm temsilidir. Doğru cevap veya eğitim açıklaması **içermez**.

```typescript
// Frontend TypeScript karşılığı (frontend/src/contracts/alert.ts)
export type AlertSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type AlertStatus = "UNCLAIMED" | "CLAIMED" | "RESOLVED" | "EXPIRED";
export type DecisionType = "TP" | "FP";

export interface AlertEndpoint {
  ip?: string | null;
  port?: number | null;
  hostname?: string | null;
  vlan?: string | null;
}

export interface AlertIndicators {
  ips: string[];
  hashes: string[];
  domains: string[];
  usernames: string[];
  hostnames: string[];
}

export interface PublicAlert {
  alert_id: string;                 // Örn: "case_02_tp_kerberoast"
  incident_code: string;            // Saf ASCII sayaç/kod: "ALT-4088"
  title: string;                    // Türkçe okunabilir başlık
  severity: AlertSeverity;
  timestamp_utc: string;            // ISO-8601
  sla_seconds: number;              // Başlangıç SLA süresi (sn)
  remaining_sla: number;            // Sunucu tarafından güncellenen kalan sn
  status: AlertStatus;
  claimed_by_player_id?: string | null;
  claimed_by_nickname?: string | null;
  claimed_by_avatar_id?: string | null; // "analyst-ali" | "analyst-zeynep" | ...
  source: AlertEndpoint;            // ECS source.*
  destination: AlertEndpoint;       // ECS destination.*
  host: { hostname: string; os?: string | null };
  user: { name: string; department?: string | null };
  process?: { name: string; command_line?: string | null; parent_name?: string | null } | null;
  file?: { name?: string | null; sha256?: string | null } | null;
  raw_log: string;                  // IBM Plex Mono terminalinde gösterilecek ham log
  indicators: AlertIndicators;      // Enricher'ların hedefleyeceği IOC'ler
  available_enrichers: string[];    // ["ip_reputation", "hash_vt", "internal_cmdb", "whois"]
  evidence_cards: EvidenceCard[];   // Takım tarafından şu ana kadar toplanan kanıtlar
}
```

### 1.2 `EvidenceCard` (Normalize Edilmiş Araç Çıktısı)
Tüm enrichment eklentileri farklı dış API formatlarını bu tek standart karta dönüştürür:

```typescript
export type EnricherStatus = "OK" | "NOT_FOUND" | "UNAVAILABLE";
export type VerdictSignal = "BENIGN" | "SUSPICIOUS" | "MALICIOUS" | "INFO";
export type SourceMode = "mock" | "cache" | "live" | "fallback";

export interface EvidenceCard {
  enricher_id: string;              // Örn: "ip_reputation", "whois"
  display_name: string;             // Örn: "IP İtibar"
  icon_id: string;                  // "tool-ip-radar" veya SVG fallback id ("fallback-globe")
  status: EnricherStatus;           // "UNAVAILABLE" ise puan kesilmez
  verdict_signal: VerdictSignal;    // UI terminal satır rengini belirler
  summary: string;                  // Tek satırlık yüksek kontrastlı Türkçe özet
  details: Record<string, string | number | boolean | null>;
  query_cost_applied: number;       // Sunucu tarafından hesaplanır (genelde -10 veya 0)
  source_mode: SourceMode;
  fetched_at_utc: string;
}
```

---

## 2. `ScenarioFile` JSON Şeması (`schema_version: "1.0"`)

> **KRİTİK GÜVENLİK SINIRI:** `ScenarioFile` içinde **`meta`** ve **`public_alert`** dışındaki hiçbir alan aktif oyun sırasında `/play` veya `/host` istemcilerine gönderilemez. `ground_truth`, `hp_penalty_on_miss`, `mitre_attack`, `category`, `required_evidence_hints`, `debrief_explanation` ve `mock_enrichment` alanları yalnızca `server_only` bloğunda yer alır.

```json
{
  "schema_version": "1.0",
  "meta": {
    "pack_id": "soc_fundamentals_v1",
    "difficulty": "MEDIUM",
    "estimated_wave": 1,
    "author": "kulup-senaryo-ekibi"
  },
  "public_alert": {
    "alert_id": "case_01_fp_backup",
    "incident_code": "ALT-1001",
    "title": "Gece Yüksek Hacimli PowerShell ve SMB Veri Aktarımı",
    "severity": "HIGH",
    "timestamp_utc": "2026-11-25T03:15:12Z",
    "sla_seconds": 90,
    "source": { "ip": "10.40.12.10", "port": 51422, "hostname": "BACKUP-SRV-01", "vlan": "VLAN-40-INFRA" },
    "destination": { "ip": "10.20.5.14", "port": 445, "hostname": "FIN-DB-02", "vlan": "VLAN-20-FINANCE" },
    "host": { "hostname": "BACKUP-SRV-01", "os": "Windows Server 2022" },
    "user": { "name": "svc_veeam_backup", "department": "IT Altyapı" },
    "process": {
      "name": "powershell.exe",
      "parent_name": "Veeam.Backup.Service.exe",
      "command_line": "powershell.exe -NoProfile -File C:\\Scripts\\NightlyDbSnapshot.ps1"
    },
    "file": {
      "name": "NightlyDbSnapshot.ps1",
      "sha256": "a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcd01"
    },
    "raw_log": "2026-11-25T03:15:12Z BACKUP-SRV-01 WinEvent[4688]: User=svc_veeam_backup -> FIN-DB-02:445/SMB BytesOut=4.2GB",
    "indicators": {
      "ips": ["10.40.12.10", "10.20.5.14"],
      "hashes": ["a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcd01"],
      "domains": [],
      "usernames": ["svc_veeam_backup"],
      "hostnames": ["BACKUP-SRV-01", "FIN-DB-02"]
    },
    "available_enrichers": ["internal_cmdb", "hash_vt", "ip_reputation"]
  },
  "server_only": {
    "ground_truth": "FP",
    "hp_penalty_on_miss": 0,
    "mitre_attack": [],
    "category": "scheduled_maintenance",
    "required_evidence_hints": ["internal_cmdb", "hash_vt"],
    "debrief_explanation": "Maç sonu oyuncuya gösterilecek teknik Türkçe açıklama.",
    "mock_enrichment": {
      "internal_cmdb": {
        "enricher_id": "internal_cmdb",
        "display_name": "İç CMDB",
        "icon_id": "tool-cmdb-server",
        "status": "OK",
        "verdict_signal": "BENIGN",
        "summary": "Özet metin...",
        "details": {},
        "source_mode": "mock"
      }
    }
  }
}
```

### Zorunluluk Kuralları
- `public_alert.available_enrichers` listesindeki her anahtar `server_only.mock_enrichment` içinde tanımlı olmalıdır (kurgusal/iç ağ IOC'lerinin kesintisiz çalışması için).
- `server_only.hp_penalty_on_miss`: `FP` vakalar için `0`, standart `TP` vakalar için `30`, kritik zafiyetler için `40` olarak ayarlanır.

---

## 3. Client ↔ Server WebSocket Protokolü

### Ortak Mesaj Zarfı (Envelope)
```json
{
  "type": "MESSAGE_TYPE",
  "request_id": "req-uuid-optional",
  "timestamp": "2026-11-25T14:20:00Z",
  "payload": {}
}
```

### 3.1 Client → Server Mesajları

| Mesaj Tipi | Yetki / Sahip Kuralı | Payload Örneği |
| :--- | :--- | :--- |
| `JOIN_ROOM` | Herkes (`/play`, `/host`, `/admin`). `F5` yenilemesinde `sessionStorage`'daki `session_token` ile 15s içinde aynı koltuğa döner. | `{"room_code":"BZ-4821","role":"PLAYER","team_id":"team_alpha","nickname":"Ali K.","avatar_id":"analyst-ali","session_token":null}` |
| `CLAIM_ALERT` | Aktif `/play` oyuncusu (takımı `BREACHED` değilse) | `{"alert_id":"case_02_tp_kerberoast"}` |
| `RELEASE_ALERT` | **Yalnızca** o bileti o an `CLAIM` etmiş `session_token` | `{"alert_id":"case_02_tp_kerberoast"}` |
| `RUN_ENRICHER` | **Yalnızca** o bileti o an `CLAIM` etmiş `session_token` | `{"alert_id":"case_02_tp_kerberoast","enricher_id":"ip_reputation","ioc_value":"185.220.101.44"}` |
| `SUBMIT_DECISION` | **Yalnızca** o bileti o an `CLAIM` etmiş `session_token` | `{"alert_id":"case_02_tp_kerberoast","decision":"TP"}` |
| `ADMIN_START_WAVE` | Geçerli `admin_token` | `{"wave_number":1,"scenario_ids":["case_01_fp_backup","case_02_tp_kerberoast"]}` |
| `ADMIN_PAUSE_WAVE` | Geçerli `admin_token` (Aktif tüm SLA sayaçlarını dondurur) | `{"reason":"Kısa teknik ara"}` |
| `ADMIN_RESUME_WAVE` | Geçerli `admin_token` | `{}` |
| `ADMIN_END_MATCH` | Geçerli `admin_token` | `{}` |
| `TRIGGER_SABOTAGE` | *(V2 Rezerve)* `5+` seri yakalamış takım | `{"target_team_id":"team_wolves"}` |

### 3.2 Server → Client Mesajları

1. **`SESSION_READY` (İstemciye özel — `JOIN_ROOM` yanıtı):**
```json
{
  "type": "SESSION_READY",
  "request_id": "req-001",
  "timestamp": "2026-11-25T14:20:01Z",
  "payload": {
    "session_token": "tok_9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c",
    "player_id": "plr_ali_01",
    "team_id": "team_alpha",
    "role": "PLAYER",
    "reconnected": false,
    "reconnect_grace_seconds": 15
  }
}
```

2. **`ROOM_STATE_UPDATE` (Oda durumu, takımlar, Breach Meter ve kuyruk özeti):**
```json
{
  "type": "ROOM_STATE_UPDATE",
  "request_id": null,
  "timestamp": "2026-11-25T14:20:05Z",
  "payload": {
    "room_code": "BZ-4821",
    "status": "ACTIVE",
    "current_wave": 1,
    "total_waves": 3,
    "teams": [
      {
        "team_id": "team_alpha",
        "name": "ALPHA SQUAD",
        "score": 320,
        "hp": 100,
        "streak": 2,
        "resolved_count": 2,
        "is_breached": false,
        "queue": []
      }
    ]
  }
}
```
> *Not:* `/play` istemcisi güvenlik ve bant genişliği için yalnızca kendi takımının `queue` (`PublicAlert[]`) dizisini alır; `/host` yalnızca takım skor/HP özetlerini alır.

3. **`ALERT_ENRICHED` (`RUN_ENRICHER` sonrası aynı takıma yayınlanır):**
```json
{
  "type": "ALERT_ENRICHED",
  "request_id": "req-014",
  "timestamp": "2026-11-25T14:20:18Z",
  "payload": {
    "alert_id": "case_02_tp_kerberoast",
    "team_score": 310,
    "evidence_card": {
      "enricher_id": "ip_reputation",
      "display_name": "IP İtibar",
      "icon_id": "tool-ip-radar",
      "status": "OK",
      "verdict_signal": "MALICIOUS",
      "summary": "185.220.101.44 → AbuseIPDB %98 Kötücül (Bilinen C2 Çıkış Düğümü)",
      "details": { "confidence_score": 98, "country": "DE", "asn": "AS205100" },
      "query_cost_applied": -10,
      "source_mode": "cache",
      "fetched_at_utc": "2026-11-25T14:20:18Z"
    }
  }
}
```

4. **`DECISION_RESULT` (Karar anında oyuncuya anlık puan geri bildirimi — `ground_truth` açıklaması maç sonunda verilir):**
```json
{
  "type": "DECISION_RESULT",
  "request_id": "req-019",
  "timestamp": "2026-11-25T14:20:26Z",
  "payload": {
    "alert_id": "case_02_tp_kerberoast",
    "accepted": true,
    "outcome": "CORRECT_TP",
    "score_delta": 182,
    "hp_delta": 0,
    "new_score": 492,
    "new_hp": 100,
    "new_streak": 3
  }
}
```

5. **`FEED_EVENT` (`/host` ve takım haber bandı):**
```json
{
  "type": "FEED_EVENT",
  "request_id": null,
  "timestamp": "2026-11-25T14:20:26Z",
  "payload": {
    "event_id": "evt_991",
    "severity": "THREAT",
    "team_name": "SİBER KURTLAR",
    "message": "SİBER KURTLAR bir Kerberoasting + C2 saldırısını yanlışlıkla kapattı! (-250 Puan, -40 HP)"
  }
}
```

6. **`MATCH_DEBRIEF` (Maç `ENDED` olduğunda tüm ekranlara gönderilen eğitim kırılımı):**
```json
{
  "type": "MATCH_DEBRIEF",
  "request_id": null,
  "timestamp": "2026-11-25T14:35:00Z",
  "payload": {
    "standings": [
      { "rank": 1, "team_id": "team_alpha", "name": "ALPHA SQUAD", "score": 1450, "hp": 100, "is_breached": false }
    ],
    "cases": [
      {
        "alert_id": "case_02_tp_kerberoast",
        "title": "WKSTN-STAJYER-04 Üzerinde Kerberoasting & C2 Sinyali",
        "ground_truth": "TP",
        "mitre_attack": ["T1558.003", "T1071.001"],
        "debrief_explanation": "...",
        "team_outcomes": { "team_alpha": "CORRECT_TP" }
      }
    ]
  }
}
```

7. **`ERROR` (Standart Hata Kodları):**
- `ALERT_ALREADY_CLAIMED`: Bilet başka bir takım arkadaşı tarafından kilitli.
- `ALERT_NOT_CLAIMED`: Karar/sorgu için önce bilet `CLAIM` edilmelidir.
- `NOT_CLAIM_OWNER`: `SUBMIT_DECISION`, `RELEASE_ALERT` veya `RUN_ENRICHER` yalnızca bileti o an `CLAIM` eden `session_token` tarafından gönderilebilir.
- `ROOM_PAUSED`: Oyun moderatör tarafından duraklatıldığı için aksiyon engellendi.
- `TEAM_BREACHED`: Takımın Breach Meter değeri `0 HP` olduğu için aksiyon kapalı.
- `INVALID_SESSION`: Geçersiz `session_token` veya süresi dolmuş oturum.
- `ENRICHER_UNAVAILABLE`: İstenen araç eklentisi devre dışı veya yanıt vermiyor (`0` maliyet).

---

## 4. Python `BaseEnricher` Soyut Sınıf Sözleşmesi

Backend & Enricher ekibi tüm araçları aşağıdaki kontrata göre yazar (`backend/app/enrichers/base.py`):

```python
from abc import ABC, abstractmethod
from typing import ClassVar, Literal
from pydantic import BaseModel, Field

IocType = Literal["ip", "hash", "domain", "hostname", "username"]


class EvidenceCard(BaseModel):
    enricher_id: str
    display_name: str
    icon_id: str
    status: Literal["OK", "NOT_FOUND", "UNAVAILABLE"] = "OK"
    verdict_signal: Literal["BENIGN", "SUSPICIOUS", "MALICIOUS", "INFO"] = "INFO"
    summary: str
    details: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    query_cost_applied: int = 0
    source_mode: Literal["mock", "cache", "live", "fallback"] = "live"
    fetched_at_utc: str


class BaseEnricher(ABC):
    """Tüm BreachZero enrichment eklentileri bu sınıftan türemelidir."""

    enricher_id: ClassVar[str]               # Örn: "ip_reputation", "whois"
    display_name: ClassVar[str]              # Örn: "IP İtibar", "WHOIS"
    icon_id: ClassVar[str]                   # PNG sprite id veya SVG fallback id
    supported_ioc_types: ClassVar[tuple[IocType, ...]]
    query_cost: ClassVar[int] = -10
    timeout_seconds: ClassVar[float] = 3.0

    @abstractmethod
    async def enrich(
        self,
        ioc_type: IocType,
        ioc_value: str,
        context: dict[str, str],
    ) -> EvidenceCard:
        """IOC değerini sorgular ve normalize edilmiş EvidenceCard döndürür."""
        raise NotImplementedError
```

### `icon_id` Çözümleme ve Crisp-Edges SVG Fallback Kuralı

Frontend araç butonlarını çizerken `EvidenceCard.icon_id` veya enricher manifestindeki `icon_id` değerini şu kurala göre render eder:

1. **Kayıtlı 16×16 PNG Sprite Seti (Tam Sayı Ölçekli `32×32` inside `40×40` `.enrich-icon-box`):**
   - `"tool-ip-radar"` → `assets/sprites/tool-ip-radar.png`
   - `"tool-hash-scanner"` → `assets/sprites/tool-hash-scanner.png`
   - `"tool-cmdb-server"` → `assets/sprites/tool-cmdb-server.png`
2. **Özel PNG Sprite'ı Olmayan Eklentiler İçin Fallback (`whois` vb.):**
   - `icon_id` yukarıdaki PNG havuzunda yer almıyorsa (ör. `"fallback-globe"` veya `"fallback-terminal"` ya da yeni eklenen bir öğrenci eklentisi), frontend kırık görsel göstermek yerine [`.agent/skills/pixel-soc-ui/SKILL.md`](../.agent/skills/pixel-soc-ui/SKILL.md) uyumlu yerleşik **24×24 `shape-rendering="crispEdges"` `<rect>`-only inline SVG** ikonunu render eder (`32×32` görünüm boyutunda, `<path>/<circle>/<ellipse>` yasak).
3. **Hata İzolasyonu:** `enrich(...)` metodu dış ağ hatalarını yukarı fırlatmamalı veya yakalandığında `RoomManager` tarafından `status="UNAVAILABLE"` ve `query_cost_applied=0` kartına dönüştürülmelidir.
