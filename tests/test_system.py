from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from siso_evidence_engines.engine import ingest_knowledge, propose_idea, propose_principle, rate_idea, rate_principle
from siso_evidence_engines.store import Store

ROOT = Path(__file__).resolve().parents[1]


class EvidenceEnginesSystemTest(unittest.TestCase):
    def test_three_engines_share_evidence_without_sharing_corpora(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "evidence.db")
            try:
                knowledge = ingest_knowledge(store, json.loads((ROOT / "fixtures/knowledge.json").read_text()))
                self.assertEqual(3, knowledge["accepted"])
                principles = json.loads((ROOT / "fixtures/principles.json").read_text())
                accepted = propose_principle(store, principles[0])
                rejected = propose_principle(store, principles[1])
                self.assertEqual("proposed", accepted["status"])
                self.assertEqual("rejected-no-source", rejected["status"])
                principle_rating = rate_principle(store, {"id": accepted["id"], "consensus_count": 1,
                    "votes": [{"test_grounded":1,"test_actionable":1,"test_general":1,"test_not_contradicted":1,"source_tier":"research"}] * 3})
                self.assertEqual("canonical", principle_rating["status"])
                self.assertEqual(6.4, principle_rating["score"])
                ideas = json.loads((ROOT / "fixtures/ideas.json").read_text())
                queued = propose_idea(store, ideas[0])
                unbacked = propose_idea(store, ideas[1])
                self.assertEqual("rejected-no-evidence", unbacked["status"])
                idea_rating = rate_idea(store, {"id": queued["id"], "votes": [
                    {"test_grounded":1,"test_novel":1,"test_right_layer":1,"test_not_gameable":1,"roi":5,"effort":1,"risk":1},
                    {"test_grounded":1,"test_novel":1,"test_right_layer":1,"test_not_gameable":1,"roi":5,"effort":2,"risk":1},
                    {"test_grounded":1,"test_novel":1,"test_right_layer":1,"test_not_gameable":1,"roi":4,"effort":1,"risk":1}]})
                self.assertEqual("queued", idea_rating["status"])
                exported = store.export()
                self.assertEqual(3, len(exported["knowledge_items"]))
                self.assertEqual(2, len(exported["principles"]))
                self.assertEqual(2, len(exported["ideas"]))
                serialized = json.dumps(exported)
                self.assertNotIn("source_text", serialized)
                self.assertNotIn("The observed teams", serialized)
            finally:
                store.close()

    def test_ungrounded_quote_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / "evidence.db")
            try:
                result = ingest_knowledge(store, {"source":{"locator":"fixture://x"},
                    "source_text":"Only the source may ground a quotation.",
                    "items":[{"claim":"Fabricated","type":"wisdom","tag":"cited",
                              "confidence":"verified","quote":"words that do not occur"}]})
                self.assertEqual(1, result["rejected_ungrounded"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
