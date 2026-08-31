"""Stage 6, trust level T0: the deterministic delivery backbone.

`api/README.md` fixes the trust levels: `T0` deterministic only, `T1` an LLM
verbalising a deterministic rationale, `T2` LLM suggestions beyond the verdict.
Everything served here is `T0`, and every response says so in its `provenance`
block along with the metamodel, catalogue and threshold-set versions that
produced it. Constraint 4 of `docs/01-pipeline.md` requires that stamp on every
output record; putting it in the envelope means no endpoint can forget it.

What is deliberately *not* here:

- No assessment, verdict or risk score. Those come from stage 4, which does not
  exist yet, and an API that invented one would be exactly the unfalsifiable
  output the SLR criticises. `/services/{name}` returns
  `assessment: {"available": false, ...}` with the reason, which is also the
  seam stage 4 plugs into.
- No LLM. The switch that disables it entirely is required to leave a working
  system behind (`api/README.md`), so the fallback is the whole product at this
  stage, not a degraded mode.
- No write endpoints. The store is read-only by construction: artifacts are
  produced by `run_pipeline.py` and served verbatim.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from aam4j_metrics.catalogue import CATALOGUE_VERSION, METRICS
from aam4j_metrics.thresholds import Thresholds
from aam4j_model.model import METAMODEL_VERSION

from .store import TRUST_LEVEL, NotFound, ProfileStore, SnapshotRef

ROOT = os.environ.get("AAM4J_ROOT") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(
    title="AAM4J delivery API",
    version="0.1.0",
    summary="Architecture-aware metric profiles, served at trust level T0 (deterministic only).",
)
store = ProfileStore(ROOT)


@app.exception_handler(NotFound)
def _not_found(_request, exc: NotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(exc)})


def provenance(ref: SnapshotRef | None = None) -> dict:
    thresholds = Thresholds.load()
    block = {
        "trust_level": TRUST_LEVEL,
        "llm": {"enabled": False, "reason": "T0: no LLM layer is wired at this stage"},
        "metamodel_version": METAMODEL_VERSION,
        "catalogue_version": CATALOGUE_VERSION,
        "threshold_set_version": thresholds.version,
    }
    if ref is not None:
        block["system"] = ref.system
        block["snapshot"] = ref.commit
    return block


@app.get("/health")
def health() -> dict:
    """Liveness, plus which subject systems actually have artifacts to serve."""
    return {
        "status": "ok",
        "provenance": provenance(),
        "systems": [
            {"system": ref.system, "snapshot": ref.commit, "artifacts": store.has_artifacts(ref)}
            for ref in store.pinned()
        ],
    }


@app.get("/catalogue")
def catalogue() -> dict:
    """What this deployment can compute, and what it cannot determine, and why.

    A consumer that only reads values would silently treat every undetermined
    metric as absent. Publishing the threshold set alongside the metric list is
    what lets a client tell "this smell did not fire" from "this smell could
    not be evaluated".
    """
    thresholds = Thresholds.load()
    return {
        "provenance": provenance(),
        "metrics": sorted(METRICS),
        "thresholds": {
            "version": thresholds.version,
            "method": thresholds.method,
            "derived_from": [{"system": s, "snapshot": c} for s, c in thresholds.derived_from],
            "by_smell": {
                smell: {
                    metric: {"value": entry.value, "determined": entry.determined, "reason": entry.reason}
                    for metric, entry in entries.items()
                }
                for smell, entries in thresholds.by_smell.items()
            },
        },
    }


@app.get("/systems")
def systems() -> dict:
    return {
        "provenance": provenance(),
        "systems": [
            {
                "system": ref.system,
                "snapshot": ref.commit,
                "branch": ref.branch,
                "url": ref.url,
                "artifacts": store.has_artifacts(ref),
            }
            for ref in store.pinned()
        ],
    }


@app.get("/systems/{system}/graph")
def graph(system: str, snapshot: str | None = None) -> dict:
    """`G` as the metric layer saw it, with the DD-002 role of every service.

    Roles are served with the nodes rather than filtered away, because a figure
    drawn from this endpoint has to be able to say which services it excluded.
    """
    ref = store.resolve(system, snapshot)
    model = store.model(ref)
    return {
        "provenance": provenance(ref),
        "services": [
            {
                "id": service["id"],
                "name": service["name"],
                "role": service["role"],
                "role_rule": service["role_rule"],
                "technology": service["technology"],
            }
            for service in model["services"]
        ],
        "dependencies": [
            {
                "id": dependency["id"],
                "source": dependency["source"],
                "target": dependency["target"],
                "kind": dependency["kind"],
                "provenance": dependency["provenance"],
                "mechanisms": dependency["mechanisms"],
            }
            for dependency in model["dependencies"]
        ],
    }


@app.get("/systems/{system}/profile")
def profile(
    system: str,
    snapshot: str | None = None,
    metric: list[str] | None = Query(default=None),
    element: str | None = None,
    determined: bool | None = None,
) -> dict:
    """The metric profile, in the long format of the 3->4 data contract."""
    ref = store.resolve(system, snapshot)
    rows = store.profile(ref)
    if metric:
        wanted = set(metric)
        unknown = wanted - set(METRICS)
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"unknown metric(s): {', '.join(sorted(unknown))}. See GET /catalogue",
            )
        rows = [row for row in rows if row["metric"] in wanted]
    if element:
        rows = [row for row in rows if row["element_id"] == element or row["element_id"].endswith("/" + element)]
    if determined is not None:
        rows = [row for row in rows if row["determined"] is determined]
    return {
        "provenance": provenance(ref),
        "count": len(rows),
        "undetermined": sum(1 for row in rows if not row["determined"]),
        "rows": rows,
    }


@app.get("/systems/{system}/gaps")
def gaps(system: str, snapshot: str | None = None) -> dict:
    """Everything the model could not determine from this snapshot.

    A first-class endpoint rather than a footnote: the evidence gaps are the
    honest half of the output, and a CI dashboard that shows metrics without
    them would report a partial extraction as a clean system.
    """
    ref = store.resolve(system, snapshot)
    model = store.model(ref)
    return {"provenance": provenance(ref), "gaps": model.get("evidence_gaps", [])}


@app.get("/systems/{system}/services/{name}")
def service(system: str, name: str, snapshot: str | None = None) -> dict:
    """Everything known about one service: the first layer of progressive disclosure.

    `api/README.md` specifies three layers (one-line verdict, metric-level
    rationale, full counterfactual). Only the middle one is computable today, so
    the verdict is served as explicitly unavailable with its reason, and the
    counterfactual is absent. Shipping the layer that exists, and naming the
    ones that do not, is the difference between a skeleton and a mock-up.
    """
    ref = store.resolve(system, snapshot)
    model = store.model(ref)
    matches = [s for s in model["services"] if s["name"] == name or s["id"] == name]
    if not matches:
        raise NotFound(
            f"{system!r} has no service {name!r}; see GET /systems/{system}/graph"
        )
    record = matches[0]
    element_id = record["id"]

    metrics = [row for row in store.profile(ref) if row["element_id"] == element_id]
    inbound = [d for d in model["dependencies"] if d["target"] == element_id]
    outbound = [d for d in model["dependencies"] if d["source"] == element_id]
    gaps_here = [g for g in model.get("evidence_gaps", []) if g["subject"] in (element_id, record["name"])]
    entities = [e for e in model.get("entities", []) if e["service"] == element_id]

    return {
        "provenance": provenance(ref),
        "service": record,
        "assessment": {
            "available": False,
            "reason": (
                "no quality model is deployed: stage 4 (models/) has no trained model for this "
                "catalogue version, and T0 does not permit an assessment from any other source"
            ),
        },
        "metrics": metrics,
        "undetermined_metrics": [row["metric"] for row in metrics if not row["determined"]],
        "dependencies": {
            "inbound": [{"from": d["source"], "kind": d["kind"], "provenance": d["provenance"]} for d in inbound],
            "outbound": [{"to": d["target"], "kind": d["kind"], "provenance": d["provenance"]} for d in outbound],
        },
        "entities": [{"id": e["id"], "java_type": e["java_type"], "table": e["table"]} for e in entities],
        "evidence_gaps": gaps_here,
    }
