# metrics/ — Obj. 2 / T3 · gap G2 · RQ2

Formal metric definitions over the metamodel, and the engine that evaluates them.

**In:** `.xmi` model instance
**Out:** metric profile — long format `(system, snapshot, element_id, element_kind, metric, value)`

Definitions live in `docs/03-metric-catalogue.md`; this directory holds their OCL and the
reference implementations. Metrics are OCL over the metamodel rather than code in the extraction
pipeline, so the catalogue can be extended without touching the extractor (proposal §5.3.2).

## Rules

- A metric is not catalogued until it has all six required items listed in the catalogue doc —
  including a unit test against a hand-built model whose correct value is known.
- Thresholds (the `θ` values in the smell predicates) are versioned catalogue data, not constants
  in code, and their derivation method is reported in the thesis.
- The catalogue is a versioned artifact; its version is stamped into every metric profile.
