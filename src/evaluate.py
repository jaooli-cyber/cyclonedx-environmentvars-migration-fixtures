#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


SAFE_FLAG = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
CLASSIFICATIONS = {"EQUIVALENT_NORMALIZATION", "UNVERIFIABLE", "NOT_APPLICABLE"}


class EvaluationError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"cannot read JSON {path}: {exc}") from exc


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validator(schema_dir: Path) -> Draft202012Validator:
    root_path = schema_dir / "cyclonedx-2.0.schema.json"
    if not root_path.is_file():
        raise EvaluationError(f"root schema is absent: {root_path}")
    registry = Registry()
    for path in sorted(schema_dir.rglob("*.json")):
        contents = load_json(path)
        identifier = contents.get("$id") if isinstance(contents, dict) else None
        if identifier:
            registry = registry.with_resource(identifier, Resource.from_contents(contents))
    root = load_json(root_path)
    Draft202012Validator.check_schema(root)
    return Draft202012Validator(root, registry=registry, format_checker=FormatChecker())


def error_record(error: Any) -> dict[str, str]:
    pointer = "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in error.path)
    schema_pointer = "/" + "/".join(str(part) for part in error.schema_path)
    return {"path": pointer, "schemaPath": schema_pointer, "validator": str(error.validator), "message": error.message}


def validate(instance_validator: Draft202012Validator, document: dict[str, Any]) -> tuple[bool, list[dict[str, str]]]:
    errors = sorted(
        instance_validator.iter_errors(document),
        key=lambda item: ("/".join(str(part) for part in item.path), item.message),
    )
    return not errors, [error_record(error) for error in errors]


def environment_vars(document: dict[str, Any]) -> Any:
    try:
        return document["formulation"][0]["workflows"][0]["inputs"][0]["environmentVars"]
    except (KeyError, IndexError, TypeError) as exc:
        raise EvaluationError("fixture does not contain the expected environmentVars path") from exc


def replace_environment_vars(document: dict[str, Any], value: Any, suffix: str) -> dict[str, Any]:
    clone = json.loads(json.dumps(document))
    formula = clone["formulation"][0]
    workflow = formula["workflows"][0]
    formula["bom-ref"] += suffix
    workflow["bom-ref"] += suffix
    workflow["uid"] += suffix
    workflow["inputs"][0]["environmentVars"] = value
    return clone


def classify(document: dict[str, Any], shape: str) -> tuple[str, dict[str, Any] | None, str]:
    value = environment_vars(document)
    if shape == "legacy":
        if not isinstance(value, list):
            return "NOT_APPLICABLE", None, "legacy source is not an array"
        pairs = all(
            isinstance(item, dict)
            and set(item) == {"name", "value"}
            and isinstance(item["name"], str)
            and isinstance(item["value"], str)
            for item in value
        )
        if pairs:
            names = [item["name"] for item in value]
            if len(set(names)) != len(names):
                return "UNVERIFIABLE", None, "multiple legacy values share one target map key"
            migrated = replace_environment_vars(document, {item["name"]: item["value"] for item in value}, ":candidate")
            if any(not name for name in names):
                return "UNVERIFIABLE", migrated, "empty name is representable but has unresolved environment semantics"
            return "EQUIVALENT_NORMALIZATION", migrated, "unique string pairs map without value loss"
        if all(isinstance(item, str) for item in value):
            if len(set(value)) == len(value) and all(SAFE_FLAG.fullmatch(item) for item in value):
                migrated = replace_environment_vars(document, {item: "" for item in value}, ":candidate")
                return "EQUIVALENT_NORMALIZATION", migrated, "plain presence flags map to non-absent empty strings"
            return "UNVERIFIABLE", None, "legacy strings have no normative cross-system assignment grammar"
        return "NOT_APPLICABLE", None, "legacy source contains an unsupported item shape"
    if shape == "candidate":
        if not isinstance(value, dict):
            return "NOT_APPLICABLE", None, "candidate source is not an object"
        if any(not isinstance(item, (str, type(None))) for item in value.values()):
            return "NOT_APPLICABLE", None, "candidate source contains a value outside string or null"
        if any(item is None for item in value.values()):
            return "UNVERIFIABLE", None, "legacy property values have no exact explicit-null equivalent"
        migrated = replace_environment_vars(
            document, [{"name": name, "value": item} for name, item in sorted(value.items())], ":legacy"
        )
        if any(not name for name in value):
            return "UNVERIFIABLE", migrated, "empty name is representable but has unresolved environment semantics"
        return "EQUIVALENT_NORMALIZATION", migrated, "string-valued map converts to unique legacy properties"
    raise EvaluationError(f"unknown source shape: {shape}")


