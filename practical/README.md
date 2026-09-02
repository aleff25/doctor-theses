# AAM4J — Architecture-Aware Metrics for Java

Practical (artifact) track of the PhD *Architecture-Aware Software Metrics for AI-Supported
Quality Assessment in Java-Based Distributed Systems* — Aleff Rodrigues Mendes de Oliveira,
Iscte-IUL. Supervisors: José Vicente Pereira dos Reis, Vítor Manuel Bastos.

`AAM4J` is a working name; change it freely before the first publication.

## What this repository is

The SLR ([`../theoretical/slr/`](../theoretical/slr/)) established four gaps (G1-G4) and mapped
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
| `dashboard/` | Obj. 5 / T6 | G4 | React view of the results, each number traced back to its source code |
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

## Running it on any machine

Stages 1 to 3 need **one third-party package, PyYAML**: the extractor parses `application.yml` and
`docker-compose.yml`, and the DD-002 role catalogue is YAML. Nothing else. A reviewer with Python,
git and that one package reproduces every stored artifact, byte for byte. The API and the learning
baseline are optional extras. There is no Docker, no Maven and no JDK in the loop: the pipeline
reads the subject systems' sources and descriptors, it never builds or runs them.

### Prerequisites

| Need | Why |
|---|---|
| Python 3.10 or newer | tested on 3.10 and 3.14 |
| pip 23.1 or newer | older pip cannot do an editable install from `pyproject.toml` alone |
| git | to fetch the three subject systems at their pinned commits |
| About 1.5 GB of free disk | the three clones; the pipeline's own outputs are a few hundred KB |
| Network access, once | for the clones and, if you want them, the optional extras |

### 1. Get the code

```bash
git clone https://github.com/aleff25/doctor-theses.git
cd doctor-theses/practical
```

### 2. Create the environment

macOS and Linux:

```bash
python3 -m venv .venv
./.venv/bin/pip install -e '.[api,learn,dev]'
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\pip install -e ".[api,learn,dev]"
```

Drop the extras (`pip install -e .`) if you only want stages 1 to 3. Every command below is written
with `./.venv/bin/python`; on Windows that is `.\.venv\Scripts\python`.

### 3. Fetch the subject systems

```bash
./subjects/fetch_subjects.sh
```

Clones Spring PetClinic Microservices, FudanSELab Train Ticket and Descartes TeaStore, then checks
each out at the exact commit in `subjects/subjects.lock.json`. With no arguments the script never
writes the lockfile: you get the pinned commits or a non-zero exit. Re-pinning is `--update`, an
explicit act. The clones are gitignored.

### 4. Run the pipeline

```bash
./.venv/bin/python run_pipeline.py --system petclinic
./.venv/bin/python run_pipeline.py --system teastore
./.venv/bin/python run_pipeline.py --system trainticket
```

Each run prints the services with the DD-002 rule that assigned each role, the service graph, the
metric profile, and the evidence gaps the model recorded. It writes into `data/`:

```
data/raw/<system>/<sha8>/        extraction bundle, one file per evidence class
data/interim/<system>/<sha8>/    the architecture model instance
data/processed/<system>/<sha8>/  the metric profile, CSV and JSON
```

### 5. Derive the smell thresholds

```bash
./.venv/bin/python metrics/derive_thresholds.py
```

Computes the group-E thresholds from the pooled distribution of all three systems and writes
`metrics/catalogue/thresholds.json`. Expect it to **refuse** the `AIS` threshold: that refusal is
correct and is explained under Current status below.

### 6. Build the supervision and train the baseline

```bash
./.venv/bin/python models/build_dataset.py
./.venv/bin/python models/train_baseline.py --task oversized-service
```

The first generates the architectural mutants, their metric profiles, the label file and the
per-task datasets. The second trains the L2-regularised logistic baseline leave-one-system-out and
writes prediction records with exact attributions.

### 7. Start the API

```bash
./.venv/bin/python -m uvicorn aam4j_api.app:app --app-dir api --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`. A quick check from another terminal:

```bash
curl -s localhost:8000/health
curl -s "localhost:8000/systems/petclinic/profile?metric=AIS&metric=SHARED_DB"
curl -s localhost:8000/systems/petclinic/services/customers-service
```

The API serves a different data root if you point `AAM4J_ROOT` at one.

### 8. Open the dashboard

```bash
./.venv/bin/python dashboard/build_dashboard_data.py   # writes dashboard/public/dashboard.json
cd dashboard && npm install && npm run dev             # http://localhost:5173
```

A React application over what the pipeline stored, with five views: what was measured, every
service with the **source code behind each of its numbers**, the metric catalogue as a hoverable
glossary, every design decision with its cost and the condition to reopen it, and the learning
results fold by fold.

To hand it to someone who will not run a toolchain:

```bash
cd dashboard && npm run standalone     # dist-standalone/aam4j-dashboard.html
```

