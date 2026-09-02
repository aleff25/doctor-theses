# Design decisions

Numbered, dated, with rationale. Anything downstream may rely on a decision recorded here;
reversing one is a versioned change to the metamodel or catalogue, not an edit.

---

## DD-001 — Element identity scheme · 2026-08-17

**Decision.** Element IDs are `<system>/<kind>/<stable-name>`, with no snapshot component.

```
petclinic/service/vets-service
petclinic/endpoint/vets-service#GET:/vets/{vetId}
petclinic/edge/api-gateway->vets-service:sync
petclinic/store/vets-db
petclinic/deployment/vets-service
```

**Rules.**

- The snapshot is a property of the *model instance*, never of the element ID. IDs must be
  comparable across snapshots or nothing can be tracked over time.
- `stable-name` derives from the **deployment/module name** (Maven artifactId, container name), not
  from a fully-qualified class name. FQCNs move under refactoring; deployment names are the unit the
  architecture is actually described in.
- Edge IDs are derived from their endpoints plus `kind`, so a sync and an async edge between the
  same pair are distinct elements.
- Endpoint IDs use the route template (`/vets/{vetId}`), never a concrete instantiation.

**Rationale.** Everything downstream — metric profiles, labels, attributions, explanations —
references these IDs. The scheme has to survive refactoring inside a service and has to be
human-readable, because explanations quote it back to developers.

**Known weakness.** A service that is *renamed* between snapshots reads as one element disappearing
and another appearing. Accept this for now; handle it with an explicit alias table if and when it
occurs in the subject systems.

---

## DD-002 — Infrastructure services in the graph · 2026-08-17

**Decision.** Model everything; filter at metric time. Every service carries
`role ∈ {functional, infrastructure}`. The default service graph `G` used by the metrics of
`03-metric-catalogue.md` contains **functional services only**. Metrics may opt in to infrastructure
nodes explicitly, and any figure that includes them must say so.

**Classified as infrastructure** in the current subject systems:

| System | Infrastructure |
|---|---|
| petclinic | `config-server`, `discovery-server`, `admin-server`, `api-gateway`* |
| teastore | `registry` |
| trainticket | config/registry equivalents — to be confirmed against `refactor/v2` |

\* `api-gateway` is deliberately marked infrastructure **but** is the subject of pattern 5 in
`04-pattern-catalogue.md`. Pattern detection runs over the full model, not the filtered `G` — the
filter applies to the metric layer only.

**Rationale.** Extracting them and filtering later is strictly more informative than not extracting
them. Discovery and config servers are touched by nearly every service, so including them in `G`
would make them top the `AIS` and betweenness rankings in every system — a result that is true and
completely useless, and which would corrupt the god-service and bottleneck smells.

**Consequence.** `role` is part of the metamodel (DD-002 is a metamodel requirement, not an
extractor convenience), and the classification rule must be explicit and auditable rather than a
hardcoded name list. Start with a name list for PetClinic, but record it as catalogue data.

---

## DD-004 — Telemetry transport is excluded from the model by rule · 2026-08-17

**Decision.** Message brokers and transports that carry *observability data* are never modelled as
application communication. Exclusion is by **rule**, not by a name list.

**Rule.** A messaging dependency is application communication only if the producing and consuming
endpoints are both application code. A dependency whose counterparty is an instrumentation agent,
collector or telemetry sink is `role: telemetry` and is excluded from `G` and from `ASYNC%`.

**Why this exists.** TeaStore contains 26 files referencing AMQP/RabbitMQ. Every one of them belongs
to `utilities/tools.descartes.teastore.kieker.rabbitmq` — Kieker's telemetry transport, not
application messaging. A naive extractor grepping for `rabbitmq|kafka|amqp|jms` would emit **phantom
async edges** in the one subject system that has no application-level async at all.

The failure mode is worse than a wrong number: `ASYNC%` would become a measurement of the
*observability stack*, i.e. a feature contaminated by the very instrumentation used to compute the
other features. Verified state across the subject set — PetClinic: no async. TeaStore: none at
application level. Train Ticket: genuine `spring-boot-starter-amqp` in ~5 services (food-booking,
sms-notification, user-notification, delivery, ticket-purchase).

**Consequence.** `role` is now three-valued at minimum (`functional`, `infrastructure`, `telemetry`)
and DD-002's classification table does not yet contemplate telemetry nodes. Zipkin/Jaeger collectors
and Prometheus scrape targets fall under the same rule.

