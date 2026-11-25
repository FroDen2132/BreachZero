"""BaseEnricher abstract interface matching docs/CONTRACTS.md."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from app.models.contracts import EvidenceCard, IocType


class BaseEnricher(ABC):
    """All BreachZero enrichment plugins must inherit from this class."""

    enricher_id: ClassVar[str]
    display_name: ClassVar[str]
    icon_id: ClassVar[str]
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
        """Query IOC and return a normalized EvidenceCard."""
        raise NotImplementedError
