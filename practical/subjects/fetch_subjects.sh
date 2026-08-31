#!/usr/bin/env bash
# Clone the three subject systems and pin the exact commit each was analysed at.
#
#   ./fetch_subjects.sh            clone if missing, then CHECK OUT THE PINNED SHA and verify
#   ./fetch_subjects.sh --update   move to branch HEAD and deliberately RE-PIN the lockfile
#
# Default mode never writes the lockfile. A replicator running this with no arguments gets
# exactly the commits recorded in subjects.lock.json, or a non-zero exit. Re-pinning is an
# explicit act, never a side effect of running the script.
#
# The clones are gitignored. subjects.lock.json is NOT — it is the reproducibility record
# that goes into the thesis. See docs/02-subject-systems.md.

set -euo pipefail
cd "$(dirname "$0")"

UPDATE=0
[[ "${1:-}" == "--update" ]] && UPDATE=1

# name|url|branch
SUBJECTS=(
  "petclinic|https://github.com/spring-petclinic/spring-petclinic-microservices.git|main"
  # refactor/v2 chosen over the frozen master (2022-11-01) — see docs/02-subject-systems.md
  "trainticket|https://github.com/FudanSELab/train-ticket.git|refactor/v2"
  "teastore|https://github.com/DescartesResearch/TeaStore.git|master"
)

# Read the pinned SHA for a subject out of the lockfile, if one is recorded.
pinned_sha() {
  [[ -f subjects.lock.json ]] || return 0
  python3 - "$1" <<'PY'
import json, sys
try:
    d = json.load(open("subjects.lock.json"))
except Exception:
    sys.exit(0)
for s in d.get("subjects", []):
    if s.get("name") == sys.argv[1]:
        print(s.get("commit", ""))
        break
PY
}

FAILED=0
for entry in "${SUBJECTS[@]}"; do
  IFS='|' read -r name url branch <<< "$entry"
  sha=$(pinned_sha "$name")

  if [[ ! -d "$name/.git" ]]; then
    echo "==> cloning $name"
    git clone --quiet "$url" "$name"
  fi

  if [[ $UPDATE -eq 1 ]]; then
    echo "==> updating $name to $branch HEAD"
    git -C "$name" fetch --quiet origin "$branch"
    # Reset rather than ff-merge: refactor/v2 is actively developed and may be force-pushed,
    # which would make --ff-only fail hard.
    git -C "$name" checkout --quiet -B "$branch" "origin/$branch"
  elif [[ -n "$sha" ]]; then
    echo "==> $name: checking out pinned $sha"
    git -C "$name" fetch --quiet origin "$branch" 2>/dev/null || true
    if ! git -C "$name" checkout --quiet "$sha" 2>/dev/null; then
      echo "    !! pinned commit $sha not found in $name" >&2
      FAILED=1
      continue
    fi
    if [[ "$(git -C "$name" rev-parse HEAD)" != "$sha" ]]; then
      echo "    !! $name is not at the pinned commit" >&2
      FAILED=1
    fi
  else
    echo "==> $name: no pin recorded; run --update to pin it"
  fi
done

if [[ $UPDATE -eq 0 ]]; then
  if [[ $FAILED -ne 0 ]]; then
    echo; echo "FAILED: one or more subjects could not be placed at their pinned commit." >&2
    exit 1
  fi
  echo; echo "All subjects at their pinned commits. Lockfile unchanged."
  exit 0
fi

echo "==> re-pinning subjects.lock.json"
{
  echo "{"
  echo "  \"pinned_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"subjects\": ["
  last=$(( ${#SUBJECTS[@]} - 1 ))
  for i in "${!SUBJECTS[@]}"; do
    IFS='|' read -r name url branch <<< "${SUBJECTS[$i]}"
    sha=$(git -C "$name" rev-parse HEAD)
    dt=$(git -C "$name" show -s --format=%cI HEAD)
    comma=","; [[ $i -eq $last ]] && comma=""
    printf '    { "name": "%s", "url": "%s", "branch": "%s", "commit": "%s", "committed_at": "%s" }%s\n' \
      "$name" "$url" "$branch" "$sha" "$dt" "$comma"
  done
  echo "  ]"
  echo "}"
} > subjects.lock.json

cat subjects.lock.json
echo
echo "Done. Cite the commit SHAs above in the thesis, not the branch names."
