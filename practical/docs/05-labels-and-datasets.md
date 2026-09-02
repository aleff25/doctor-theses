# Labels and datasets

RQ3 asks whether hybrid metric+AI models can predict or explain quality outcomes. That requires
labels. **This is the highest-risk part of the practical work** and the place where thesis projects
in this area most often stall — the metrics are the easy half; supervision is the hard half.

## The problem

The three subject systems are open-source reference applications. Two consequences:

- Their git histories are not production defect histories. PetClinic in particular is maintained as
  a teaching artifact, so mining its commits for defect labels yields a tiny, biased signal.
- None of them has an incident record of the kind an industrial system would have.

So labels have to come from somewhere other than "mine the repository", and each system contributes
a different kind.

## Per-system label strategy

### Train Ticket → fault / root-cause labels

The strongest option. The benchmark exists precisely to supply injected faults with known root
causes, which gives supervised labels of the form `(system state, faulty service)`. This is what
makes RQ3 answerable at all, and it is what gives comparability with the RCA studies in the SLR
corpus.

Action before committing: verify which fault-injection dataset/version is current and what exactly
it labels (service-level? call-level? with or without telemetry captures?). Do not design the
feature pipeline before knowing the label granularity — they have to match.

### TeaStore → performance / resource labels

Run under controlled load, measure latency, throughput and energy. The labels are continuous and
generated on demand, so the dataset size is a function of experiment time rather than of what
someone else published. Good for regression targets; useless for defect prediction.

Action: define the load profiles and the SLO thresholds *before* running, and keep them fixed
across snapshots, or the labels are not comparable between runs.

### PetClinic → pattern ground truth, not statistical labels

Small and clean enough to state by hand which patterns hold. Use it for the regression suite of
`04-pattern-catalogue.md` and for validating the extractor's correctness. Do **not** try to build a
training set from it — 8 services will not support a learned model, and attempting it invites the
"n too small" objection at the defence.

## Synthetic and mutation-based supervision

A fourth source worth considering seriously: deliberately mutate a subject system's architecture
(merge two services, add a shared database, introduce a cycle) and label the mutants by
construction. This yields as much labelled data as compute allows and directly tests whether the
metrics respond to architectural change in the expected direction — which is, arguably, a cleaner
test of RQ2 than any prediction task.

Threat to flag explicitly if used: mutants are not drawn from the same distribution as real
architectural decay, so results transfer to "does the metric detect this property" and not to "does
this predict real-world failure". Say so in threats to validity rather than letting a reviewer say
it first.

## Dataset layout

```
data/
  raw/         extraction bundles, one dir per (system, snapshot)
  interim/     architecture model instances (.xmi)
  processed/   metric profiles (parquet + csv), the model-ready tables
  labels/      label sets, one dir per source, each with a README stating provenance
```

Every dataset directory needs a provenance note: which system, which commit SHA from
`subjects/subjects.lock.json`, which metamodel and catalogue version, when generated, by which
command. SLR §4.10 found that only ~14% of the corpus ships a reproducible artifact — the thesis
should not join that majority.

## Splitting

Split **by system or by service**, never randomly by row. Random row splits leak: two snapshots of
the same service land on both sides and the model memorises the service rather than learning the
relationship. Report leave-one-system-out results as the headline number; it is the honest estimate
of how this generalises, and it is what a sceptical reviewer will ask for.

---

## Implemented: mutation-based supervision (2026-08-31)

The fourth source above is the one that could start without waiting on anything, and it now runs:
`models/aam4j_models/mutate.py` plus `models/build_dataset.py`.

Three operators, each labelling by construction:

| Operator | Task | What it does |
|---|---|---|
| `introduce_cycle` | `cycle` | reverses an existing declared edge, closing a two-service cycle |
| `share_database` | `shared-persistence` | points a service with no store at another service's store |
| `merge_services` | `oversized-service` | absorbs one service into another: endpoints, entities, stores and edges |

Targets are chosen by sorted element ID, never at random, so the whole dataset is reproducible from
the pinned snapshots and a catalogue version.

### How the negative class is built

This is where synthetic supervision usually goes wrong, so it is explicit:

- a service the operator damaged is a positive;
- a service that already exhibited the injected property in the base model is **not emitted at
  all**, because its label is genuinely unknown;
- everything else is a negative, and when the task has no deterministic detector to verify the base
  against (`oversized-service`), every such row carries `note = "unverified negative"` so the
  weakness travels with the data instead of living in someone's memory.

### The circularity guard

`CYC` detects cycles deterministically, so a classifier predicting the `cycle` task from a feature
set containing `CYC` would score perfectly and mean nothing. `models/aam4j_models/dataset.py`
declares, per task, the features that must be excluded (`EXCLUDED_FEATURES`), and the exclusion is
recorded in the run record of every training run. `SCF` is excluded from every task for a related
reason: it is one number per system, so it would act as a system identifier under a
leave-one-system-out split.

### What the first run produced

| Task | Rows | Positives | Systems with labels |
|---|---|---|---|
| `oversized-service` | 227 | 9 | petclinic, teastore, trainticket |
| `cycle` | 138 | 8 | petclinic, trainticket |
| `shared-persistence` | 3 | 2 | petclinic only |

(Figures after DD-009 re-pinned Train Ticket to `master`. Before it, `cycle` had 12 rows in one
system and could not be evaluated leave-one-system-out at all.)

Two of the three tasks can now be evaluated leave-one-system-out, and the one that cannot is blocked
by the same thing that blocks `GOD`: the regex analyser recovers 4 call sites in PetClinic, 3 in
Train Ticket and 0 in TeaStore, and two of the three operators need dependencies or persistence
links to have something to damage. A JVM static analyser behind the existing `StaticAnalyser` seam
is therefore a prerequisite for supervision, not only for the metrics.

`models/train_baseline.py` trains the L2-regularised logistic baseline on these tables and writes
prediction records in the 4 -> 5 contract shape. Its numbers are a wiring test: they show whether
the metrics respond to an injected architectural change, and say nothing about real-world quality
outcomes. That sentence belongs in threats to validity, as this document already required.

---

## Resolved: the label source (2026-09-02)

The open action at the top of the Train Ticket section, *verify which fault-injection dataset is
current and what exactly it labels*, is closed.

**AnoMod** (Ping, K., Bin Mazhar, H., Wang, Y., Song, Y., Mäntylä, M. V., 2026, MSR '26,
[doi:10.1145/3793302.3793324](https://doi.org/10.1145/3793302.3793324), data
[doi:10.5281/zenodo.18342898](https://doi.org/10.5281/zenodo.18342898), CC-BY-4.0). Thirteen Train
Ticket runs, one normal and twelve with injected faults across four levels: performance
(`Lv_P_`), service (`Lv_S_`), database (`Lv_D_`) and code (`Lv_C_`). Each run carries traces, logs,
metrics, API responses and coverage.

**Label granularity, which this document said to establish before designing the feature pipeline:**
service level and code region. Service level is what this pipeline's elements are, so the join is
direct. Code-region labels are finer than any element in the metamodel and are not usable without
adding one.

**Traces are Apache SkyWalking**, which is better than the Zipkin or Jaeger assumed here: spans
carry `service_code` with parent and child node ids and depth, so an observed dependency is a
parent-to-child pair and the span tree yields call path length and fan-out for group B directly.

The dataset lives at `data/external/anomod/`, gitignored, with provenance and licence in that
directory's README. Attribution is required by CC-BY-4.0 for any figure derived from it.
