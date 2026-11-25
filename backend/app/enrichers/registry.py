"""Enricher plugin registry with Cache-First + Mock-Fallback + Fault Isolation."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.cache.sqlite_cache import SqliteIocCache
from app.core.scoring import ENRICHER_QUERY_COST
from app.enrichers.base import BaseEnricher
from app.enrichers.ip_reputation import IpReputationEnricher
from app.models.contracts import EvidenceCard, IocType, ScenarioFile

logger = logging.getLogger("breachzero.enrichers")

DEFAULT_ENRICHER_META: dict[str, tuple[str, str]] = {
    "ip_reputation": ("IP İtibar", "tool-ip-radar"),
    "hash_vt": ("Hash / VT", "tool-hash-scanner"),
    "internal_cmdb": ("İç CMDB", "tool-cmdb-server"),
    "whois": ("WHOIS", "fallback-globe"),
}


def pick_ioc_for_enricher(scenario: ScenarioFile, enricher_id: str) -> tuple[IocType, str]:
    ind = scenario.public_alert.indicators
    if enricher_id in ("ip_reputation", "whois") and ind.ips:
        # Prefer non-private external IP when available
        for ip in ind.ips:
            if not ip.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.")):
                return ("ip", ip)
        return ("ip", ind.ips[0])
    if enricher_id == "hash_vt" and ind.hashes:
        return ("hash", ind.hashes[0])
    if enricher_id == "internal_cmdb":
        if ind.usernames:
            return ("username", ind.usernames[0])
        if ind.hostnames:
            return ("hostname", ind.hostnames[0])
    if ind.ips:
        return ("ip", ind.ips[0])
    if ind.hashes:
        return ("hash", ind.hashes[0])
    if ind.domains:
        return ("domain", ind.domains[0])
    return ("hostname", scenario.public_alert.host.hostname)


class EnricherRegistry:
    """Resolves enrichment requests through: Existing -> Scenario Mock -> SQLite Cache -> Live Plugin -> Fallback."""

    def __init__(self, cache: SqliteIocCache) -> None:
        self.cache = cache
        self._plugins: dict[str, BaseEnricher] = {}
        self.register(IpReputationEnricher())

    def register(self, plugin: BaseEnricher) -> None:
        self._plugins[plugin.enricher_id] = plugin

    def get_meta(self, enricher_id: str, scenario: Optional[ScenarioFile] = None) -> tuple[str, str]:
        if scenario and enricher_id in scenario.server_only.mock_enrichment:
            m = scenario.server_only.mock_enrichment[enricher_id]
            return (m.display_name, m.icon_id)
        if enricher_id in self._plugins:
            p = self._plugins[enricher_id]
            return (p.display_name, p.icon_id)
        return DEFAULT_ENRICHER_META.get(enricher_id, (enricher_id.upper(), "fallback-terminal"))

    async def execute(
        self,
        enricher_id: str,
        ioc_type: IocType,
        ioc_value: str,
        scenario: ScenarioFile,
        existing_cards: list[EvidenceCard],
    ) -> tuple[EvidenceCard, int]:
        now = datetime.now(timezone.utc).isoformat()

        # 1. Already fetched on this team's ticket -> 0 cost
        for card in existing_cards:
            if card.enricher_id == enricher_id:
                return card.model_copy(update={"query_cost_applied": 0}), 0

        # 2. Scenario mock_enrichment (offline-safe & deterministic for internal/fictional IOCs)
        mock = scenario.server_only.mock_enrichment.get(enricher_id)
        if mock is not None:
            card = EvidenceCard(
                enricher_id=mock.enricher_id,
                display_name=mock.display_name,
                icon_id=mock.icon_id,
                status=mock.status,
                verdict_signal=mock.verdict_signal,
                summary=mock.summary,
                details=dict(mock.details),
                query_cost_applied=ENRICHER_QUERY_COST if mock.status != "UNAVAILABLE" else 0,
                source_mode="mock",
                fetched_at_utc=now,
            )
            cost = card.query_cost_applied
            if card.status == "OK":
                self.cache.set(enricher_id, ioc_type, ioc_value, card)
            return card, cost

        # 3. SQLite IOC Cache
        cached = self.cache.get(enricher_id, ioc_type, ioc_value)
        if cached is not None:
            card = cached.model_copy(
                update={
                    "source_mode": "cache",
                    "query_cost_applied": ENRICHER_QUERY_COST,
                    "fetched_at_utc": now,
                }
            )
            return card, ENRICHER_QUERY_COST

        # 4. Live BaseEnricher plugin with timeout isolation
        plugin = self._plugins.get(enricher_id)
        display_name, icon_id = self.get_meta(enricher_id, scenario)
        if plugin is not None:
            try:
                card = await asyncio.wait_for(
                    plugin.enrich(ioc_type, ioc_value, {"alert_id": scenario.public_alert.alert_id}),
                    timeout=plugin.timeout_seconds,
                )
                if card.status == "OK":
                    cost = plugin.query_cost
                    card = card.model_copy(update={"query_cost_applied": cost})
                    self.cache.set(enricher_id, ioc_type, ioc_value, card)
                    return card, cost
                return card.model_copy(update={"query_cost_applied": 0}), 0
            except Exception as exc:
                logger.warning("Enricher %s failed cleanly: %s", enricher_id, exc)

        # 5. Graceful degradation -> 0 cost
        fallback_card = EvidenceCard(
            enricher_id=enricher_id,
            display_name=display_name,
            icon_id=icon_id,
            status="UNAVAILABLE",
            verdict_signal="INFO",
            summary=f"{display_name} servisi şu an yanıt vermiyor (puan kesilmedi).",
            details={},
            query_cost_applied=0,
            source_mode="fallback",
            fetched_at_utc=now,
        )
        return fallback_card, 0
