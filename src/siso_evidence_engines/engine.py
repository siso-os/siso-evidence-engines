"""The public contracts shared by the three engines."""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePath
import re
import statistics

from .grounding import quote_grounded
from .rubrics import IDEA_GATES, PRINCIPLE_GATES, TIER_WEIGHT, idea_score, principle_score
from .store import Store

KNOWLEDGE_TYPES = {"news", "wisdom", "tactic", "prediction", "opinion"}
EVIDENCE_TAGS = {"cited", "opinion", "anecdote"}
CONFIDENCE = {"verified", "reported", "inferred"}


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:24]


def _key(*values: str) -> str:
    return "|".join(re.sub(r"\s+", " ", str(value or "").strip().lower()) for value in values)[:300]


def _sources(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and (item.get("locator") or item.get("url"))]


def ingest_knowledge(store: Store, document: dict) -> dict:
    source = document.get("source") or {}
    locator = str(source.get("locator") or "").strip()
    source_text = str(document.get("source_text") or "")
    if not locator or not source_text:
        raise ValueError("knowledge input requires source.locator and source_text")
    source_id = _hash(locator)
    store.save_source({"source_id": source_id, "locator": locator,
                       "title": str(source.get("title") or locator),
                       "source_tier": str(source.get("tier") or "opinion"),
                       "content_hash": hashlib.sha256(source_text.encode()).hexdigest()})
    accepted, rejected = 0, 0
    for item in document.get("items") or []:
        claim = str(item.get("claim") or "").strip()
        if not claim:
            continue
        implicit = bool(item.get("implicit"))
        quote = str(item.get("quote") or "").strip()
        grounded, ratio = (True, 1.0) if implicit and not quote else quote_grounded(quote, source_text)
        status = "active" if grounded else "rejected-ungrounded"
        accepted += int(grounded)
        rejected += int(not grounded)
        item_type = str(item.get("type") or "opinion")
        evidence_tag = str(item.get("tag") or "opinion")
        confidence = "inferred" if implicit else str(item.get("confidence") or "reported")
        if item_type not in KNOWLEDGE_TYPES or evidence_tag not in EVIDENCE_TAGS or confidence not in CONFIDENCE:
            raise ValueError("invalid knowledge type, evidence tag, or confidence")
        store.save_knowledge({"item_id": _hash(f"{source_id}|{claim}"), "source_id": source_id,
                              "claim": claim, "item_type": item_type, "evidence_tag": evidence_tag,
                              "confidence": confidence, "quote": quote, "implicit": int(implicit),
                              "status": status, "grounded_ratio": ratio,
                              "buckets_json": json.dumps(item.get("buckets") or []),
                              "relations_json": json.dumps(item.get("relations") or [])})
    return {"source_id": source_id, "accepted": accepted, "rejected_ungrounded": rejected}


def propose_principle(store: Store, candidate: dict) -> dict:
    title, statement = str(candidate.get("title") or "").strip(), str(candidate.get("statement") or "").strip()
    if not title or not statement:
        raise ValueError("principle requires title and statement")
    domain = str(candidate.get("domain") or "general").lower()
    dedup_key = _key(domain, title)
    incoming = _sources(candidate.get("sources"))
    existing = store.get_principle(dedup_key)
    prior = json.loads(existing["sources_json"]) if existing else []
    merged: dict[str, dict] = {}
    for source in prior + incoming:
        locator = str(source.get("locator") or source.get("url") or "")
        if locator:
            merged[locator] = source
    evidence = str(candidate.get("evidence") or "").strip()
    status = "proposed" if merged or evidence else "rejected-no-source"
    row = {"principle_id": _hash(dedup_key), "dedup_key": dedup_key, "title": title,
           "statement": statement, "domain": domain,
           "source_tier": str(candidate.get("source_tier") or "opinion").lower(),
           "sources_json": json.dumps(list(merged.values()), sort_keys=True),
           "consensus_count": len(merged), "evidence": evidence,
           "citation": str(candidate.get("citation") or ""), "status": status}
    store.save_principle(row)
    return {"id": row["principle_id"], "status": status, "consensus_count": len(merged)}


