#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

"$root/scripts/acquire-schemas.sh" "$work/schemas"
python "$root/src/generate_cases.py" --output-dir "$work/fixtures"
diff -ru "$root/fixtures" "$work/fixtures"

python "$root/src/evaluate.py" \
  --base-schema "$work/schemas/base" \
  --candidate-schema "$work/schemas/candidate" \
  --fixtures "$work/fixtures" \
  --expectations "$root/expectations.json" \
  --output-dir "$work/results"
diff -ru "$root/results" "$work/results"

python "$root/src/mutate_expectation.py" \
  --source "$root/expectations.json" --output "$work/mutated-expectations.json"
set +e
python "$root/src/evaluate.py" \
  --base-schema "$work/schemas/base" \
  --candidate-schema "$work/schemas/candidate" \
  --fixtures "$work/fixtures" \
  --expectations "$work/mutated-expectations.json" \
  --output-dir "$work/mutated-results"
mutation_status=$?
set -e
if [[ $mutation_status -ne 2 ]]; then
  echo "mutation control returned $mutation_status; expected 2" >&2
  exit 1
fi

python -m unittest discover -s "$root/tests" -p 'test_*.py'
echo "Reference corpus, results and mutation control verified."
