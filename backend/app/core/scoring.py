"""Anti-exploit scoring and Breach Meter calculations matching docs/GDD.md."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from app.models.contracts import DecisionType

ENRICHER_QUERY_COST = -10
DEFAULT_TP_HP_PENALTY = 30


@dataclass(frozen=True)
class DecisionEval:
    outcome: Literal[
        "CORRECT_TP",
        "CORRECT_FP",
        "FALSE_NEGATIVE",
        "FALSE_POSITIVE",
        "TIMEOUT_TP",
        "TIMEOUT_FP",
    ]
    score_delta: int
    hp_delta: int
    reset_streak: bool


def streak_multiplier(streak: int) -> float:
    if streak >= 5:
        return 1.50
    if streak >= 3:
        return 1.25
    return 1.0


def evaluate_decision(
    ground_truth: DecisionType,
    decision: DecisionType,
    remaining_sla: int,
    sla_seconds: int,
    current_streak: int,
    hp_penalty_on_miss: int,
) -> DecisionEval:
    ratio = max(0.0, min(1.0, remaining_sla / max(1, sla_seconds)))
    mult = streak_multiplier(current_streak)

    if ground_truth == "TP" and decision == "TP":
        base = math.floor(150 * mult)
        speed = math.floor(50 * ratio)
        return DecisionEval("CORRECT_TP", base + speed, 0, False)

    if ground_truth == "FP" and decision == "FP":
        base = math.floor(100 * mult)
        speed = math.floor(40 * ratio)
        return DecisionEval("CORRECT_FP", base + speed, 0, False)

    if ground_truth == "TP" and decision == "FP":
        hp_loss = hp_penalty_on_miss if hp_penalty_on_miss > 0 else DEFAULT_TP_HP_PENALTY
        return DecisionEval("FALSE_NEGATIVE", -250, -hp_loss, True)

    # ground_truth == "FP" and decision == "TP"
    return DecisionEval("FALSE_POSITIVE", -80, 0, True)


def evaluate_timeout(ground_truth: DecisionType, hp_penalty_on_miss: int) -> DecisionEval:
    if ground_truth == "TP":
        hp_loss = hp_penalty_on_miss if hp_penalty_on_miss > 0 else DEFAULT_TP_HP_PENALTY
        return DecisionEval("TIMEOUT_TP", -250, -hp_loss, True)
    return DecisionEval("TIMEOUT_FP", -40, 0, True)