def _majority(votes: list[dict], key: str) -> int:
    values = [int(vote.get(key, 0)) for vote in votes]
    return int(bool(values) and statistics.median(values) >= 0.5)


def _median(votes: list[dict], key: str, default: int = 3) -> int:
    values = [int(vote[key]) for vote in votes if vote.get(key) is not None]
    return int(round(statistics.median(values))) if values else default


def rate_principle(store: Store, entry: dict, threshold: float = 6.0) -> dict:
    votes = entry.get("votes") or []
    if not votes:
        raise ValueError("principle rating requires votes")
    tiers = [vote.get("source_tier") for vote in votes if vote.get("source_tier")]
    tier = max(set(tiers), key=lambda value: (tiers.count(value), TIER_WEIGHT.get(value, 0))) if tiers else "opinion"
    rated = {gate: _majority(votes, gate) for gate in PRINCIPLE_GATES}
    rated.update({"source_tier": tier, "consensus_count": int(entry.get("consensus_count") or 1)})
    score = principle_score(rated)
    dissent = int(any(len({int(vote.get(gate, 0)) for vote in votes}) > 1 for gate in PRINCIPLE_GATES))
    status = "canonical" if score >= threshold else "rated"
    store.rate_principle(str(entry["id"]), {"source_tier": tier,
        "gates_json": json.dumps({gate: rated[gate] for gate in PRINCIPLE_GATES}),
        "score": score, "votes_json": json.dumps(votes), "dissent": dissent, "status": status})
    return {"id": entry["id"], "score": score, "status": status, "dissent": dissent}


def propose_idea(store: Store, candidate: dict) -> dict:
    title, body = str(candidate.get("title") or "").strip(), str(candidate.get("body") or "").strip()
    if not title or not body:
        raise ValueError("idea requires title and body")
    target = str(candidate.get("target") or "strategy")
    if PurePath(target).is_absolute():
        raise ValueError("idea target must be a logical locator, not an absolute machine path")
    dedup_key = _key(target, title)
    evidence = str(candidate.get("evidence") or "").strip()
    status = "proposed" if evidence else "rejected-no-evidence"
    row = {"idea_id": _hash(dedup_key), "dedup_key": dedup_key, "title": title, "body": body,
           "proposer": str(candidate.get("proposer") or "unknown"),
           "source_finding": str(candidate.get("source_finding") or ""), "evidence": evidence,
           "grounding_proof": str(candidate.get("grounding_proof") or ""), "target": target,
           "action": str(candidate.get("action") or "strategy"),
           "blast_radius": str(candidate.get("blast_radius") or "safe-text"),
           "reversible": int(bool(candidate.get("reversible", True))), "status": status}
    store.save_idea(row)
    return {"id": row["idea_id"], "status": status}


def rate_idea(store: Store, entry: dict, threshold: float = 6.0) -> dict:
    votes = entry.get("votes") or []
    if not votes:
        raise ValueError("idea rating requires votes")
    rated = {gate: _majority(votes, gate) for gate in IDEA_GATES}
    rated.update({"roi": _median(votes, "roi"), "effort": _median(votes, "effort"),
                  "risk": _median(votes, "risk")})
    score = idea_score(rated)
    dissent = int(any(len({int(vote.get(gate, 0)) for vote in votes}) > 1 for gate in IDEA_GATES))
    status = "queued" if score >= threshold else "rated"
    store.rate_idea(str(entry["id"]), {"gates_json": json.dumps({gate: rated[gate] for gate in IDEA_GATES}),
        "roi": rated["roi"], "effort": rated["effort"], "risk": rated["risk"],
        "score": score, "votes_json": json.dumps(votes), "dissent": dissent, "status": status})
    return {"id": entry["id"], "score": score, "status": status, "dissent": dissent}
