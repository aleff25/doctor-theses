# Subject systems

Three open-source Java microservice systems. Verified 2026-08-17: all three are Java, Apache-2.0,
and not archived.

## Selection criteria

The SLR constrains this choice more than it might appear:

- **Java/JVM** — SLR §4.8 found only 5 of 113 studies target Java explicitly. Java focus *is* the
  positioning of the thesis, so subject systems that are polyglot-by-design (Sock Shop, Online
  Boutique, DeathStarBench) would dilute exactly the differentiator being claimed.
- **Genuinely microservice, not a modular monolith** — RQ1 needs real inter-service communication,
  independent deployment units, and a deployment topology to model.
- **Observable** — RQ1's metamodel fuses static + configuration + *runtime* evidence. A system with
  no telemetry story can only exercise two thirds of the pipeline.
- **Distinct label sources** — RQ3 needs quality outcomes to predict. One system cannot supply
  defect, performance and fault labels credibly, so the three are chosen to divide that work.
- **Scale spread** — metrics that behave sensibly on 8 services and collapse on 47 are not metrics.

## The three

### 1. Spring PetClinic Microservices — *the reference system*

`https://github.com/spring-petclinic/spring-petclinic-microservices` · Apache-2.0 · `main`

8 Maven modules: `customers-service`, `vets-service`, `visits-service` (appointments),
`api-gateway`, `config-server`, `discovery-server` (Eureka), `admin-server`, `genai-service`.
Ships with Docker Compose plus Prometheus, Grafana and Zipkin already wired.

This is the "vet / appointment" system, and it is the control case. Small enough to build the
ground truth by hand: you can read all 8 services in an afternoon and state with confidence which
architectural patterns are present, which makes it the natural home for the pattern catalogue of
`04-pattern-catalogue.md`. It also exhibits textbook instances of several catalogue entries
out of the box — API gateway, service discovery, database-per-service, config server.

Caveats: it is a *demo*, so its git history reflects tutorial maintenance rather than production
defect pressure; do not lean on it for defect labels. The `genai-service` module is a recent
addition and worth checking before including it in a snapshot — it may skew the AI-related facets.

### 2. FudanSELab Train Ticket — *the scale and fault-ground-truth system*

`https://github.com/FudanSELab/train-ticket` · Apache-2.0 · `master`

47 `ts-*` modules (one of which, `ts-common`, is a shared library, not a service — the extractor
must not count it as one). Mostly Java/Spring Boot with a few non-Java components.

> **Branch decision — REVERSED 2026-09-02: `master` (DD-009).**
>
> It was pinned to `refactor/v2` on 2026-08-17 by candidate decision, because `master` HEAD is
> frozen at 2022-11-01 while `refactor/v2` was still moving (last commit 2025-11-21). The third
> bullet of that decision said the fault-injection labels had to be re-verified against v2, and that
> if they did not port, the decision had to be revisited. They did not port.
>
> The AnoMod dataset (Ping et al., MSR 2026), which is the current fault-injection source for this
> benchmark, names `master`'s services. Measured over its 13 Train Ticket runs: **35 of 35** traced
> services have an element in the model when pinned to `master`, against **24 of 35** on
> `refactor/v2`. Eleven high-traffic services, `ts-route-service` among them with 12,740 spans, had
> nowhere to attach.
>
> What the reversal costs, and it is not small:
>
> - **The pinned snapshot is from 2022-11-01.** Every Train Ticket finding now describes a
>   four-year-old system, and no claim about current microservice practice can lean on it.
> - **The pinned source and the traces are still different builds.** AnoMod was collected in
>   November 2025 from a deployment of `master`; we analyse `master`'s source. The names join
>   completely, which is what the metrics need, but that is version alignment and not identity.
>   It belongs in threats to validity.
>
> What it buys: the label source, and like-for-like comparability with the SLR-corpus studies, which
> overwhelmingly evaluate on `master`. Figures quoting "41 / 47 microservices" from the literature
> now refer to the same branch this thesis analyses.
>
> `master` being frozen has one advantage worth naming: re-running `--update` cannot move it.

This is the de facto benchmark of the microservice fault-analysis literature, and several studies
in the SLR corpus evaluate on it. Two consequences: the thesis gets **comparability** with existing
work almost for free, and it gets **labelled faults** — the project publishes fault-injection
scenarios with known root causes, which is exactly the supervision signal RQ3 needs and which the
SLR (§4.9) found most studies lack.

At 47 modules it is also the scalability test for the extractor and for the graph-based metrics
(centrality over a 47-node service graph is a different proposition from an 8-node one).

Caveats: heavier to stand up than PetClinic; budget real time for the deployment. Verify which
fault-injection dataset version is current before committing to it as the label source.

### 3. Descartes TeaStore — *the performance and model-extraction system*

`https://github.com/DescartesResearch/TeaStore` · Apache-2.0 · `master`

5 services (WebUI, Auth, Persistence, Recommender, Image Provider) plus a registry, under
`services/`, with `interfaces/`, `utilities/` and `e2e-tests/`.

TeaStore was built by a research group explicitly as a reference application for **model extraction**
and performance/energy prediction, and ships with Kieker instrumentation. That makes it the natural
validation case for RQ1: if the metamodel cannot represent a system that was *designed* to be
model-extracted, the metamodel is wrong. It also supplies performance and energy labels under
controlled load, which neither of the other two does well.

Caveats: smallest service count and the least "modern cloud-native" of the three (Tomcat/WAR-based
rather than Spring Boot), so it stresses the *technology-agnostic* claim of RQ1 — which is a feature
for the thesis, but means the extractor cannot assume Spring Boot conventions everywhere.

## Deliberate alternate

**sqshq/PiggyMetrics** (`https://github.com/sqshq/piggymetrics`, MIT, ~14k stars) — Spring Boot +
Spring Cloud, financial domain, the most-starred Java microservice reference app. Swap it in if one
of the three proves impractical, or add it as a fourth if a non-demo domain is wanted. It was left
out of the core three because it has no observability stack and was last pushed in 2024, so it
would exercise only the static + configuration half of the pipeline.

## Fetching

```sh
./subjects/fetch_subjects.sh
```

Clones all three under `subjects/` and writes `subjects/subjects.lock.json` with the resolved commit
SHA of each. **Cite those SHAs in the thesis**, not branch names — `main` will have moved by the
time anyone tries to replicate, and reproducibility of the subject systems is exactly the weakness
the SLR (§4.10) identified in the corpus.

Re-run with `--update` to refresh and re-pin. The clones are gitignored; the lockfile is not.

## Verified state (fetched 2026-08-17)

| System | Commit | Commit date | Confirmed structure |
|---|---|---|---|
| petclinic | `305a1f13` | 2026-05-17 | 8 `spring-petclinic-*` modules |
| trainticket | `313886e9` | 2022-11-01 | 47 `ts-*` modules on `master` (incl. `ts-common` — a library, not a service). 42 classified functional, 262 endpoints, 26 entities |
| teastore | `34b37f7e` | 2025-01-08 | 6 services under `services/` (auth, image, persistence, recommender, registry, webui) |

TeaStore has a `registry` service in addition to the five functional ones — the extractor should
treat registry/discovery components as infrastructure, consistent with how `discovery-server` and
`config-server` are treated in PetClinic. Decide once whether infrastructure services count as nodes
in `G` for the centrality metrics; they will dominate `AIS` if included, and the answer should be
recorded in the metric catalogue rather than left implicit in code.
