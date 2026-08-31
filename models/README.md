# models/ — Obj. 4 / T5 · gap G3 · RQ3

Hybrid metric+AI quality models, and the explanation layer.

**In:** metric profiles from `metrics/` + labels from `data/labels/`
**Out:** prediction records — `prediction`, `attributions[]`, each attribution naming a metric and
an `element_id` — then structured rationales for `api/`

## Interpretable-by-design (SLR §5.3)

Primary families: regularised linear models, gradient-boosted trees with SHAP over **metric**
features, rule learners. Deep baselines are trained **only** to quantify the accuracy cost of
interpretability, and that cost is reported explicitly.

The rule that decides feature-set membership: *if a feature cannot be traced back to a service,
dependency edge, endpoint or deployment unit, it does not belong here.* Embedding dimensions and
raw telemetry counters fail this test — that failure is precisely the gap G3 the thesis closes.

## Explanation chain

`quality risk → contributing metrics → concrete services / dependencies / configurations`

Plus counterfactuals: the smallest metric change that would bring predicted risk below threshold,
translated into a candidate refactoring (reduce fan-in of a god service, split a chatty path).

Everything in this directory produces **structured** rationale. Natural language happens in `api/`,
downstream, and only as verbalisation of what was computed here.

## Splitting

Leave-one-system-out is the headline number. Never split randomly by row — see
`docs/05-labels-and-datasets.md`.

---

## Implemented today

| File | Purpose |
|---|---|
| `aam4j_models/mutate.py` | three architectural mutation operators, labelling by construction (DD-008) |
| `aam4j_models/dataset.py` | the 3 -> 4 join: wide feature table, leave-one-system-out splitter, per-fold imputation |
| `build_dataset.py` | generates the mutants, their metric profiles, the label file and the per-task datasets |
| `train_baseline.py` | L2-regularised logistic baseline, leave-one-system-out, exact attributions |

```bash
./.venv/bin/python models/build_dataset.py
./.venv/bin/python models/train_baseline.py --task oversized-service
```

Why logistic regression first: its attribution is exact. The contribution of a feature to a
decision is `coef_j * z_j`, not an estimate of it, so the 4 -> 5 contract is satisfied with no SHAP,
no sampling, and no approximation error to report separately. Gradient-boosted trees with SHAP are
the next arm, and the deep baseline exists only to price the interpretability, as above.

Three rules are enforced in `dataset.py` rather than left to whoever writes a training script:
never split randomly by row, never impute an undetermined metric as zero (median of the *training*
fold, plus an explicit `<metric>__undetermined` indicator), and never let a task keep the
deterministic detector of the property it is predicting.

**Read the current numbers as a wiring test.** The labels are synthetic, only `oversized-service`
has labels in more than one system, and the positives are single digits. What the run demonstrates
is that the chain from extraction to attribution holds together, not that anything predicts quality.
