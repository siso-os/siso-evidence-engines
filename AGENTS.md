# SISO Evidence Engines

## Purpose

Turn explicit sources into traceable knowledge items, engineering principles,
and ranked improvement ideas. The reusable engines live here; corpora do not.

## First reads

- Product and commands: `README.md`
- Engine boundaries: `docs/ARCHITECTURE.html`
- Machine inventory: `registry/engines.json`
- Warehouse dispositions: `MIGRATION-MAP.json`
- Verification: `script/test`

## Invariants

- No crawler, provider credential, machine scheduler, corpus, or generated research state.
- Every accepted knowledge item has a source and grounded quote, unless explicitly marked inferred.
- Every rateable principle has evidence or an independently identifiable source.
- Every rateable idea has concrete evidence.
- Models may propose votes; deterministic code owns gates, jury aggregation, scores, and state.
- This package records ideas and approval state. It never edits target code.

## Operations

```sh
./script/bootstrap
./script/test
./bin/siso-evidence-engines --help
```