**Second-order consequence.** `ASYNC%` has real variance in exactly one of three subject systems.
Treat it as a reporting metric, not a model feature, until an event-driven subject exists.

---

## DD-003 — Train Ticket pinned to `refactor/v2` · 2026-08-17 · **SUPERSEDED by DD-009 (2026-09-02)**

**Decision.** Candidate's call, overriding the earlier recommendation of `master`.

See `02-subject-systems.md` for the consequences: 33 modules rather than 47, loss of like-for-like
comparability with SLR-corpus studies, and fault-injection labels that must be re-verified against
the v2 layout.

**Outcome.** The re-verification happened on 2026-09-02 and the labels did not survive it. Reversed
by DD-009. This entry stays in place because a decision that was made, acted on and then overturned
by evidence is part of the record, and the revisit clause above is what made the reversal a
procedure rather than a change of mind.

---

## DD-005 — Domain entities are metamodel elements · 2026-08-31

**Decision.** `DomainEntity` (`id`, `service`, `java_type`, `table`) joins the metamodel.
`METAMODEL_VERSION` goes to `0.2.0-json`. Entity IDs are `<system>/entity/<service>#<JavaType>`.

**Why.** `NOD` (number of domain entities owned) is a group-C metric and a conjunct of the
god-service predicate, and the extractor was already producing the facts that stage ② was dropping
on the floor. Recomputing them at metric time would have put parsing behind the metric layer and
broken the stage contract.

**Why the type and not the table.** The table is the mapping and can change without the domain
concept changing. DD-001's stable-name rule is satisfied by the owning service plus the type's
simple name.

**Known weakness.** The catalogue says *aggregate roots*; the extractor sees persisted types, which
over-counts an aggregate that spans several tables. Recorded as a construct-validity limitation of
`NOD` rather than corrected silently.

**Consequence.** Stored `model.json` files written before this change deserialise fine (the field
defaults to empty), but their profiles carry no `NOD`. Re-run `run_pipeline.py` rather than mixing
metamodel versions inside one dataset.

---

## DD-006 — Smell thresholds are derived data, and the derivation may refuse · 2026-08-31

**Decision.** Group-E thresholds live in `metrics/catalogue/thresholds.json`, are produced by
`metrics/derive_thresholds.py` as a nearest-rank quantile over the pooled subject-system
distributions, and carry their method and provenance. If the quantile equals the minimum of the
distribution, **no threshold is emitted** and the reason is stored in its place. A predicate that
needs an unemitted threshold reports undetermined for every element.

**Why.** `03-metric-catalogue.md` says thresholds are the weak point reviewers will attack. Three
failure modes are closed at once: magic numbers in code (they are catalogue data, versioned with
`catalogue_version`), unstated derivation (the file records the method and the exact snapshots), and
thresholds derived from a distribution that cannot support one.

**What it does today.** `GOD.AIS` is refused (q=0.9 equals the minimum, 0, over n=47), so `GOD` is
undetermined on every service of every system. That is the correct output: firing the predicate on
two of its three conjuncts would manufacture god services out of a threshold that was never
derivable.

**Consequence.** Changing the quantile changes the threshold set version, which is stamped into
every response the API serves. It is a versioned change, not a tuning knob to be turned quietly
before a figure is drawn.

**Known defect, found 2026-09-02.** The metric profile does *not* carry the threshold set version.
It stamps `metamodel_version` and `catalogue_version` only, and `derive_thresholds.py` changes
catalogue data without touching either. Re-deriving the thresholds therefore silently invalidates
every stored profile, because `GOD`'s note embeds the refusal reason, and a stale profile is
indistinguishable from a fresh one by its own provenance. This surfaced when a determinism check
diffed a PetClinic profile computed under the previous threshold set against one computed under the
new one and reported a change that looked like non-determinism.

The fix is one column: add `threshold_set_version` to `metrics/aam4j_metrics/profile.py` and to the
API's row typing, so a profile states every input that produced it. Until then, re-run
`run_pipeline.py` for **every** system after any `derive_thresholds.py` run, and treat mixed
profiles as invalid. Constraint 4 of `docs/01-pipeline.md` says everything is versioned; this is a
place where it is not, and the gap was found by the practice in P4 rather than by review.

---

