"""Pre-warm SQLite IOC cache from scenario files before a live campus event."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.cache.sqlite_cache import SqliteIocCache
from app.core.scenario_loader import ScenarioLoader
from app.enrichers.registry import EnricherRegistry, pick_ioc_for_enricher
from app.models.contracts import EvidenceCard


async def prewarm_scenarios(scenarios_dir: Path, db_path: Path) -> int:
    loader = ScenarioLoader(scenarios_dir)
    cache = SqliteIocCache(db_path)
    registry = EnricherRegistry(cache=cache)
    warmed = 0

    for scenario in loader.list_all():
        for enricher_id in scenario.public_alert.available_enrichers:
            ioc_type, ioc_value = pick_ioc_for_enricher(scenario, enricher_id)
            mock = scenario.server_only.mock_enrichment.get(enricher_id)
            if mock:
                card = EvidenceCard(
                    enricher_id=mock.enricher_id,
                    display_name=mock.display_name,
                    icon_id=mock.icon_id,
                    status=mock.status,
                    verdict_signal=mock.verdict_signal,
                    summary=mock.summary,
                    details=mock.details,
                    query_cost_applied=0,
                    source_mode="cache",
                    fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                )
                cache.set(enricher_id, ioc_type, ioc_value, card)
                warmed += 1
            else:
                card, _ = await registry.execute(
                    enricher_id=enricher_id,
                    ioc_type=ioc_type,
                    ioc_value=ioc_value,
                    scenario=scenario,
                    existing_cards=[],
                )
                if card.status == "OK":
                    warmed += 1
    return warmed


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-warm BreachZero SQLite IOC cache.")
    parser.add_argument("--scenarios", type=Path, default=Path("../scenarios"))
    parser.add_argument("--db", type=Path, default=Path("data/ioc_cache.db"))
    args = parser.parse_args()

    count = asyncio.run(prewarm_scenarios(args.scenarios, args.db))
    print(f"[PREWARM] {count} IOC kaydı önbelleğe alındı -> {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
