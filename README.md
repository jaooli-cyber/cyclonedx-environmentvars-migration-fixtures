# CycloneDX 2.0 `environmentVars` migration fixtures

This repository provides a small, fully synthetic reproduction for the `environmentVars`
representation change proposed in CycloneDX specification pull request
[#1088](https://github.com/CycloneDX/specification/pull/1088).

It compares these exact revisions:

| Profile | Commit |
|---|---|
| `2.0-dev` base | `a1c8aeb2e4e6a72851fd937f210e9b5add1cf514` |
| PR #1088 head | `0ebfa3951e5cf0976e16debcf14c0ef8687fb4ef` |

The base profile accepts an array of property objects or arbitrary strings. The proposed profile
uses a system-independent JSON object whose values are strings or `null`.

## Result

Twelve synthetic documents produce 36 passing checks:

- 3 `EQUIVALENT_NORMALIZATION` cases;
- 6 `UNVERIFIABLE` migrations that require an external policy choice;
- 3 `NOT_APPLICABLE` invalid source shapes.

The checks confirm the expected breaking schema boundary and highlight four migration boundaries:

1. unique string pairs can be represented in the proposed map;
2. arbitrary shell-like strings have no normative cross-system parsing rule;
3. repeated legacy names cannot be represented losslessly by a map;
4. proposed `null` values have no exact legacy property-value equivalent.

Both pinned schemas accept an empty variable name in their respective representations. This is an
observation about schema acceptance, not a claim of standards non-conformance.

## Reproduce

Requirements: Git, Python 3.12 or later, and a POSIX shell.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
./scripts/verify-reference.sh
```

The script fetches the two exact upstream revisions, verifies their schema tree and file hashes,
regenerates the corpus and results, compares them with the committed reference artefacts, and
checks that a deliberately mutated expectation is rejected.

## Layout

- `fixtures/`: generated synthetic CycloneDX 2.0 documents;
- `expectations.json`: expected validity and conservative migration classification;
- `results/`: deterministic JSON, CSV, JUnit and migrated reference artefacts;
- `src/`: corpus generator, evaluator and mutation control;
- `scripts/`: pinned schema acquisition and clean reproduction;
- `tests/`: unit tests that require no network.

## Scope

This is a focused interoperability fixture set. It does not decide whether PR #1088 should be
accepted, define CycloneDX semantics, test a released CycloneDX 2.0 standard, or provide a general
SBOM/CBOM converter. All documents and identifiers are synthetic.

## Licence

Apache License 2.0. See [LICENSE](LICENSE).
