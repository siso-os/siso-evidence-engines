"""One portable SQLite source of truth for three related engine contracts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY, locator TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  source_tier TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS knowledge_items (
  item_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
  claim TEXT NOT NULL, item_type TEXT NOT NULL, evidence_tag TEXT NOT NULL,
  confidence TEXT NOT NULL, quote TEXT NOT NULL, implicit INTEGER NOT NULL,
  status TEXT NOT NULL, grounded_ratio REAL NOT NULL, buckets_json TEXT NOT NULL,
  relations_json TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS principles (
  principle_id TEXT PRIMARY KEY, dedup_key TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  statement TEXT NOT NULL, domain TEXT NOT NULL, source_tier TEXT NOT NULL,
  sources_json TEXT NOT NULL, consensus_count INTEGER NOT NULL, evidence TEXT NOT NULL,
  citation TEXT NOT NULL, gates_json TEXT, score REAL, votes_json TEXT,
  dissent INTEGER DEFAULT 0, status TEXT NOT NULL, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ideas (
  idea_id TEXT PRIMARY KEY, dedup_key TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
  body TEXT NOT NULL, proposer TEXT NOT NULL, source_finding TEXT NOT NULL,
  evidence TEXT NOT NULL, grounding_proof TEXT NOT NULL, target TEXT NOT NULL,
  action TEXT NOT NULL, blast_radius TEXT NOT NULL, reversible INTEGER NOT NULL,
  gates_json TEXT, roi INTEGER, effort INTEGER, risk INTEGER, score REAL,
  votes_json TEXT, dissent INTEGER DEFAULT 0, status TEXT NOT NULL,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_items(source_id);
CREATE INDEX IF NOT EXISTS idx_principles_rank ON principles(status,score DESC);
CREATE INDEX IF NOT EXISTS idx_ideas_rank ON ideas(status,score DESC);
"""


class Store:
    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def save_source(self, row: dict) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO sources(source_id,locator,title,source_tier,content_hash) VALUES (:source_id,:locator,:title,:source_tier,:content_hash)",
            row,
        )

    def save_knowledge(self, row: dict) -> None:
        self.connection.execute(
            """INSERT OR REPLACE INTO knowledge_items
               (item_id,source_id,claim,item_type,evidence_tag,confidence,quote,implicit,status,
                grounded_ratio,buckets_json,relations_json)
               VALUES (:item_id,:source_id,:claim,:item_type,:evidence_tag,:confidence,:quote,:implicit,
                       :status,:grounded_ratio,:buckets_json,:relations_json)""",
            row,
        )
        self.connection.commit()

    def get_principle(self, dedup_key: str):
        return self.connection.execute("SELECT * FROM principles WHERE dedup_key=?", (dedup_key,)).fetchone()

    def save_principle(self, row: dict) -> None:
        self.connection.execute(
            """INSERT INTO principles
               (principle_id,dedup_key,title,statement,domain,source_tier,sources_json,
                consensus_count,evidence,citation,status)
               VALUES (:principle_id,:dedup_key,:title,:statement,:domain,:source_tier,
                       :sources_json,:consensus_count,:evidence,:citation,:status)
               ON CONFLICT(dedup_key) DO UPDATE SET
                 statement=excluded.statement,source_tier=excluded.source_tier,
                 sources_json=excluded.sources_json,consensus_count=excluded.consensus_count,
                 evidence=excluded.evidence,citation=excluded.citation,
                 status=CASE WHEN principles.status='canonical' THEN principles.status ELSE excluded.status END,
                 updated_at=CURRENT_TIMESTAMP""",
            row,
        )
        self.connection.commit()

    def rate_principle(self, principle_id: str, row: dict) -> None:
        self.connection.execute(
            """UPDATE principles SET source_tier=:source_tier,gates_json=:gates_json,
               score=:score,votes_json=:votes_json,dissent=:dissent,status=:status,
               updated_at=CURRENT_TIMESTAMP WHERE principle_id=:principle_id""",
            {**row, "principle_id": principle_id},
        )
        self.connection.commit()

    def get_idea(self, dedup_key: str):
        return self.connection.execute("SELECT * FROM ideas WHERE dedup_key=?", (dedup_key,)).fetchone()

    def save_idea(self, row: dict) -> None:
        self.connection.execute(
            """INSERT INTO ideas
               (idea_id,dedup_key,title,body,proposer,source_finding,evidence,grounding_proof,
                target,action,blast_radius,reversible,status)
               VALUES (:idea_id,:dedup_key,:title,:body,:proposer,:source_finding,:evidence,
                       :grounding_proof,:target,:action,:blast_radius,:reversible,:status)
               ON CONFLICT(dedup_key) DO UPDATE SET body=excluded.body,evidence=excluded.evidence,
                 grounding_proof=excluded.grounding_proof,status=CASE WHEN ideas.status='applied'
                 THEN ideas.status ELSE excluded.status END,updated_at=CURRENT_TIMESTAMP""",
            row,
        )
        self.connection.commit()

    def rate_idea(self, idea_id: str, row: dict) -> None:
        self.connection.execute(
            """UPDATE ideas SET gates_json=:gates_json,roi=:roi,effort=:effort,risk=:risk,
               score=:score,votes_json=:votes_json,dissent=:dissent,
               status=CASE WHEN status='applied' THEN status ELSE :status END,
               updated_at=CURRENT_TIMESTAMP WHERE idea_id=:idea_id""",
            {**row, "idea_id": idea_id},
        )
        self.connection.commit()

    def export(self) -> dict:
        def rows(table: str) -> list[dict]:
            return [dict(row) for row in self.connection.execute(f"SELECT * FROM {table} ORDER BY 1")]
        return {"schema_version": "1.0.0", "sources": rows("sources"),
                "knowledge_items": rows("knowledge_items"), "principles": rows("principles"),
                "ideas": rows("ideas")}

    def export_json(self) -> str:
        return json.dumps(self.export(), indent=2) + "\n"
