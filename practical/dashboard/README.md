# dashboard/ — reading the results

A React application over what the pipeline stored. It computes nothing: every number, note and
version stamp on the page comes out of `data/`, so the dashboard and the API cannot disagree with
each other or with the stored profile.

```bash
# 1. the pipeline must have run at least once (see ../README.md)
../.venv/bin/python build_dashboard_data.py      # writes public/dashboard.json

# 2. the app
npm install
npm run dev                                      # http://localhost:5173
npm run build && npm run preview                 # production build, served locally
npm run standalone                               # one self-contained .html file
```

### Which build to use

`npm run build` emits `dist/`, which **needs a server**. Opening `dist/index.html` by double-click
does not work, and the browser console says so in an alarming way:

```
Access to script at 'file:///.../assets/index-*.js' from origin 'null'
has been blocked by CORS policy
```

That is not a bug in the build. A page loaded over `file://` has the opaque origin `null`, and
Chrome blocks cross-origin module scripts, stylesheets and `fetch()` from there. `npm run preview`
serves `dist/` over http and it works.

`npm run standalone` is for the case where a server is not wanted: it inlines the CSS, the module
script and the data into `dist-standalone/aam4j-dashboard.html`, about 800 KB, which opens by
double-click on any machine with a browser and no toolchain at all. Inlining removes the fetches
rather than working around the rule, so nothing is being bypassed. That is the form to hand a
supervisor or attach to an email.

## What each view is for

| View | What it answers |
|---|---|
| Overview | What was measured, and the one constraint that limits every number on the other pages |
| Systems | Per service: role, metric profile, and **the source code behind each number**. Open a service, then a dependency, an endpoint or an entity inside it |
| Metrics | The catalogue as a glossary: formula, interpretation, hypothesised effect, limitation, references, plus the observed range across all three systems |
| Rules | Every design decision and standing practice, each with its cost and the condition under which it should be reopened |
| Learning | The mutation-based supervision, the leave-one-system-out folds, and the exact attributions behind individual predictions |

Hovering any metric badge, anywhere in the app, shows that metric's definition, formula and what a
high value means, plus the note recorded for that specific element.

## The generator

`build_dashboard_data.py` reads `data/`, the catalogue files and the prose in `content/`, then
opens the pinned clones under `subjects/` to lift the source lines around every fact the extractor
recorded. That is what lets a card answer "why does this service have AIS = 1" with the Java
statement that created the edge rather than with a number.

Two invariants are enforced there rather than assumed, so the dashboard cannot drift away from the
code:

1. every metric in `aam4j_metrics.catalogue.METRICS` must have an entry in `content/metrics.json`,
   so adding a metric without documenting it fails the build;
2. every reference key used by a metric or a rule must exist in `content/references.json`, so a
   dangling citation fails the build.

Missing clones are not an error: snippets degrade to file and line, which is still enough to find
the code by hand.

## content/

Prose, versioned as data rather than embedded in components.

| File | Holds |
|---|---|
| `metrics.json` | one entry per catalogued metric, plus the ten documented as absent and why |
| `rules.json` | the DD-00x design decisions and the P-x standing practices, each with decision, why, cost, and when to revisit |
| `references.json` | the bibliography, each entry with a note saying what it is cited **for** |

Every reference was checked against Crossref or the publisher before it was written down. Where a
paper could not be verified directly (Rud et al. 2006 is behind a proceedings paywall), the entry
says which secondary source confirms the attribution.

## Deliberately not here

- **No verdicts.** There is no trained quality model, so the dashboard shows measurements and their
  evidence, never an assessment. DD-007 is the same decision on the API side.
- **No averaging across folds.** With three systems and single-digit positives, a headline number
  would flatter the result into meaninglessness. Each fold is shown against its own majority-class
  rate.
- **No chart of the service graph.** With 2 edges across 47 functional services, a graph drawing
  would be a picture of the extractor's coverage rather than of any architecture. It becomes worth
  drawing when the JVM analyser lands.
