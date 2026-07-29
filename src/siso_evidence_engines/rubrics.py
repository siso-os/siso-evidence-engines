"""Deterministic gates and scores. Model output is input, never arithmetic truth."""

from __future__ import annotations

PRINCIPLE_GATES = ("test_grounded", "test_actionable", "test_general", "test_not_contradicted")
IDEA_GATES = ("test_grounded", "test_novel", "test_right_layer", "test_not_gameable")
TIER_WEIGHT = {"research": 4, "standard": 3, "practitioner": 2, "opinion": 1}


def principle_score(row: dict) -> float:
    if any(not row.get(gate) for gate in PRINCIPLE_GATES):
        return 0.0
    tier = TIER_WEIGHT.get(str(row.get("source_tier") or "opinion").lower(), 1)
    consensus = min(int(row.get("consensus_count") or 1), 5)
    return round(max(0.0, min(10.0, tier * 1.6 + (consensus - 1) * 0.75)), 2)


def idea_score(row: dict) -> float:
    if any(not row.get(gate) for gate in IDEA_GATES):
        return 0.0
    roi = int(row.get("roi") or 1)
    effort = int(row.get("effort") or 3)
    risk = int(row.get("risk") or 3)
    return round(max(0.0, min(10.0, roi * 2 - (effort - 1) * 0.6 - (risk - 1) * 0.8)), 2)
