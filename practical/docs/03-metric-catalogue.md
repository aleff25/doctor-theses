# Metric catalogue (draft v0)

Obj. 2 / T3 · closes gap **G2** · answers **RQ2**

SLR §5.2 states G2 as "fragmented and informally-defined architecture-aware metrics". The
contribution is therefore not *inventing* metrics — several of these exist informally in the
literature — but giving them a single formal definition over one metamodel, so they are
unambiguously computable and comparable across systems. Each metric below must end up with an OCL
expression in `metrics/` before it counts as catalogued.

Notation: the architecture model is a graph `G = (S, D)` where `S` is the set of services and
`D ⊆ S × S` the set of directed dependency edges, each edge carrying a `kind ∈ {sync, async}` and an
observed call volume. `E(s)` = endpoints of service `s`, `P(s)` = persistence stores of `s`.

## Group A — Inter-service coupling

| ID | Metric | Definition | Evidence |
|---|---|---|---|
| `AIS` | Absolute Importance of a Service | in-degree: `|{t : (t,s) ∈ D}|` | static + config |
| `ADS` | Absolute Dependence of a Service | out-degree: `|{t : (s,t) ∈ D}|` | static + config |
| `ACS` | Absolute Criticality | `AIS(s) × ADS(s)` | derived |
| `SCF` | Service Coupling Factor | `|D| / (|S|² − |S|)` — system-level density | derived |
| `ASYNC%` | Asynchrony ratio | share of `s`'s edges with `kind = async` | static + config |

`AIS`/`ADS`/`ACS` are adapted from the service-oriented coupling literature; the contribution is
computing them over a model that fuses declared *and* observed dependencies rather than one or the
other. Report the delta between the two — a dependency that exists in code but never fires at
runtime, or fires but is not declared, is itself a finding.

## Group B — Communication complexity

| ID | Metric | Definition | Evidence |
|---|---|---|---|
| `CPL` | Call path length | mean number of services traversed per end-to-end request | traces |
| `CPL_max` | Deepest call path | max over observed request types | traces |
| `CHAT` | Chattiness | mean calls per service-pair per request | traces |
| `FANOUT_r` | Request fan-out | distinct services touched by request type `r` | traces |

This group is trace-only, and is the reason a system without telemetry (see PiggyMetrics in
`02-subject-systems.md`) cannot exercise the full catalogue.

## Group C — Service granularity

| ID | Metric | Definition | Evidence |
|---|---|---|---|
| `NOE` | Number of endpoints | `|E(s)|` | static |
| `NOD` | Number of domain entities owned | count of persisted aggregate roots | static |
| `LOC_s` | Size | aggregated LOC over the service's modules | static |
| `SGI` | Service Granularity Index | normalised composite of `NOE`, `NOD`, `LOC_s` | derived |

`SGI`'s weighting is an open decision — do not freeze it before the sensitivity analysis on the
three subject systems, and report it as a tuned parameter rather than a constant.

## Group D — Centrality

| ID | Metric | Definition | Evidence |
|---|---|---|---|
| `DEG` | Degree centrality | over `G` | derived |
| `BTW` | Betweenness centrality | over `G` | derived |
| `PR` | PageRank | over `G`, weighted by call volume | derived + traces |

Weighting by observed call volume is what distinguishes these from the graph metrics already
common in the corpus (SLR §4.12 shows graph/GNN approaches clustering on runtime concerns and
metric-based approaches on structural ones — these metrics sit deliberately across that line).

## Group E — Architectural smells

Each smell is a *predicate* over the model, defined in terms of the metrics above. This is what
makes explanations decomposable: a smell fires because named metrics crossed named thresholds on
named elements.

| ID | Smell | Predicate (draft) |
|---|---|---|
| `GOD` | God service | `AIS(s) > θ₁ ∧ NOE(s) > θ₂ ∧ NOD(s) > θ₃` |
| `CYC` | Cyclic dependency | `s` participates in a cycle in `G` |
| `SHARED_DB` | Shared persistence | `∃ p ∈ P(s₁) ∩ P(s₂), s₁ ≠ s₂` |
| `CHATTY` | Chatty communication | `CHAT(s₁,s₂) > θ₄` |
| `NANO` | Nano service | `NOE(s) = 1 ∧ LOC_s < θ₅` |
| `BOTTLE` | Bottleneck | `BTW(s)` in top decile ∧ no replication in deployment model |

