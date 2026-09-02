# Positioning, and the runtime evidence the thesis is missing

Written 2026-09-02, after the question that matters was asked out loud: *where is the thesis
contribution, if SonarQube and the Azure metric tools already do this?*

The short answer is that the question is fair **about the artifact as it stands today**, and unfair
about the thesis. This document separates the two, with the evidence for each claim, because the
same question will be asked at every supervision meeting and at the defence.

---

## 1. The subject systems are not monoliths. The extraction is.

| System | What it is |
|---|---|
| Spring PetClinic Microservices | 8 Spring Boot services plus Zipkin, Prometheus and Grafana, wired through a config server, a Eureka registry and an edge gateway |
| FudanSELab Train Ticket | 33 `ts-*` services at the pinned commit, the most used microservice benchmark in the fault-diagnosis literature |
| Descartes TeaStore | 5 services plus a registry, built specifically for model extraction research |

All three are microservice systems. What looks monolithic is the **model this pipeline builds of
them**: 47 functional services and 2 edges. That number is a property of the regex static analyser,
not of the systems, and the dashboard makes it look like an architectural finding because it is
rendered next to real architectural metrics. That reading is the artifact's fault and it is worth
stating plainly rather than explaining away.

## 2. What the industrial tools actually do

Checked 2026-09-02 against vendor documentation rather than from memory.

