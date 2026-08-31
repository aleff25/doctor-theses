# Reference pattern catalogue

Source: supervisor meeting 09/07/2026, item 9 → SLR §5.4 and future-work item 6 of §6.2.

The idea agreed with the supervisors: curate ~10 well-known architectural patterns and
anti-patterns, instantiate each in a reference system **where the correct assessment is known in
advance**, and use that as ground truth. This turns an open-ended generation problem into a
verifiable classification-and-explanation problem, and doubles as the regression suite that gates
every release of the tool and every LLM version change.

## The ten

| # | Pattern | Type | Expected detection route | Likely host |
|---|---|---|---|---|
| 1 | God service / central bottleneck | anti-pattern | `GOD`, `BTW` | Train Ticket |
| 2 | Chatty communication | anti-pattern | `CHAT`, `CPL` | Train Ticket |
| 3 | Cyclic service dependencies | anti-pattern | `CYC` | to be located |
| 4 | Shared database | anti-pattern | `SHARED_DB` | to be located / injected |
| 5 | API gateway | pattern | edge topology + config | PetClinic |
| 6 | Database per service | pattern | `P(s)` disjointness | PetClinic |
| 7 | Circuit breaker | pattern | static (annotations/config) | PetClinic, Train Ticket |
| 8 | Saga / distributed transaction | pattern | trace topology | Train Ticket |
| 9 | Event sourcing | pattern | async edges + store shape | to be located |
| 10 | Strangler fig | pattern | requires two snapshots | synthetic |

## Open decisions (flagged as pending in `../reuniao_orientadores_09_07_2026.md`)

These three were listed as pending actions after the 09/07 meeting and are still open:

1. **Confirm the final ten with the supervisors.** The list above is the SLR §5.4 candidate set;
   it has not been ratified.
2. **Choose the reference system for each.** Several entries above say "to be located" — patterns 3,
   4 and 9 may not occur naturally in the three subject systems. Two honest options: find a fourth
   system that exhibits them, or *inject* them deliberately into a fork of PetClinic and document
   the injection. Injection is defensible and common in this literature, but it must be declared as
   such — a detected smell that you planted is evidence about the detector, not about the wild.
3. **A vacuous pass must not look like a pass.** A predicate that is satisfied because it had *no
   elements to range over* is indistinguishable, in a green test run, from one that genuinely holds.
   Concrete case: if PetClinic's embedded in-memory databases are not modelled as store elements at
   all, then `SHARED_DB` finds no shared store, pattern 6 (database-per-service) reports **pass**,
   and the harness is testing nothing — on the control system chosen precisely because its ground
   truth is known. Silent, and worse than a false positive.

   Every case must therefore report its **support**: how many elements the predicate ranged over. A
   case with zero support is `INCONCLUSIVE`, never `PASS`, and inconclusive cases fail the suite
   until the extractor is fixed or the case is deliberately retired. This is also a requirement on
   DD-001 — store identity must be defined *downward* far enough to cover embedded stores, not only
   to distinguish container from schema.

4. **Define the acceptance metric.** What counts as a correct answer? Proposal: three levels, scored
   separately — (a) the pattern is detected at all, (b) the implicated services are exactly right,
   (c) the explanation names the right metrics. Level (c) is the one that actually tests the
   explanation layer, and it is the one that will be hardest to grade objectively. Consider a
   rubric with two independent raters and a kappa, mirroring §3.2.9 of the SLR.

Pattern 10 (strangler fig) is a process, not a static structure — it can only be detected by
comparing two snapshots of the same system over time. Either build a synthetic two-snapshot case or
drop it from the suite; do not leave it in as an entry the harness silently never exercises.

## Use as a regression harness

Per SLR §5.4, this catalogue gates releases:

- every release of the tool runs the full suite
- every change of LLM version runs the full suite before adoption
- results are published with the tool documentation, so users can see what it was verified against

Structure the suite so that a case is `(model instance, expected verdict, expected implicated
elements, expected metrics cited)`. Store the model instances, not just the source systems —
re-deriving a model from source on every CI run makes the suite slow and makes failures ambiguous
between "the extractor changed" and "the detector changed".
