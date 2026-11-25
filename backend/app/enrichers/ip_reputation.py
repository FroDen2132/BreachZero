"""IP Reputation enricher plugin template (RFC1918 local check + optional AbuseIPDB)."""

from __future__ import annotations

import ipaddress
import os
from datetime import datetime, timezone

import httpx

from app.enrichers.base import BaseEnricher
from app.models.contracts import EvidenceCard, IocType


class IpReputationEnricher(BaseEnricher):
    enricher_id = "ip_reputation"
    display_name = "IP İtibar"
    icon_id = "tool-ip-radar"
    supported_ioc_types = ("ip",)
    query_cost = -10
    timeout_seconds = 3.0

    async def enrich(
        self,
        ioc_type: IocType,
        ioc_value: str,
        context: dict[str, str],
    ) -> EvidenceCard:
        now = datetime.now(timezone.utc).isoformat()
        try:
            ip_obj = ipaddress.ip_address(ioc_value.strip())
            if ip_obj.is_private:
                return EvidenceCard(
                    enricher_id=self.enricher_id,
                    display_name=self.display_name,
                    icon_id=self.icon_id,
                    status="OK",
                    verdict_signal="INFO",
                    summary=f"{ioc_value} dahili RFC1918 ağ adresidir; dış itibar kaydı gerekmez.",
                    details={"scope": "RFC1918 Private", "abuse_confidence": 0},
                    query_cost_applied=self.query_cost,
                    source_mode="live",
                    fetched_at_utc=now,
                )
        except ValueError:
            pass

        api_key = os.getenv("ABUSEIPDB_API_KEY", "").strip()
        if not api_key:
            return EvidenceCard(
                enricher_id=self.enricher_id,
                display_name=self.display_name,
                icon_id=self.icon_id,
                status="UNAVAILABLE",
                verdict_signal="INFO",
                summary="Canlı API anahtarı tanımlı değil ve senaryo/cache kaydı bulunamadı.",
                details={},
                query_cost_applied=0,
                source_mode="fallback",
                fetched_at_utc=now,
            )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(
                "https://api.abuseipdb.com/api/v2/check",
                headers={"Key": api_key, "Accept": "application/json"},
                params={"ipAddress": ioc_value, "maxAgeInDays": "90"},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

        score = int(data.get("abuseConfidenceScore", 0))
        signal = "MALICIOUS" if score >= 75 else ("SUSPICIOUS" if score >= 25 else "BENIGN")
        return EvidenceCard(
            enricher_id=self.enricher_id,
            display_name=self.display_name,
            icon_id=self.icon_id,
            status="OK",
            verdict_signal=signal,
            summary=f"{ioc_value} → AbuseIPDB %{score} risk skoru ({data.get('countryCode', '??')}).",
            details={
                "abuse_confidence": score,
                "country": data.get("countryCode"),
                "isp": data.get("isp"),
            },
            query_cost_applied=self.query_cost,
            source_mode="live",
            fetched_at_utc=now,
        )
