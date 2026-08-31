# extractor/ — Obj. 3 / T4 · RQ1

Builds metamodel instances from real systems with minimal manual intervention.

**In:** a subject system checkout + (optionally) a telemetry capture
**Out:** extraction bundles (JSON) → consumed by `metamodel/`

## Four evidence classes

| Class | Source | Notes |
|---|---|---|
| Static | `.java`, POMs, annotations | Spoon / JavaParser / Eclipse JDT. Also computes CK OO metrics for the RQ2 comparison arm. |
| Configuration | `application.yml`, Spring config, Dockerfiles, k8s manifests, compose files | Where endpoints and deployment topology actually live |
| Metrics/logs | Prometheus, application logs | PetClinic and Train Ticket ship stacks; TeaStore uses Kieker |
| Traces | Zipkin / Jaeger | The only source for the whole communication-complexity metric group |

SLR §4.5: no study in the 113-paper corpus combines all four. Doing so is the first contribution —
which also means there is no prior art to copy the fusion logic from.

## Design constraints

- Do not assume Spring Boot. TeaStore is in the subject set specifically to break that assumption.
- Declared and observed dependencies are recorded **separately**, never merged silently. Their
  disagreement is a finding, not noise.
- Extraction must be re-runnable and deterministic given the same commit SHA and telemetry capture.
