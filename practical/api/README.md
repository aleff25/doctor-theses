# api/ — Obj. 5 / T6 · gap G4 · RQ4

The delivery backbone: REST API, exports, developer-facing feedback, and the optional LLM layer.

**In:** structured rationales from `models/`
**Out:** JSON/CSV/time-series exports, CI dashboard entries, IDE-consumable annotations

Per the proposal (§5.3.5), the API/export backbone is prioritised over an IDE plugin. IDE
integration is explored only if it demonstrably supports the evaluation.

## Feedback presentation (SLR §5.3)

Three layers of progressive disclosure: one-line verdict → metric-level rationale → full
counterfactual with suggested refactoring. Every explanation keeps navigable links back to the
metamodel elements involved.

## LLM layer — controls are mandatory (SLR §5.4)

Role: **bounded consultant and explainer**. It never originates an assessment; it operates strictly
downstream of the deterministic pipeline.

Trust levels: `T0` deterministic only · `T1` LLM verbalises a deterministic rationale · `T2` LLM
suggestions beyond the verdict, always labelled unverified.

Three checks before any output reaches a developer:
1. **Grounding** — every claim references metrics or model elements present in the input context
2. **Consistency** — regenerating must not change the substantive recommendation
3. **Contradiction** — must not conflict with the deterministic verdict

Also required: configurable verbosity, temperature (low by default; high only in a separated
exploratory what-if mode), audience profile, and a switch that disables the LLM entirely with
template-based explanation as a working fallback. All configuration is logged with each output.

Security: prefer locally hosted / privately deployed models — source code and telemetry must not
leave the organisation. Test prompt-injection resistance: code comments, config values and log
messages all become model context, and all are attack vectors.

Every LLM version change must pass the pattern regression suite (`docs/04-pattern-catalogue.md`)
before adoption.

---

## Implemented today: trust level T0

`aam4j_api/` is a FastAPI application that serves what the pipeline wrote under `data/`, and
nothing else. Run it from the repository root:

```bash
./.venv/bin/pip install -e '.[api,dev]'
./.venv/bin/python -m uvicorn aam4j_api.app:app --app-dir api --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

| Endpoint | Returns |
|---|---|
| `GET /health` | liveness, and which pinned systems actually have artifacts |
| `GET /catalogue` | the metric IDs this deployment can compute, plus the threshold set and what it refused to derive |
| `GET /systems` | the pinned subject systems |
| `GET /systems/{system}/graph` | services with their DD-002 role and role rule, and the dependency edges |
| `GET /systems/{system}/profile` | the metric profile, filterable by `metric`, `element`, `determined` |
| `GET /systems/{system}/gaps` | everything the model could not determine from that snapshot |
| `GET /systems/{system}/services/{name}` | one service: metrics, neighbours, entities, gaps, and an explicitly unavailable assessment |

Four properties are load-bearing and are covered by `tests/test_api_t0.py`:

1. **Every response is stamped.** Trust level, LLM state, metamodel version, catalogue version and
   threshold-set version travel in a `provenance` block on every payload, per constraint 4 of
   `docs/01-pipeline.md`.
2. **Undetermined is never zero.** A metric that could not be computed is served as `value: null`
   with its note. `GOD` is undetermined on every service today (see DD-006), and the API says so
   rather than reporting "no god services found".
3. **No assessment without a model.** `assessment.available` is `false` with a reason until stage
   ④ ships one. See DD-007.
4. **Only pinned snapshots are servable.** A directory that appears under `data/` without a
   matching entry in `subjects.lock.json` cannot be served as the subject system.

The LLM layer described above remains unimplemented, which is the intended order: the T0 fallback
has to be a working product before anything verbalises it.
