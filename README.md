# SISO Evidence Engines

Three evidence-gated research engines sharing one small, inspectable core:

- **Knowledge Engine:** sources become grounded knowledge items and relations.
- **Principles Engine:** evidence becomes credibility-ranked engineering guidance.
- **Idea Engine:** findings become adversarially gated, ROI-ranked improvement ideas.

The repository is in the Great Library’s **Research** section. Agents can consume
its outputs, but that does not make Foundry or research infrastructure part of the
Agents operating stack.

## Quick start

```sh
./script/bootstrap
./bin/siso-evidence-engines --db ./evidence.db ingest-knowledge --json fixtures/knowledge.json
./bin/siso-evidence-engines --db ./evidence.db propose-principles --json fixtures/principles.json
./bin/siso-evidence-engines --db ./evidence.db rate-principles --json fixtures/principle-votes.json
./bin/siso-evidence-engines --db ./evidence.db propose-ideas --json fixtures/ideas.json
./bin/siso-evidence-engines --db ./evidence.db rate-ideas --json fixtures/idea-votes.json
./bin/siso-evidence-engines --db ./evidence.db export
```

All inputs are explicit JSON. The first release performs no discovery, scraping,
model call, or network request. That work belongs in Foundry or an external adapter.

## Repository boundary

Git stores source code, schemas, synthetic fixtures, architecture, and provenance.
Raw transcripts, cloned repositories, research reports, provider configuration,
runtime databases, and generated corpora live behind external data locators.

See [`docs/ARCHITECTURE.html`](docs/ARCHITECTURE.html) and
[`MIGRATION-MAP.json`](MIGRATION-MAP.json) for the complete reasoning.

## License

MIT. Source material ingested by a user retains its own rights.
