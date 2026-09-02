# data/external/ — third-party datasets

Downloaded, not produced by this pipeline, and never committed. Each entry below carries the exact
provenance so the directory can be rebuilt from nothing.

## anomod/

> Ping, K., Bin Mazhar, H., Wang, Y., Song, Y., Mäntylä, M. V. (2026). *AnoMod: A Dataset for
> Anomaly Detection and Root Cause Analysis in Microservice Systems.* MSR '26.
> Paper [doi:10.1145/3793302.3793324](https://doi.org/10.1145/3793302.3793324) ·
> Data [doi:10.5281/zenodo.18342898](https://doi.org/10.5281/zenodo.18342898) · **CC-BY-4.0**

```bash
# 202 MB archive, about 3 GB extracted
curl -L -o AnoMod.zip https://zenodo.org/records/18342898/files/AnoMod.zip
unzip AnoMod.zip -d data/external/ && mv data/external/AnoMod data/external/anomod
python subjects/inspect_anomod.py data/external/anomod
```

**Layout.** `TT_data/` (Train Ticket) and `SN_data/` (SocialNetwork), each split into
`trace_data/`, `log_data/`, `metric_data/`, `api_responses/`, `coverage_data/` and
`coverage_report/`. Thirteen Train Ticket runs: one `Normal_case_*` and twelve injected faults named
by level, `Lv_P_` performance, `Lv_S_` service, `Lv_D_` database, `Lv_C_` code.

**Traces are Apache SkyWalking exports**, not Zipkin or Jaeger. Each file is a single JSON document
with `metadata.services_discovered` and a `traces[]` array; every span carries `service_code`,
`parent_node_id`, `children_node_ids`, `depth`, timing and an error flag. A parent-to-child pair of
`service_code` values is an observed dependency; the span tree gives call path length and fan-out.

**Attribution is required by the licence.** Any figure, table or number derived from this data cites
the paper above.

**Known join limitation.** 35 Train Ticket services appear in the traces. They match `master`
completely (35/35) and the pinned `refactor/v2` only partly (24/35). See
`docs/07-positioning-and-runtime-evidence.md`.
