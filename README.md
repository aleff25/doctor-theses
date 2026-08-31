# AAM4J — Architecture-Aware Metrics for Java

Practical (artifact) track of the PhD *Architecture-Aware Software Metrics for AI-Supported
Quality Assessment in Java-Based Distributed Systems* — Aleff Rodrigues Mendes de Oliveira,
Iscte-IUL. Supervisors: José Vicente Pereira dos Reis, Vítor Manuel Bastos.

`AAM4J` is a working name; change it freely before the first publication.

## What this repository is

The SLR (`../SLR_Architecture_Aware_Metrics_v5.docx`) established four gaps (G1–G4) and mapped
each to a thesis objective. This repository is the software that closes them. Every directory
here exists because the SLR says something is missing from the literature — nothing is here
"because a project usually has one".

| Dir | Objective | Gap closed | One-line purpose |
|---|---|---|---|
| `metamodel/` | Obj. 1 / T2 | G1 | Technology-agnostic architectural metamodel fusing static + config + runtime evidence |
| `metrics/` | Obj. 2 / T3 | G2 | Formal (OCL) catalogue of architecture-aware metrics over that metamodel |
| `extractor/` | Obj. 3 / T4 | — | Builds metamodel instances from Java code, configuration and deployment descriptors |
| `models/` | Obj. 4 / T5 | G3 | Hybrid metric+AI models, interpretable-by-design, and the supervision they need |
| `api/` | Obj. 5 / T6 | G4 | REST/export backbone + developer-facing feedback (trust level T0) |
| `subjects/` | all | — | The three subject systems the whole chain is evaluated on |
| `data/` | Obj. 4–5 | — | Extracted models, metric profiles, labels, train/test splits |

The dependency chain is strict and matches SLR §5.2: **G1 → G2 → G3 → G4**. The metamodel is a
precondition for the metric catalogue, which supplies the interpretable features for the models,
which produce the feedback that gets evaluated with developers. Do not start a downstream stage
before its upstream stage has a frozen version.

## Subject systems

Three Java microservice systems, chosen to span scale and to each contribute a *different kind of
label* (see `docs/02-subject-systems.md` for the full rationale):

| System | Services | Role in the thesis |
|---|---|---|
| Spring PetClinic Microservices | 8 modules (vets, visits/appointments, customers, gateway, config, discovery, admin, genai) | Reference/control system; full Prometheus+Grafana+Zipkin stack; pattern ground truth |
| FudanSELab Train Ticket | 33 `ts-*` modules (`refactor/v2`) | Scale; **label source unresolved — see `docs/05`** |
| Descartes TeaStore | 5 services + registry | Performance/energy labels; built for model extraction, so it validates RQ1 |

Fetch them with `./subjects/fetch_subjects.sh` (clones + writes `subjects.lock.json` recording the
exact commit of each, for reproducibility).

## Running it locally

Stages ①–③ have no third-party dependencies at all: a reviewer with a Python install and the
subject clones can reproduce every stored artifact. The API and the learning baseline are optional
extras, declared in `pyproject.toml`.

```bash
python -m venv .venv
./.venv/bin/pip install -e '.[api,learn,dev]'   # or omit extras for the pipeline alone

./subjects/fetch_subjects.sh                    # clones the three systems at their pinned commits

# (1) extraction -> (2) model -> (3) metric profile, per system
./.venv/bin/python run_pipeline.py --system petclinic
./.venv/bin/python run_pipeline.py --system teastore
./.venv/bin/python run_pipeline.py --system trainticket

# group-E smell thresholds, derived from the three distributions (never hardcoded)
./.venv/bin/python metrics/derive_thresholds.py

# (4) supervision: architectural mutants, labelled by construction, and the joined datasets
./.venv/bin/python models/build_dataset.py
./.venv/bin/python models/train_baseline.py --task oversized-service

# (6) delivery: the deterministic API, http://127.0.0.1:8000/docs
./.venv/bin/python -m uvicorn aam4j_api.app:app --app-dir api --reload

./.venv/bin/pytest                              # the whole suite
```

`pytest` must be run from the repository root: `pyproject.toml` confines collection to `tests/`,
because `subjects/` contains three full clones, two of which ship Python test suites of their own.

## Current status

Stages ①–③ run end to end on all three subject systems, stage ④ has synthetic supervision and a
first interpretable baseline, and stage ⑥ serves the results deterministically. Stage ⑤ (structured
rationale as its own artifact) is still folded into the attribution records the baseline emits.

| Stage | State |
|---|---|
| ① extraction | Regex static analyser behind the `StaticAnalyser` seam. **Weak on Train Ticket and TeaStore**: it recovers 1 and 0 declared dependencies respectively, against 4 for PetClinic. This is the binding constraint on everything downstream (see below). |
| ② metamodel | JSON instances, metamodel `0.2.0-json`. Ecore/XMI still deferred. |
| ③ metrics | Catalogue `0.2.0`: `AIS`, `ADS`, `ACS`, `SCF`, `ASYNC%`, `DEG`, `BTW`, `NOE`, `NOD`, `CYC`, `SHARED_DB`, `GOD`. Group B is absent for want of telemetry, by design. |
| ④ models | Mutation-based labels + `logreg-l2/0.1.0` baseline, leave-one-system-out. |
| ⑤ explanation | Exact attributions from the linear model; no separate rationale artifact yet. |
| ⑥ api | FastAPI, read-only, trust level **T0**: no LLM, and no assessment at all until stage ④ ships a model. |

**The one number that governs the next months of work.** The extractor recovers almost no
dependencies outside PetClinic, and three consequences follow immediately: `AIS` has a degenerate
distribution, so `derive_thresholds.py` *refuses* to emit a threshold for it and `GOD` is
undetermined everywhere; the `cycle` and `shared-persistence` tasks have labels for PetClinic only,
so neither can be evaluated leave-one-system-out; and any centrality figure outside PetClinic is
currently a picture of missing evidence. A JVM analyser behind the existing seam (`extractor/spi.py`)
is therefore the highest-value next piece of work, ahead of any modelling.

## Documents

- `docs/01-pipeline.md` — the six-stage pipeline, its data contracts, and how each stage traces to the SLR
- `docs/02-subject-systems.md` — the three systems, why these three, and what each is for
- `docs/03-metric-catalogue.md` — initial metric definitions (RQ2)
- `docs/04-pattern-catalogue.md` — the ~10 reference patterns/anti-patterns that form the regression ground truth (SLR §5.4)
- `docs/05-labels-and-datasets.md` — where the training labels come from, per system
- `docs/06-design-decisions.md` — numbered, dated decisions (DD-001 …). Downstream work relies on these; reversing one is a versioned change, not an edit.
