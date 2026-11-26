"""WHOIS enricher plugin: free, key-less RDAP (rdap.org) lookups for IP and domain IOCs."""

from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.enrichers.base import BaseEnricher
from app.models.contracts import EvidenceCard, IocType

RDAP_BASE_URL = "https://rdap.org"
YOUNG_DOMAIN_DAYS = 30


def _parse_event_date(events: list[dict[str, Any]], action: str) -> Optional[datetime]:
    for event in events:
        if event.get("eventAction") == action and event.get("eventDate"):
            raw = str(event["eventDate"]).replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return None
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _registrar_name(entities: list[dict[str, Any]]) -> Optional[str]:
    """Extract the registrar's 'fn' value from the RDAP vCard array, if present."""
    for entity in entities:
        if "registrar" not in entity.get("roles", []):
            continue
        vcard = entity.get("vcardArray") or []
        if len(vcard) > 1:
            for field in vcard[1]:
                if field and field[0] == "fn" and len(field) > 3:
                    return str(field[3])
    return None


class WhoisEnricher(BaseEnricher):
    enricher_id = "whois"
    display_name = "WHOIS"
    icon_id = "fallback-globe"
    supported_ioc_types = ("ip", "domain")
    query_cost = -10
    timeout_seconds = 3.0

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        # `transport` is injectable so tests can mock rdap.org without network access.
        self._transport = transport

    def _card(self, **kwargs: Any) -> EvidenceCard:
        return EvidenceCard(
            enricher_id=self.enricher_id,
            display_name=self.display_name,
            icon_id=self.icon_id,
            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )

    def _unavailable(self, summary: str) -> EvidenceCard:
        return self._card(
            status="UNAVAILABLE",
            verdict_signal="INFO",
            summary=summary,
            details={},
            query_cost_applied=0,
            source_mode="fallback",
        )

    async def enrich(
        self,
        ioc_type: IocType,
        ioc_value: str,
        context: dict[str, str],
    ) -> EvidenceCard:
        value = ioc_value.strip()

        if ioc_type == "ip":
            try:
                ip_obj = ipaddress.ip_address(value)
            except ValueError:
                return self._unavailable(f"'{value}' geçerli bir IP adresi değil; WHOIS sorgusu yapılmadı.")
            # Never leak internal addresses to an external RDAP server.
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local:
                return self._card(
                    status="OK",
                    verdict_signal="INFO",
                    summary=f"{value} dahili RFC1918 ağ adresidir; dış WHOIS kaydı yoktur.",
                    details={"scope": "RFC1918 Private"},
                    query_cost_applied=self.query_cost,
                    source_mode="live",
                )
            url = f"{RDAP_BASE_URL}/ip/{value}"
        elif ioc_type == "domain":
            url = f"{RDAP_BASE_URL}/domain/{value.lower().rstrip('.')}"
        else:
            return self._unavailable(f"WHOIS '{ioc_type}' tipini desteklemiyor.")

        try:
            # rdap.org answers with a 302 redirect to the responsible RIR/TLD server.
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout_seconds,
                transport=self._transport,
                headers={"Accept": "application/rdap+json, application/json"},
            ) as client:
                resp = await client.get(url)
            if resp.status_code == 404:
                return self._card(
                    status="NOT_FOUND",
                    verdict_signal="INFO",
                    summary=f"{value} için RDAP kaydı bulunamadı.",
                    details={},
                    query_cost_applied=self.query_cost,
                    source_mode="live",
                )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, ValueError):
            return self._unavailable("WHOIS (RDAP) servisi şu an yanıt vermiyor (puan kesilmedi).")

        return self._build_card(ioc_type, value, data)

    def _build_card(self, ioc_type: IocType, value: str, data: dict[str, Any]) -> EvidenceCard:
        events = data.get("events") or []
        registered = _parse_event_date(events, "registration")
        name = data.get("name") or data.get("ldhName")
        country = data.get("country")
        handle = data.get("handle")
        registrar = _registrar_name(data.get("entities") or [])

        age_days: Optional[int] = None
        if registered is not None:
            age_days = max((datetime.now(timezone.utc) - registered).days, 0)

        details: dict[str, str | int | float | bool | None] = {
            "name": name,
            "country": country,
            "handle": handle,
            "registrar": registrar,
            "registered": registered.date().isoformat() if registered else None,
            "age_days": age_days,
        }

        signal = "INFO"
        if ioc_type == "domain":
            parts = [f"{value} alan adı"]
            if registered is not None:
                parts.append(f"{registered.date().isoformat()} tarihinde kaydedilmiş ({age_days} gün önce)")
            if registrar:
                parts.append(f"kayıt kuruluşu: {registrar}")
            if age_days is not None and age_days < YOUNG_DOMAIN_DAYS:
                signal = "SUSPICIOUS"
                parts.append("çok yeni kayıt, phishing/C2 riski")
        else:
            parts = [f"{value} → {name or 'bilinmeyen kurum'}"]
            if handle:
                parts.append(f"handle: {handle}")
            if country:
                parts.append(f"ülke: {country}")
            if registered is not None:
                parts.append(f"kayıt: {registered.date().isoformat()}")

        return self._card(
            status="OK",
            verdict_signal=signal,
            summary=", ".join(parts) + ".",
            details=details,
            query_cost_applied=self.query_cost,
            source_mode="live",
        )