One file, about 800 KB, that opens by double-click. Note that the ordinary `npm run build` output
in `dist/` does **not** open that way: `file://` pages have the opaque origin `null` and Chrome
blocks the module script, the stylesheet and the data fetch from there. Use `npm run preview` to
serve `dist/` locally, or the standalone build. See `dashboard/README.md`.

Node 20 or newer. This is the only part of the repository that needs a JavaScript toolchain, and
nothing else depends on it.

### 9. Run the tests

```bash
./.venv/bin/pytest
```

Run it **from `practical/`**. `pyproject.toml` confines collection to `tests/`, because `subjects/`
holds three full clones, two of which ship Python test suites of their own that would otherwise be
collected and fail on their own dependencies.

### Did it work?

| Check | Expected |
|---|---|
| `pytest` | 76 passed. The API tests skip if the `api` extra is not installed, and tests needing PetClinic skip until the pipeline has run once. |
| `wc -l data/processed/*/*/metric_profile.csv` | 46, 145 and 332 lines for petclinic, teastore and trainticket, one header plus 11 service metrics per functional service plus one system-level `SCF` row |
| `metrics/catalogue/thresholds.json` | `GOD.AIS` present with `"value": null` and a `reason` |
| `models/build_dataset.py` | 12 mutants, 194 labelled rows, three task datasets |
| `dashboard/build_dashboard_data.py` | 12 implemented metrics, 13 rule cards, 13 references, 0 dangling citations |
| Re-running everything | byte-identical outputs. No artifact contains a timestamp or an absolute path, so a diff after a second run is a bug, not noise. |

### If something goes wrong

- **`pytest` tries to import `fastapi.testclient` from `subjects/`.** You ran it from the wrong
  directory, or with a `-p` override that bypassed `pyproject.toml`. Run it from `practical/`.
- **`no artifact for <system>@<sha>`** from the API, or `missing profile` from
  `derive_thresholds.py`. Run `run_pipeline.py` for that system first: nothing downstream ever
  recomputes an upstream stage on the fly, by design.
- **`pinned commit ... not found`** from `fetch_subjects.sh`. The upstream branch was force-pushed.
  Do not re-pin silently: a changed SHA invalidates every stored profile that claims to describe it.
- **`'system' is not in subjects.lock.json`.** Only the three pinned names are accepted, which is
  what stops an unpinned working copy from being analysed as if it were the subject system.
- **`Multiple top-level packages discovered in a flat-layout`** from pip. An old checkout, from
  before the packages were declared explicitly in `pyproject.toml`. Pull and retry: setuptools
  cannot tell `docs/`, `data/` and `subjects/` from importable packages, and refuses to guess.
- **`No module named 'yaml'`** when running the pipeline. The environment was never installed, or
  the wrong `python` is being used. `./.venv/bin/pip install -e .` is the minimum.
- **A `scikit-learn` build from source that fails.** Only `models/train_baseline.py` needs it.
  Install without that extra (`pip install -e '.[api,dev]'`); everything else still runs.

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
| ⑥ dashboard | React over the stored artifacts. Shows the metric profile, the evidence and the code behind each number, the rules with their costs, and the folds. Recomputes nothing. |

**The one number that governs the next months of work.** The extractor recovers almost no
dependencies outside PetClinic, and three consequences follow immediately: `AIS` has a degenerate
distribution, so `derive_thresholds.py` *refuses* to emit a threshold for it and `GOD` is
undetermined everywhere; the `cycle` and `shared-persistence` tasks have labels for PetClinic only,
so neither can be evaluated leave-one-system-out; and any centrality figure outside PetClinic is
currently a picture of missing evidence. A JVM analyser behind the existing seam (`extractor/spi.py`)
is therefore the highest-value next piece of work on the **declared** side of the graph. Whether it
comes before or after runtime evidence is now an open question, and the argument is in
`docs/07-positioning-and-runtime-evidence.md`: the observed side is what distinguishes this artifact
from tools a reviewer can buy, and the declared side is what makes it accurate.

## Documents

- `docs/01-pipeline.md` — the six-stage pipeline, its data contracts, and how each stage traces to the SLR
- `docs/02-subject-systems.md` — the three systems, why these three, and what each is for
- `docs/03-metric-catalogue.md` — initial metric definitions (RQ2)
- `docs/04-pattern-catalogue.md` — the ~10 reference patterns/anti-patterns that form the regression ground truth (SLR §5.4)
- `docs/05-labels-and-datasets.md` — where the training labels come from, per system
- `docs/06-design-decisions.md` — numbered, dated decisions (DD-001 …). Downstream work relies on these; reversing one is a versioned change, not an edit.
- `docs/07-positioning-and-runtime-evidence.md` — what this does that SonarQube and Azure do not, why that answer depends on runtime evidence that does not exist yet, and the two routes to getting it