## DD-007 — The API is read-only and offers no assessment at T0 · 2026-08-31

**Decision.** `api/` serves artifacts written by the pipeline and never recomputes them. Every
response carries a `provenance` block with the trust level, the LLM state, and the metamodel,
catalogue and threshold-set versions. `/systems/{s}/services/{name}` returns
`assessment: {"available": false, "reason": ...}` until stage ④ ships a trained model.

**Why read-only.** A served number and a stored number that can disagree is a reproducibility hole,
and the pipeline stages have to stay usable with no server running.

**Why no assessment.** `api/README.md` requires that switching the LLM off leaves a working system.
The corollary nobody states is that switching the *model* off must also leave an honest one: an API
that invented a verdict from metrics alone would be exactly the unfalsifiable output the SLR
criticises. The explicit `available: false` is also the seam stage ④ plugs into.

**Consequence.** Undetermined metrics travel to the client as `value: null` plus a note, never as
`0`, so no consumer can accidentally render missing evidence as a clean bill of health.

---

## DD-008 — Synthetic supervision is admissible, with two guards · 2026-08-31

**Decision.** Architectural mutants labelled by construction are the first label source
(`docs/05-labels-and-datasets.md`), subject to two guards that are enforced in code, not by
convention:

1. **Circularity.** The deterministic detector of an injected property is excluded from the feature
   set for that task (`EXCLUDED_FEATURES` in `models/aam4j_models/dataset.py`), and the exclusion is
   written into every run record.
2. **Honest negatives.** A service that already exhibited the injected property in the base model is
   dropped rather than labelled, and a negative that could not be verified against a deterministic
   detector is marked `unverified negative` in the label file itself.

**Why both.** Either one alone still produces a defensible-looking number that means nothing: the
first guard stops the model from reading its own answer key, the second stops the label file from
asserting more than the operator guaranteed.

**Standing threat.** Mutants are not drawn from the distribution of real architectural decay.
Results transfer to "does the metric detect this property", never to "does this predict real-world
failure", and that sentence goes in threats to validity rather than waiting for a reviewer to say
it first.

---

## DD-009 — Train Ticket re-pinned to `master` · 2026-09-02

**Decision.** Reverses DD-003. Train Ticket is analysed at `master`,
`313886e99befb94be6cd45f085c98e0019f59829`, committed 2022-11-01.

**What forced it.** The AnoMod dataset (Ping et al., MSR 2026) is the current fault-injection
source for this benchmark, and its traces name `master`'s services. Measured with
`subjects/inspect_anomod.py` over the 13 Train Ticket runs:

| Pinned at | Traced services with a modelled element |
|---|---|
| `refactor/v2` | 24 / 35 (69%) |
| `master` | **35 / 35 (100%)** |

The eleven unmatched services under `refactor/v2` were not marginal: `ts-route-service` alone
carries 12,740 spans, `ts-order-other-service` 10,790. Thirteen `refactor/v2`-only services never
appeared in a trace at all. DD-003's own revisit clause named this exact condition, so the reversal
is the procedure working rather than a reconsideration.

**What it costs, and this is the uncomfortable half.** `master` is frozen: its head commit is from
**2022-11-01**. Trading an actively maintained branch for a four-year-old snapshot is a real loss,
and it is the reason DD-003 chose `refactor/v2` in the first place. Three consequences to state
rather than discover later:

1. Every finding about Train Ticket describes a 2022 system. Any claim about "current microservice
   practice" cannot lean on it.
2. The pinned code and the AnoMod traces are still not the same build. The dataset was collected in
   November 2025 from a deployment of `master`; we analyse `master`'s source. Service names join
   completely, which is what the metrics need, but this is version alignment, not identity, and it
   belongs in threats to validity.
3. Comparability with the SLR corpus improves, since the fault-diagnosis literature overwhelmingly
   uses `master`.

**Consequence for stored artifacts.** Every Train Ticket profile, model and label written before
this date describes a different snapshot and is not comparable with what follows. They were
regenerated rather than migrated. The counts moved accordingly: 42 functional services instead of
30, 262 endpoints instead of 219, and the `cycle` learning task gained a second system, so it can be
evaluated leave-one-system-out for the first time.

**When this should change.** If `refactor/v2` ever acquires a published fault-injection dataset of
its own, the argument reverses again and the maintained branch wins. The deciding question is always
the same one: where do the labels come from.
