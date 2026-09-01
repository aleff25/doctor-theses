# Doctor Theses

PhD, Iscte-IUL, ISTA/DCTI.

**Architecture-Aware Software Metrics for AI-Supported Quality Assessment in Java-Based Distributed
Systems**

Candidate: Aleff Rodrigues Mendes de Oliveira.
Supervisors: José Vicente Pereira dos Reis, Vítor Manuel Bastos.

## The two tracks

| Folder | What it holds | Start here |
|---|---|---|
| [`theoretical/`](theoretical/) | The systematic literature review, the research proposal, the search protocol and the screening record | [`theoretical/README.md`](theoretical/README.md) |
| [`practical/`](practical/) | The software artifact: extraction, architectural metamodel, metric catalogue, hybrid models, delivery API | [`practical/README.md`](practical/README.md) |

They are one argument in two halves. The SLR screened 113 papers and closed on four gaps in the
literature; every directory in `practical/` exists because one of those gaps says something is
missing. Nothing is in the artifact "because a project usually has one".

| Gap | What the literature is missing | Where it is closed |
|---|---|---|
| G1 | No study fuses code, configuration, metrics/logs and traces into one representation | `practical/metamodel/` |
| G2 | Architecture-aware metrics are fragmented and informally defined | `practical/metrics/` |
| G3 | Metric-based and model-driven approaches occupy mirror-image halves of the field and never meet | `practical/models/` |
| G4 | Explanations are rare, and none are grounded in architectural entities | `practical/api/` |

The dependency chain is strict: G1 to G2 to G3 to G4. A downstream stage does not start before its
upstream stage has a frozen version.

## Reproducing the artifact

Everything needed to run the pipeline on any machine is in
[`practical/README.md`](practical/README.md#running-it-on-any-machine), including the React
dashboard that renders the results with the source code behind each number. Stages 1 to 3 need Python,
git and a single third-party package (PyYAML); the API and the learning baseline are optional
extras.

## What is deliberately not in this repository

- **Publisher PDFs of third-party articles.** The thesis cites DOIs. Redistributing a publisher's
  typeset PDF is the publisher's right, not the author's.
- **Correspondence with the supervisors.** Third-party material, and not needed by anyone
  reproducing the work.
- **The subject systems.** Spring PetClinic, Train Ticket and TeaStore are cloned by
  `practical/subjects/fetch_subjects.sh` at the exact commits recorded in `subjects.lock.json`,
  rather than vendored into this history.
- **Generated data.** Everything under `practical/data/` is reproducible by re-running the
  pipeline, byte for byte, from the pinned commits.

## Status

The SLR is at v5 and under supervisor review. The artifact runs end to end on three subject systems:
extraction, architectural model, twelve metrics, synthetic supervision, a first interpretable
baseline, and a deterministic API. The binding constraint on everything downstream is the static
analyser, which is documented openly in `practical/README.md` rather than left for a reader to
discover.

## Citing this work

Not yet published. Until then, cite the thesis proposal in `theoretical/proposal/` and reference
this repository by commit SHA, since the artifact's outputs are reproducible only against a pinned
version of the metamodel and the metric catalogue.
