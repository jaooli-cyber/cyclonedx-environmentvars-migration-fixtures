#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CASES: tuple[dict[str, Any], ...] = (
    {"id": "legacy-unique-pairs", "shape": "legacy", "environmentVars": [
        {"name": "LANG", "value": "en_US.UTF-8"}, {"name": "MY_FLAG", "value": ""}]},
    {"id": "legacy-plain-flag", "shape": "legacy", "environmentVars": ["MY_FLAG"]},
    {"id": "legacy-posix-assignment", "shape": "legacy", "environmentVars": ["LANG=en_US.UTF-8"]},
    {"id": "legacy-powershell-assignment", "shape": "legacy", "environmentVars": ["$Env:LANG='en_US.UTF-8'"]},
    {"id": "legacy-conflicting-name", "shape": "legacy", "environmentVars": [
        {"name": "MODE", "value": "safe"}, {"name": "MODE", "value": "fast"}]},
    {"id": "legacy-empty-name", "shape": "legacy", "environmentVars": [{"name": "", "value": ""}]},
    {"id": "candidate-string-map", "shape": "candidate", "environmentVars": {"LANG": "en_US.UTF-8", "MY_FLAG": ""}},
    {"id": "candidate-null-unset", "shape": "candidate", "environmentVars": {"LC_ALL": None}},
    {"id": "candidate-empty-name", "shape": "candidate", "environmentVars": {"": ""}},
    {"id": "candidate-nested-object", "shape": "candidate", "environmentVars": {"LC": {"ALL": None}}},
    {"id": "candidate-number", "shape": "candidate", "environmentVars": {"AMOUNT": 2}},
    {"id": "candidate-boolean", "shape": "candidate", "environmentVars": {"0TRUST": True}},
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def document(environment_vars: Any, case_id: str) -> dict[str, Any]:
    return {
        "$schema": "https://cyclonedx.org/schema/2.0/cyclonedx-2.0.schema.json",
        "specFormat": "CycloneDX",
        "specVersion": "2.0",
        "version": 1,
        "formulation": [{
            "bom-ref": f"formula:{case_id}",
            "workflows": [{
                "bom-ref": f"workflow:{case_id}",
                "uid": f"urn:example:synthetic:{case_id}",
                "name": f"Synthetic {case_id}",
                "taskTypes": ["build"],
                "inputs": [{"environmentVars": environment_vars}],
            }],
        }],
    }


def write_cases(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    index: list[dict[str, Any]] = []
    for case in CASES:
        filename = f"{case['id']}.cdx.json"
        payload = canonical_bytes(document(case["environmentVars"], case["id"]))
        (output_dir / filename).write_bytes(payload)
        index.append({
            "id": case["id"], "shape": case["shape"], "file": filename,
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
    result = {"corpusVersion": "1.0", "synthetic": True, "cases": index}
    (output_dir / "case-index.json").write_bytes(canonical_bytes(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    write_cases(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
