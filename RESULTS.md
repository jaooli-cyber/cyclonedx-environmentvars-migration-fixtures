# Reference results

The committed results were generated from the exact schema revisions recorded in
[`expectations.json`](expectations.json). All 36 registered checks pass.

| Case | Base schema | PR #1088 schema | Conservative migration |
|---|---|---|---|
| Unique legacy pairs | Valid | Invalid | `EQUIVALENT_NORMALIZATION` |
| Plain legacy flag | Valid | Invalid | `EQUIVALENT_NORMALIZATION` |
| POSIX-like assignment | Valid | Invalid | `UNVERIFIABLE` |
| PowerShell-like assignment | Valid | Invalid | `UNVERIFIABLE` |
| Conflicting duplicate name | Valid | Invalid | `UNVERIFIABLE` |
| Empty legacy name | Valid | Invalid | `UNVERIFIABLE`; migrated shape is valid |
| Candidate string map | Invalid | Valid | `EQUIVALENT_NORMALIZATION` |
| Candidate `null` value | Invalid | Valid | `UNVERIFIABLE` |
| Empty candidate name | Invalid | Valid | `UNVERIFIABLE`; migrated shape is valid |
| Candidate nested object | Invalid | Invalid | `NOT_APPLICABLE` |
| Candidate number | Invalid | Invalid | `NOT_APPLICABLE` |
| Candidate boolean | Invalid | Invalid | `NOT_APPLICABLE` |

`EQUIVALENT_NORMALIZATION` means that this fixture can be represented in the target shape under
the explicit policy implemented by this reproduction. `UNVERIFIABLE` means that a neutral
migration cannot select one target meaning without an external policy. `NOT_APPLICABLE` means
that the source shape is not valid for the proposed representation being tested.

These results describe the two pinned draft revisions only. They are not a conformance statement
about a released CycloneDX 2.0 specification.
