"""Automatic scenario discovery with fault-tolerant Pydantic validation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from app.models.contracts import ScenarioFile, ScenarioSummary

logger = logging.getLogger("breachzero.scenarios")


class ScenarioLoader:
    """Loads valid JSON scenarios from scenarios/ and safely skips invalid files."""

    def __init__(self, scenarios_dir: Path) -> None:
        self.scenarios_dir = scenarios_dir
        self._scenarios: dict[str, ScenarioFile] = {}
        self.invalid_files: list[str] = []
        self.reload()

    def reload(self) -> None:
        self._scenarios.clear()
        self.invalid_files.clear()
        if not self.scenarios_dir.exists():
            logger.warning("Scenarios directory does not exist: %s", self.scenarios_dir)
            return

        for path in sorted(self.scenarios_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                scenario = ScenarioFile.model_validate(raw)
                self._scenarios[scenario.public_alert.alert_id] = scenario
                logger.info("Loaded scenario %s (%s)", scenario.public_alert.alert_id, path.name)
            except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
                self.invalid_files.append(path.name)
                logger.error("Skipping invalid scenario %s: %s", path.name, exc)

    def get(self, alert_id: str) -> Optional[ScenarioFile]:
        return self._scenarios.get(alert_id)

    def list_all(self) -> list[ScenarioFile]:
        return list(self._scenarios.values())

    def list_summaries(self) -> list[ScenarioSummary]:
        return [
            ScenarioSummary(
                alert_id=s.public_alert.alert_id,
                incident_code=s.public_alert.incident_code,
                title=s.public_alert.title,
                severity=s.public_alert.severity,
                difficulty=s.meta.difficulty,
                estimated_wave=s.meta.estimated_wave,
                sla_seconds=s.public_alert.sla_seconds,
                available_enrichers=list(s.public_alert.available_enrichers),
            )
            for s in self._scenarios.values()
        ]
