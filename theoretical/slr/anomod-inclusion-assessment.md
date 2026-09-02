# Should AnoMod be in the SLR corpus?

Assessed 2026-09-02, after the dataset was adopted as the source of runtime evidence for the
artifact (`practical/docs/07-positioning-and-runtime-evidence.md`).

> Ping, K., Bin Mazhar, H., Wang, Y., Song, Y., Mäntylä, M. V. (2026). *AnoMod: A Dataset for
> Anomaly Detection and Root Cause Analysis in Microservice Systems.* MSR '26.
> [doi:10.1145/3793302.3793324](https://doi.org/10.1145/3793302.3793324)

The instinct to include it is right, and the answer is still probably "not in the corpus". The two
are not in conflict, because a paper can be cited in three different roles and only one of them is
corpus membership.

## 1. It passes the Phase 2 criteria, and comfortably

Scored against the operationalised protocol in `search-results/phase2_preclassification.xlsx`,
sheet *Criteria (for §3.2.6)*, using title and abstract only, as that protocol specifies.

| Block | Hit | Evidence in the abstract |
|---|---|---|
| **A** Architecture | yes | "a predominant **architectural** style for cloud services" |
| **D** Domain | yes | "**microservice** systems (MSS)", "cloud services" |
| **M** Metrics | yes | "we collect five modalities: logs, **metrics**, distributed traces …" |
| **O** Observability | yes | "**anomaly detection** (AD) and **root cause analysis** (RCA)", "**logs**", "distributed **traces**", "**monitoring** modalities" |
| **L** AI/ML | **no** | none of machine learning, artificial intelligence, AI, deep learning, neural, GNN, LLM, classifier, clustering, model-driven, metamodel, OCL appears in title or abstract |

Block score **s = 4** of 5. Domain match **d = TRUE**. Out-of-scope flag **x = FALSE**.

By the decision rule (`EXC if x`, `EXC if not d`, `EXC if s ≤ 1`, `BORDERLINE if s = 2`,
`INC otherwise`) the verdict is **INC**. STAR score t = 0, so it is a plain include, not a star.

Excluding it on scope grounds would therefore be inconsistent with how the other 113 papers were
treated. That has to be said plainly, because it is the argument *for* inclusion and it is a good
one.

## 2. But it was never retrieved by the search, and that is the real problem

The V3 string requires a hit in **all five** concept groups. On title and abstract, AnoMod misses
the AI/ML group entirely: the closest it comes is "cross-modal anomaly detection and
fusion/ablation strategies", and none of those are listed terms. It would be retrieved only by a
database matching on full text, where "machine learning" almost certainly occurs in the related
work.

There is a second possible reason: timing. The search window closes 2026-05-01 and the Mendeley
export is dated 2026-05-24. The arXiv preprint is 2026-01-30 and the MSR '26 proceedings are later,
so the paper may simply not have been indexed in the queried databases when the searches ran.

Either way, **the paper did not come out of the documented process**. It was found by a targeted
search for current fault-injection datasets, which is a different activity. Inserting it into the
corpus without saying how it got there is exactly what makes a systematic review criticisable, and
it would not survive a careful reader comparing the corpus against the reported protocol.

Calling it snowballing would be false: snowballing means following references of included papers,
and this was not that.

## 3. The Phase 3 question that decides it

Phase 3's inclusion criterion IC3.1 asks **which research questions the paper addresses**. AnoMod
addresses none of RQ1 to RQ4. It is a dataset paper: it does not propose an architectural
representation, does not define metrics, does not build a model, and does not explain anything to a
developer. It *enables* work on RQ3 rather than answering it.

Also worth checking against EC3.2 (short paper or extended abstract): MSR's Data and Tool Showcase
track runs to a handful of pages, and the criterion is stated as "< 2000 words".

A corpus whose members are supposed to answer the review's questions is weakened, not strengthened,
by admitting a paper that answers none of them.

## 4. Recommendation: cite it three times, in three roles, and keep it out of the corpus

1. **In the SLR discussion, as third-party corroboration of G1.** AnoMod's own motivation is that
   existing benchmarks "emphasize performance-related faults and provide only one or two monitoring
   modalities, limiting research on broader failure modes and cross-modal methods". That is an
   independent 2026 statement of the fusion gap the review claims from its own corpus analysis, made
   by authors with no stake in this thesis. Discussion and related-work citations do not have to be
   corpus members, and this is the strongest available use of the paper.
2. **In the SLR's threats to validity, as a named example of search-string sensitivity.** A paper
   that scores 4 of 5 concept blocks and was not retrieved is evidence about the string, not about
   the paper. Reporting it converts a weakness into a demonstration of rigour. State which group it
   missed and why.
3. **In the artifact methodology, as the data source.** This needs no change to the review at all
   and is how empirical datasets are normally cited.

**If the corpus is to include it anyway**, the only honest channel is a documented **search
update**: re-run the V3 string on the same databases with the window extended, record the date, the
counts and the delta, and let AnoMod enter as an ordinary Phase 2 and Phase 3 candidate alongside
whatever else two months of publishing produced. That is defensible. Adding one paper by hand,
because it turned out to be useful, is not.

## 5. One thing to declare either way

The dataset is about to become the evaluation input for the artifact. If its paper also joins the
corpus that justifies the artifact, that dual role should be stated once, explicitly, wherever the
corpus is described. It is not disqualifying. Leaving a reader to notice it unaided is the problem.