**Thresholds are the weak point of this whole group** and reviewers will go straight at them.
Derive `θ` empirically from the distribution across the three subject systems, state the derivation
method in the thesis, and treat the thresholds as a versioned part of the catalogue rather than as
magic numbers in code.

## Required per entry

Before a metric is considered catalogued it needs all six:

1. Formal OCL definition over the metamodel
2. Intended interpretation in one sentence
3. Which quality attribute it is hypothesised to affect, and in which direction
4. Evidence class(es) required to compute it (static / config / runtime)
5. Known limitations and threats to construct validity
6. Reference implementation + unit test over a hand-built model instance

Item 6 is what keeps the catalogue honest: a metric with no test on a model whose correct value is
known by hand is a definition, not a metric.

## Relation to OO metrics

RQ2 asks how these *complement* traditional OO metrics, which means the CK suite must actually be
computed too, aggregated to service level, and included as a comparison arm — otherwise the
complementarity claim is asserted rather than shown. Plan for a Java OO-metric tool (Spoon,
JavaParser or CK) in `extractor/` from the start rather than bolting it on later.

---

## Implementation status (catalogue 0.2.0)

Twelve metric IDs are implemented as reference implementations in `metrics/aam4j_metrics/`, each
with unit tests over hand-built models whose expected values are stated in the test docstring
(item 6 of "Required per entry"). Items 1 and 5, the OCL definition and the construct-validity
note, are still outstanding for every entry, so nothing below is *catalogued* in the full sense of
this document yet.

| ID | State | Note |
|---|---|---|
| `AIS`, `ADS`, `NOE`, `SHARED_DB` | implemented | catalogue 0.1.0 |
| `ACS` | implemented | derived from `AIS` and `ADS` |
| `SCF` | implemented | the only system-level metric, so `element_kind` is a real column |
| `ASYNC%` | implemented | undetermined for a service with no edges; DD-004 governs what counts as async |
| `DEG` | implemented | normalised by `|S| - 1`, so it compares across systems of different size |
| `BTW` | implemented | Brandes, **unweighted**: there is no observed call volume to weight by, and the value says so |
| `NOD` | implemented | needs metamodel 0.2.0-json, which added the `DomainEntity` element |
| `CYC` | implemented | Tarjan; the note names the other members of the cycle |
| `GOD` | implemented, **undetermined in practice** | see the threshold refusal below |
| `PR` | absent | would need call volume; an unweighted PageRank is not the metric this document defines |
| `LOC_s`, `SGI`, `NANO` | absent | the extractor emits no LOC facts yet |
| `CPL`, `CPL_max`, `CHAT`, `FANOUT_r`, `CHATTY` | absent | trace-only, and no subject system is instrumented yet |
| `BOTTLE` | absent | needs `BTW` plus replication facts from the deployment model |

Absent is a deliberate state, not a backlog entry. A metric computed from evidence the pipeline
does not have would be a fabrication, and the SLR's own criticism of the corpus is precisely that
studies report numbers whose evidence base is not stated.

### Thresholds are derived, and the derivation can refuse

`metrics/derive_thresholds.py` computes the group-E thresholds as a nearest-rank quantile over the
pooled distribution of the functional services of all three pinned subject systems, and writes them
to `metrics/catalogue/thresholds.json` with the method and the exact (system, snapshot) pairs used.
Nearest-rank rather than an interpolating quantile, because the inputs are counts and no service
can have 2.4 endpoints.

The script refuses to emit a threshold whose quantile equals the minimum of the distribution: such
a threshold separates nothing. On the current profiles this fires on `AIS` (q=0.9 equals 0 over
n=59 services), so `GOD` reports **undetermined** on every service rather than a verdict. The cause
is the regex static analyser recovering almost no dependencies outside PetClinic, which makes this
a finding about stage ①, not about the subject systems. A conjunctive predicate evaluated with two
of its three conjuncts is a looser predicate, so `GOD` is all-or-nothing by construction.
