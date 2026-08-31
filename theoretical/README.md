# theoretical/

The written half of the thesis: the systematic literature review, the research proposal, and the
full search and screening record behind them.

The SLR is not background reading for the artifact. It is what licenses it: each of the four gaps
it identifies is mapped to an objective, and each objective is a directory in
[`../practical/`](../practical/). If a gap moves, the artifact moves with it.

## Layout

| Path | What it is |
|---|---|
| `slr/SLR_Architecture_Aware_Metrics_v5.docx` | The current SLR draft |
| `slr/SLR_Architecture_Aware_Metrics_v5_highlighted.docx` | The same draft with the changes since v4 highlighted, for the supervisors |
| `slr/archive/` | Superseded drafts, kept so a claim can be traced to the version that made it |
| `slr/Search_URLs_and_Workflow.md` | The search protocol: the V3 string, one pre-filled URL per database, and the export-to-Mendeley routine |
| `slr/SLR_Search_Tracker.xlsx` | Per-database screening counts, phase by phase |
| `slr/search-results/` | The raw exports and the screening worksheets for phases 2 and 3 |
| `slr/references/` | Mendeley exports split per database, plus the duplicate report |
| `proposal/` | The research proposal submitted to DCTI |

## The review protocol, in short

- **Question.** How can architecture-aware metrics, computed over a representation that fuses static
  code, configuration and runtime evidence, support AI-assisted quality assessment of Java-based
  distributed systems, and be explained in terms a developer can act on.
- **Search string.** V3, language-agnostic, five required concept groups (metrics, distributed
  systems, observability, AI, architecture) with exclusion clauses for IoT, cyber-physical and
  biomedical domains. The exact string and the pre-filled URLs are in `slr/Search_URLs_and_Workflow.md`.
- **Window.** 2014-01-01 to 2026-05-01.
- **Databases.** ACM DL, IEEE Xplore, Scopus, SpringerLink, Web of Science, ScienceDirect, Wiley,
  MDPI. Exports are kept per database, never merged before deduplication, so a per-source count is
  always recoverable.
- **Screening.** Four phases. Phase 1 title and abstract, phase 2 pre-classification against the
  inclusion and exclusion criteria, phase 3 full-text decision with the EC3.x exclusion codes
  recorded per paper, phase 4 quality scoring (Dybå) on the survivors. Phase 3 closed on a corpus
  of **113 papers**, including 27 reached by snowballing.
- **Reproducibility.** Every phase's worksheet is in `slr/search-results/`, with the decision and
  its reason code per row. The intent is that a reader can re-run the search and land on the same
  corpus, which SLR §4.10 found only about 14% of that corpus itself allows.

## What the review concluded

Four gaps, and they are the reason the artifact has the shape it has:

| Gap | Finding | SLR section |
|---|---|---|
| G1 | No study in the 113-paper corpus combines all four evidence classes (code, configuration, metrics and logs, traces) into a single representation. They are consumed in isolation, by different tools. | §4.5 |
| G2 | Architecture-aware metrics exist informally across the corpus but are fragmented and never formally defined over one metamodel, so they are not comparable across studies. | §5.2 |
| G3 | Model-driven and metric-based approaches occupy mirror-image cells of the field: metamodel studies cover smells, security and documentation but never runtime concerns, and metric studies do the opposite. | §4.12 |
| G4 | At most 7.5% of the corpus offers any explainability provision, and none grounds its explanations in architectural entities. About 6% does any human-subject evaluation at all. | §4.9, §4.11 |

## Status

v5 is with the supervisors. `supervision/` holds the feedback thread and the mapping from each of
Vítor's comments to the section that answers it. That folder is intentionally not published: it is
correspondence, and none of it is needed to reproduce the review.

## Not in this repository

- The publisher's PDF of any third-party article. The corpus is identified by DOI in the exports
  under `slr/search-results/`; the PDFs themselves stay on the author's machine.
- The rendered audio summary of the SLR. The script that generates it and the narration script are
  tracked in `audio/`; the 25 MB render is not, since git keeps binaries forever and the render is
  reproducible from the two tracked files.
