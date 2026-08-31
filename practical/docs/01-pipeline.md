# The pipeline

Derived from the SLR. Each stage names the gap it closes and the SLR section that justifies it.

```
  Java source        config / deploy        runtime telemetry
  (.java, POMs)      (application.yml,      (Prometheus metrics,
       │              Dockerfile, k8s)       Zipkin/Jaeger traces, logs)
       └──────────────────┬──────────────────┘
                          ▼
   ① EXTRACTION ......... extractor/          parse → normalise → correlate
                          ▼
   ② ARCHITECTURAL MODEL  metamodel/          one Ecore instance per system per snapshot   [G1]
                          ▼
   ③ METRIC COMPUTATION   metrics/            OCL-defined metrics over the model           [G2]
                          ▼   metric profile (per service / per edge / per system)
   ④ HYBRID MODEL ....... models/             interpretable-by-design metric+AI            [G3]
                          ▼   prediction + attribution + counterfactual
   ⑤ EXPLANATION ........ models/explain/     attribution → architectural elements
                          ▼   structured rationale (never free text at this point)
   ⑥ DELIVERY ........... api/                REST + JSON/CSV export + CI dashboard        [G4]
                          ▼   optional LLM verbalisation layer (T0/T1/T2 — SLR §5.4)
                     developer / architect
```

## Why this shape

SLR §4.5 found that **no study in the 113-paper corpus combines all four evidence classes** (code,
configuration, metrics/logs, traces) into one representation — they are consumed in isolation by
different tools. Stage ① is therefore the first contribution, and it is only meaningful because
stage ② gives the fused evidence somewhere to live.

SLR §4.12's heat-map showed model-driven approaches and metric-based approaches occupying
*mirror-image* cells: metamodel studies cover smells/security/documentation but never runtime
concerns, and metric studies do the opposite. Stages ②→④ are the bridge between those two halves.

SLR §4.11 measured that ≤7.5% of the corpus offers any explainability provision and that none
grounds explanations in architectural entities. Stage ⑤ is the thesis' clearest original
contribution, and its feasibility depends entirely on stage ③ producing features that *are*
architectural elements rather than opaque embeddings.

## Data contracts between stages

Freeze these early; they are what lets stages be developed and versioned independently.

| Boundary | Artifact | Format | Notes |
|---|---|---|---|
| ①→② | extraction bundle | JSON | Raw parsed facts, pre-fusion. One file per evidence class. |
| ②→③ | architecture model | `.xmi` (Ecore instance) | Versioned against the metamodel version. |
| ③→④ | metric profile | Parquet + CSV | Long format: `(system, snapshot, element_id, element_kind, metric, value)`. |
| ④→⑤ | prediction record | JSON | `prediction`, `attributions[]`, each attribution referencing a `metric` and `element_id`. |
| ⑤→⑥ | structured rationale | JSON | Verdict, contributing metrics, implicated elements, counterfactual. Renderable without an LLM. |

The `element_id` must be stable across snapshots of the same system, otherwise nothing downstream
can be tracked over time. Decide the identity scheme (fully-qualified service name + role?) before
writing the extractor — it is the single most expensive thing to change later.

## Non-negotiable design constraints (from the SLR)

1. **Interpretable-by-design, not post-hoc.** Model families are chosen so that decisions decompose
   over inputs (regularised linear, gradient-boosted trees + SHAP over *metric* features, rule
   learners). Deep baselines are trained only to quantify the accuracy cost of interpretability,
   and that cost gets reported, not hidden. (SLR §5.3)
2. **Every attribution resolves to an architectural element.** If a feature cannot be traced back to
   a service, dependency edge, endpoint or deployment unit, it does not belong in the feature set.
3. **The LLM never originates an assessment.** It sits downstream of stage ⑤ and only verbalises an
   already-computed rationale, under the T0/T1/T2 trust levels and the grounding / consistency /
   contradiction checks of SLR §5.4. Template-based explanation must remain a working fallback with
   the LLM switched off entirely.
4. **Everything is versioned.** Metamodel version, metric catalogue version, model version and LLM
   version are recorded in every output record. SLR §5.4 requires this for reproducibility.

## Evaluation plan (Obj. 5)

Two distinct evaluations, frequently conflated — keep them apart:

- **Technical:** predictive performance on the labels of `docs/05-labels-and-datasets.md`, plus the
  pattern regression suite of `docs/04-pattern-catalogue.md` (does the tool detect a known
  anti-pattern in a system where we know it is present?).
- **Human:** developer study measuring comprehension, actionability, trust calibration and
  time-to-decision against a no-explanation baseline (SLR §5.3). SLR §4.9 found only ~6% of the
  corpus does any human-subject evaluation — this is where G4 is actually closed.
