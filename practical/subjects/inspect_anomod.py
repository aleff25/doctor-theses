#!/usr/bin/env python3
"""Answer one question about the AnoMod dataset: does it join with our model?

    python subjects/inspect_anomod.py ~/Downloads/AnoMod.zip
    python subjects/inspect_anomod.py /path/to/extracted/AnoMod

`docs/07-positioning-and-runtime-evidence.md` argues that observed evidence is
what distinguishes this artifact from the tools on the market, and that AnoMod
(Ping et al., MSR 2026) is the fastest route to it. It also says that nothing
should be built before one measurement is made: **which service names actually
appear in the traces**, and how many of them have an element in the architecture
model this pipeline already builds.

That is all this script does. It reads, it counts, it joins, and it writes
nothing. It is deliberately not part of the pipeline: it is the evidence for a
decision (re-pin Train Ticket to the dataset's branch, keep `refactor/v2` with
recorded gaps, or drop the route), and once the decision is recorded as a design
decision the script has done its job.

## Why it sniffs rather than assumes

The archive's internal layout is not documented outside the paper, and trace
exports come in at least three shapes that all encode the same thing:

    Zipkin      [{"traceId":..., "localEndpoint":{"serviceName":"ts-x"}}, ...]
    Jaeger      {"data":[{"processes":{"p1":{"serviceName":"ts-x"}}}]}
    OTLP/JSON   resourceSpans[].resource.attributes[service.name]

Rather than commit to one, the scan looks for the service-name keys those
formats share, over any JSON, NDJSON or CSV it finds. A regex scan is used
instead of parsing, because a 63,975-trace export can be a single multi-hundred-
megabyte document and the question here does not need the structure, only the
names. Anything it cannot read is reported rather than skipped silently.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: The keys the three common trace exports use for a service name, plus the
#: column name a flattened CSV export usually carries.
NAME_PATTERNS = [
    re.compile(rb'"serviceName"\s*:\s*"([^"]{1,120})"'),
    # OTLP puts the name two levels down from the key, so the pattern has to
    # reach across a little JSON rather than sit next to it.
    re.compile(rb'"service\.name".{0,80}?"stringValue"\s*:\s*"([^"]{1,120})"', re.DOTALL),
    re.compile(rb'"service_name"\s*:\s*"([^"]{1,120})"'),
    # SkyWalking, which is what AnoMod actually exports. Its spans carry
    # `service_code`, and each file also lists `services_discovered` and, per
    # trace, `services_involved`.
    re.compile(rb'"service_code"\s*:\s*"([^"]{1,120})"'),
]

#: Arrays of bare service names that some exports carry alongside the spans.
NAME_ARRAY_KEYS = (b"services_discovered", b"services_involved")
ARRAY_PATTERN = re.compile(
    rb'"(?:' + b"|".join(NAME_ARRAY_KEYS) + rb')"\s*:\s*\[([^\]]{0,20000})\]'
)
ARRAY_ITEM = re.compile(rb'"([^"]{1,120})"')

TEXT_SUFFIXES = (".json", ".ndjson", ".jsonl", ".csv", ".tsv", ".log", ".txt")
SCAN_BUDGET = 64 * 1024 * 1024  # per file; the names repeat, the tail adds nothing


def pinned_snapshot(system: str = "trainticket") -> tuple[str, str]:
    with open(os.path.join(ROOT, "subjects", "subjects.lock.json"), encoding="utf-8") as handle:
        lock = json.load(handle)
    for subject in lock["subjects"]:
        if subject["name"] == system:
            return subject["commit"], subject.get("branch", "")
    raise SystemExit(f"{system!r} is not pinned in subjects.lock.json")


def modelled_services(system: str = "trainticket") -> dict[str, str]:
    """`{service name: role}` from the stored architecture model."""
    commit, _ = pinned_snapshot(system)
    path = os.path.join(ROOT, "data", "interim", system, commit[:8], "model.json")
    if not os.path.exists(path):
        raise SystemExit(
            f"no model for {system}: run `python run_pipeline.py --system {system}` first"
        )
    with open(path, encoding="utf-8") as handle:
        model = json.load(handle)
    return {service["name"]: service["role"] for service in model["services"]}


def scan_bytes(blob: bytes) -> collections.Counter:
    found: collections.Counter = collections.Counter()
    for pattern in NAME_PATTERNS:
        for match in pattern.finditer(blob):
            found[match.group(1).decode("utf-8", "replace")] += 1
    # Names listed in an array rather than on a span. Counted once each, not per
    # occurrence: they are a declaration of what was present, not a measurement
    # of how often it was called.
    for match in ARRAY_PATTERN.finditer(blob):
        for item in ARRAY_ITEM.finditer(match.group(1)):
            found.setdefault(item.group(1).decode("utf-8", "replace"), 0)
    return found


def walk_archive(path: str) -> tuple[list[tuple[str, int]], collections.Counter, list[str]]:
    entries: list[tuple[str, int]] = []
    names: collections.Counter = collections.Counter()
    unreadable: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            entries.append((info.filename, info.file_size))
            if not info.filename.lower().endswith(TEXT_SUFFIXES):
                continue
            try:
                with archive.open(info) as handle:
                    names.update(scan_bytes(handle.read(SCAN_BUDGET)))
            except Exception as error:  # noqa: BLE001 - reporting beats crashing here
                unreadable.append(f"{info.filename}: {error}")
    return entries, names, unreadable


def walk_directory(root: str) -> tuple[list[tuple[str, int]], collections.Counter, list[str]]:
    entries: list[tuple[str, int]] = []
    names: collections.Counter = collections.Counter()
    unreadable: list[str] = []
    for directory, _, filenames in os.walk(root):
        for filename in filenames:
            full = os.path.join(directory, filename)
            relative = os.path.relpath(full, root)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            entries.append((relative, size))
            if not filename.lower().endswith(TEXT_SUFFIXES):
                continue
            try:
                with open(full, "rb") as handle:
                    names.update(scan_bytes(handle.read(SCAN_BUDGET)))
            except Exception as error:  # noqa: BLE001
                unreadable.append(f"{relative}: {error}")
    return entries, names, unreadable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="AnoMod.zip, or a directory it was extracted into")
    parser.add_argument("--system", default="trainticket")
    parser.add_argument("--top", type=int, default=40, help="how many entries to list")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        raise SystemExit(f"not found: {args.path}")

    if zipfile.is_zipfile(args.path):
        entries, names, unreadable = walk_archive(args.path)
    elif os.path.isdir(args.path):
        entries, names, unreadable = walk_directory(args.path)
    else:
        raise SystemExit(f"{args.path} is neither a zip archive nor a directory")

    total_bytes = sum(size for _, size in entries)
    print(f"archive     {args.path}")
    print(f"files       {len(entries)}  ({total_bytes / 1e6:.0f} MB uncompressed)")

    tops = collections.Counter(entry.split("/")[0] for entry, _ in entries)
    print("\ntop level")
    for name, count in tops.most_common(12):
        print(f"  {name:<40} {count:>6} files")

    suffixes = collections.Counter(os.path.splitext(entry)[1].lower() or "(none)" for entry, _ in entries)
    print("\nfile types")
    for suffix, count in suffixes.most_common(12):
        print(f"  {suffix:<40} {count:>6}")

    print(f"\nbiggest files")
    for entry, size in sorted(entries, key=lambda item: -item[1])[:8]:
        print(f"  {size / 1e6:>8.1f} MB  {entry}")

    if unreadable:
        print(f"\nunreadable ({len(unreadable)})")
        for line in unreadable[:5]:
            print(f"  {line}")

    # --- the measurement -------------------------------------------------
    modelled = modelled_services(args.system)
    commit, branch = pinned_snapshot(args.system)
    observed = {name for name in names if name.startswith("ts-") or name in modelled}
    other = sorted(set(names) - observed)

    print(f"\n{'=' * 68}")
    print(f"JOIN against {args.system} @ {commit[:8]} ({branch})")
    print(f"{'=' * 68}")
    if not names:
        print("\nNo service names found. The trace files are in a shape this script does not")
        print("recognise. Re-run with the layout above in hand and add the key to NAME_PATTERNS.")
        return 2

    matched = sorted(observed & set(modelled))
    only_traces = sorted(observed - set(modelled))
    only_model = sorted(set(modelled) - observed)
    functional_only_model = sorted(n for n in only_model if modelled[n] == "functional")

    print(f"\ndistinct service names in the data   {len(observed)}"
          f"{f'  (plus {len(other)} outside this system, listed below)' if other else ''}")
    print(f"services in the model                {len(modelled)}"
          f"  ({sum(1 for r in modelled.values() if r == 'functional')} functional)")
    print(f"\nin both                              {len(matched)}"
          f"   -> {100 * len(matched) / max(1, len(observed)):.0f}% of the traced services can carry observed evidence")
    print(f"traced but absent from the model     {len(only_traces)}")
    print(f"modelled but never traced            {len(only_model)}"
          f"   ({len(functional_only_model)} of them functional)")

    def show(title, items, counts=None):
        if not items:
            return
        print(f"\n{title}")
        width = max((len(name) for name in items[: args.top]), default=0)
        for name in items[: args.top]:
            suffix = f"  {counts[name]:>9} spans" if counts else ""
            print(f"  {name:<{width}}{suffix}".rstrip())
        if len(items) > args.top:
            print(f"  ... and {len(items) - args.top} more")

    show("matched (observed evidence will attach to these)", matched, names)
    show("traced but not modelled (would be dropped as evidence gaps)", only_traces, names)
    show("modelled and never traced (their metrics stay declared-only)", functional_only_model)
    # Never drop a name silently. A service that looks foreign may just be named
    # differently in the traces (a pod name, a namespace prefix), and that is a
    # mapping problem rather than a missing service.
    show("names outside this system (other subject, or a naming scheme to map)", other, names)

    print(f"\n{'=' * 68}")
    ratio = len(matched) / max(1, len(observed))
    if ratio > 0.9:
        print("Clean join. Keep the pinned branch and write the ingestion.")
    elif ratio > 0.6:
        print("Partial join. This is the DD-003 decision: re-pin to the dataset's branch, or")
        print("keep refactor/v2 and record every unmatched service as an evidence gap. Neither")
        print("is free, and the choice belongs in docs/06 before any ingestion code is written.")
    else:
        print("The join is too thin to build on. Either the dataset is from a different version")
        print("of the system, or the names are qualified differently (pod names, namespaces).")
        print("Check a sample trace by hand before deciding anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