def evaluate(base_dir: Path, candidate_dir: Path, fixtures_dir: Path, expectations_path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = load_json(expectations_path)
    index = load_json(fixtures_dir / "case-index.json")
    indexed = {row["id"]: row for row in index.get("cases", [])}
    expected = manifest["expected"]["cases"]
    if set(indexed) != set(expected) or len(indexed) != manifest["expected"]["caseCount"]:
        raise EvaluationError("fixture index and expectations differ")
    validators = {"base": validator(base_dir), "candidate": validator(candidate_dir)}
    checks: list[dict[str, Any]] = []
    migrations: dict[str, dict[str, Any]] = {}
    for case_id in sorted(indexed):
        row = indexed[case_id]
        fixture = fixtures_dir / row["file"]
        if sha256(fixture) != row["sha256"]:
            raise EvaluationError(f"fixture hash mismatch: {case_id}")
        document = load_json(fixture)
        wanted = expected[case_id]
        for revision, instance_validator in validators.items():
            valid, errors = validate(instance_validator, document)
            observed = "VALID" if valid else "INVALID"
            checks.append({
                "id": f"{case_id}:{revision}", "kind": "SCHEMA_ACCEPTANCE",
                "expected": wanted[revision], "observed": observed,
                "passed": observed == wanted[revision], "errors": errors,
            })
        observed_class, migrated, reason = classify(document, row["shape"])
        if observed_class not in CLASSIFICATIONS:
            raise EvaluationError(f"unknown classification: {observed_class}")
        target = "candidate" if row["shape"] == "legacy" else "base"
        target_valid: bool | None = None
        target_errors: list[dict[str, str]] = []
        if migrated is not None:
            target_valid, target_errors = validate(validators[target], migrated)
            migrations[case_id] = migrated
        passed = observed_class == wanted["migration"]
        if "migratedTarget" in wanted:
            passed = passed and target_valid == (wanted["migratedTarget"] == "VALID")
        checks.append({
            "id": f"{case_id}:migration", "kind": "SEMANTIC_MIGRATION",
            "expected": wanted["migration"], "observed": observed_class,
            "targetRevision": target, "targetObserved": None if target_valid is None else ("VALID" if target_valid else "INVALID"),
            "passed": passed, "reason": reason, "targetErrors": target_errors,
        })
    counts = Counter(item["observed"] for item in checks if item["kind"] == "SEMANTIC_MIGRATION")
    failed = sum(not item["passed"] for item in checks)
    if len(checks) != manifest["expected"]["checkCount"]:
        raise EvaluationError("check count differs from expectations")
    if dict(sorted(counts.items())) != manifest["expected"]["migrationClassifications"]:
        raise EvaluationError("classification counts differ from expectations")
    return {
        "reportVersion": "1.0", "projectId": manifest["projectId"], "source": manifest["source"],
        "summary": {"cases": len(indexed), "checks": len(checks), "passed": len(checks) - failed,
                    "failed": failed, "migrationClassifications": dict(sorted(counts.items()))},
        "checks": checks,
    }, migrations


def write_junit(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    suite = ET.Element("testsuite", name=report["projectId"], tests=str(summary["checks"]), failures=str(summary["failed"]))
    for check in report["checks"]:
        case = ET.SubElement(suite, "testcase", classname=check["kind"], name=check["id"])
        if not check["passed"]:
            failure = ET.SubElement(case, "failure", message=f"expected {check['expected']}, observed {check['observed']}")
            failure.text = json.dumps(check, sort_keys=True)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def write_csv(path: Path, report: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "kind", "expected", "observed", "passed"],
            lineterminator="\n",
        )
        writer.writeheader()
        for check in report["checks"]:
            writer.writerow({key: check[key] for key in writer.fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-schema", required=True, type=Path)
    parser.add_argument("--candidate-schema", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--expectations", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        report, migrations = evaluate(args.base_schema, args.candidate_schema, args.fixtures, args.expectations)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "migrations").mkdir()
        (args.output_dir / "result.json").write_bytes(canonical_bytes(report))
        write_csv(args.output_dir / "result.csv", report)
        write_junit(args.output_dir / "junit.xml", report)
        for case_id, document in migrations.items():
            (args.output_dir / "migrations" / f"{case_id}.cdx.json").write_bytes(canonical_bytes(document))
        return 0 if report["summary"]["failed"] == 0 else 2
    except EvaluationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