**SonarQube.** Architecture analysis shipped in 2026.4 and is real: it reverse-engineers component
dependencies from code, lets a team declare the intended architecture, and flags deviations as
code-level issues. Its evidence is **source code only**. Its scope is **one codebase**, at module
and package level. There is no configuration evidence, no runtime telemetry, no traces, and no
cross-service analysis. It is in beta and on SonarQube Cloud first.
([overview](https://www.sonarsource.com/blog/introducing-architecture-in-sonarqube/),
[2026.4 release](https://www.sonarsource.com/products/sonarqube/whats-new/2026-4/))

**Azure Application Insights, Application Map.** Discovers the topology of a distributed
application from telemetry, shows calls between components with latency and failure rates, and does
it without reading a line of source. Its evidence is **runtime only**. It has no notion of an
intended architecture, no metric catalogue defined over a model, and nothing to say about code
structure. ([application map](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-map),
[dependency tracking](https://learn.microsoft.com/en-us/azure/azure-monitor/app/dependencies))

## 3. The two of them are the SLR's finding, restated by industry

SLR §4.12 reported that model-driven and metric-based research occupies mirror-image cells: model
studies cover smells, security and documentation but never runtime concerns, and metric studies do
the opposite. The tool market has the same shape. SonarQube is the static half with an architecture
feature bolted on. Application Insights is the runtime half with no architecture in it. Neither one
produces a single versioned representation in which a metric is defined over code, configuration
**and** runtime evidence at once, which is exactly gap **G1**.

So the honest positioning is not "we compute metrics they do not". Several of the metrics here exist
elsewhere in some form. It is:

1. **One model, four evidence classes** (G1). Not a code graph and a separate service map, but one
   instance where an endpoint, a declared call, a container and an observed span are elements of the
   same model, versioned together.
2. **Formal, comparable definitions** over that model (G2). SonarQube's dependency notion is
   internal to SonarQube; nobody can restate it in OCL over a published metamodel and get the same
   number from another tool.
3. **Interpretable prediction whose features are architectural elements** (G3), rather than a rules
   engine with a severity column.
4. **Explanations grounded in architectural entities, evaluated with developers** (G4). SLR §4.11
   found at most 7.5% of the corpus offers any explainability provision and none grounds it in
   architecture; §4.9 found about 6% does any human-subject evaluation.

## 4. The one measurement that no existing tool can produce

The metamodel already keeps `declared` and `observed` dependencies as separate arrays and refuses to
merge them. That decision was made on the first day and has never been exercised, because there is
no observed evidence yet. Once there is, the pipeline can compute something neither half of the
market can:

- an edge that **exists in code but never fires** at runtime: dead coupling, a dependency the team
  is paying for and not using;
- an edge that **fires but is not declared** anywhere in the source: the coupling nobody designed,
  which is where incidents come from;
- the **weight** of a declared edge, which turns every centrality metric from a structural guess
  into a measured one.

SonarQube cannot compute the first two because it never sees runtime. Application Insights cannot,
because it never sees the code. This delta is the sharpest single answer to "what is new here", it
is cheap to compute once traces exist, and it produces a figure that a reviewer immediately
understands.

## 5. Where the runtime evidence comes from

Two routes, and they answer different questions.

### Route A: run PetClinic ourselves and capture its traces

The PetClinic compose file already contains Zipkin, Prometheus and Grafana. Bringing the system up,
driving traffic through the gateway and exporting the spans produces observed dependencies for a
system whose source we have pinned, so declared and observed refer to exactly the same snapshot.
That is the clean experiment for the delta in §4, and it is the only route where the two sides are
guaranteed to be comparable.

It gives no fault labels, so it feeds RQ1 and RQ2 and does nothing for RQ3.

### Route B: the AnoMod dataset

Ping, K., Bin Mazhar, H., Wang, Y., Song, Y., Mäntylä, M. V. (2026). *AnoMod: A Dataset for Anomaly
Detection and Root Cause Analysis in Microservice Systems*. MSR '26.
[doi:10.1145/3793302.3793324](https://doi.org/10.1145/3793302.3793324) ·
data [doi:10.5281/zenodo.18342898](https://doi.org/10.5281/zenodo.18342898) · CC-BY-4.0 · 201.9 MB
archive.

It covers **Train Ticket** (41 microservices) and SocialNetwork (21 services), with logs, metrics,
distributed traces, API responses and code coverage. For Train Ticket: 63,975 traces, 444.6K log
lines, 33 metrics, 98,073 API requests. Four families of injected faults (performance, service,
database, code level) with ground truth at **service and code-region granularity**.

This is the answer to the open question `docs/05-labels-and-datasets.md` left standing: *verify which
fault-injection dataset is current and what exactly it labels*. It is current, it is labelled at
service level, and it is openly licensed.

**The risk, measured.** AnoMod's Train Ticket has 41 microservices; our pinned commit
(`refactor/v2`, DD-003) yields 30 functional services and 38 infrastructure containers. Comparing
our modelled service names against `master`, which is the branch the 41-service figure is
consistent with:

| | |
|---|---:|
| `ts-*` modules on `master` | 47 |
| modelled services at our pinned commit (any role) | 67 |
| names present in both | 34 |
| `master` modules with **no** element in our model | 13 |
| our **functional** services absent from `master` | 11 |

So roughly seven in ten of `master`'s modules would find an element to attach observed evidence to,
and eleven services that only exist on `refactor/v2` (`ts-ticket-service`,
`ts-food-booking-service`, `ts-order-query-service`, the notification pair, and others) would never
appear in a trace at all. That is not a clean join.

Three ways out, in order of honesty rather than convenience:

1. **Re-pin Train Ticket to the branch the dataset was collected on.** DD-003's own revisit clause
   already names this condition: *"Revisit if the fault-injection dataset turns out to be defined
   only against master. The label source is the reason this system is in the study at all, so it
   outranks the branch preference."* The clause was written on 2026-08-31 and the evidence arrived
   two days later.
2. **Keep `refactor/v2` and record the unmapped services as evidence gaps.** The metamodel already
   supports exactly this, and a 70% join with the gaps stated is defensible. It weakens every
   system-level metric, since `SCF` over a graph that is missing a third of its edges is not
   comparable with anything.
3. **Drop Train Ticket as the label source** and use AnoMod's SocialNetwork instead, adding it as a
   fourth subject system. Costs a new extraction target and loses the alignment with the
   fault-diagnosis literature that Train Ticket was chosen for.

### The measurement, made 2026-09-02

The archive is on disk at `data/external/anomod/` (see that directory's README for provenance and licence) and `subjects/inspect_anomod.py` has been run against it. The traces are
**Apache SkyWalking** exports, not Zipkin or Jaeger: each file carries a `metadata.services_discovered`
list and spans keyed by `service_code`, with parent and child node ids, depth, duration and an error
flag. That shape is better than expected, because a parent-to-child pair of `service_code` values is
an observed dependency directly, and `depth` plus the span tree give call path length and fan-out
without further work.

Thirteen runs for Train Ticket: one normal case and twelve injected faults, named by level
(`Lv_P_` performance, `Lv_S_` service, `Lv_D_` database, `Lv_C_` code), each with traces, logs,
metrics, API responses and coverage.

**35 distinct Train Ticket services appear in the traces.** The join:

| Pinned at | Services matched | |
|---|---:|---|
| `refactor/v2` (DD-003, today) | 24 / 35 | **69%** |
| `master` | 35 / 35 | **100%** |

Not one traced service is missing a module on `master`. The eleven unmatched under `refactor/v2` are
not marginal either: `ts-route-service` (12,740 spans), `ts-order-other-service` (10,790),
`ts-price-service` (3,308), `ts-station-food-service` (3,792), `ts-food-service` (2,470),
`ts-train-food-service` (2,527), `ts-notification-service` (2,080) and four others. Thirteen of our
functional services, the `refactor/v2`-only ones, never appear in a trace at all.

This is conclusive: **the dataset was collected on a Train Ticket whose service naming is `master`,
not `refactor/v2`.** DD-003's own revisit clause fires, word for word: *"Revisit if the
fault-injection dataset turns out to be defined only against master. The label source is the reason
this system is in the study at all, so it outranks the branch preference."*

### Both routes need the same new capability

Whichever comes first, stage ① needs an **observed evidence class**: a parser from spans
(Zipkin/Jaeger JSON, or OTLP) to `Dependency` elements with `provenance: observed`, a call count and
a latency distribution. That parser is the same for a live Zipkin export and for a dataset on disk,
so it is not wasted work under either route.

## 6. What this changes in the thesis narrative

Until runtime evidence lands, the artifact is a static analyser with fewer features than SonarQube,
and any comparison table would say so. After it lands, the comparison table has a column that no
competitor can fill, and the RQ2 claim about complementarity becomes measurable rather than
asserted.

The order of work therefore is: **runtime evidence first, then the JVM analyser**. That reverses
what `README.md` currently recommends. The JVM analyser makes the declared side of the graph
accurate, which matters, but the observed side is what makes the thesis distinguishable from a
product a reviewer can buy.
