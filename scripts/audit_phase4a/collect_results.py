"""Publish only enumerated synthetic audit results, never private context/files."""

import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sources = (
        "api-results.json",
        "browser-results.json",
        "browser-extra-results.json",
        "supplemental-results.json",
        "persistence-results.json",
    )
    checks = []
    for name in sources:
        values = json.loads((args.private / name).read_text(encoding="utf-8"))
        for item in values:
            assert set(item) == {"id", "expected", "observed", "status"}
            assert item["status"] in {"verified", "defect", "unverified"}
            checks.append(dict(item, source=name))
    assert len({c["id"] for c in checks}) == len(checks)
    counts = dict(Counter(c["status"] for c in checks))
    result = dict(
        source_commit="1d346eb",
        branch="dev/phase4a-academic-audit",
        synthetic_only=True,
        institutional_database_unchanged=True,
        baseline_regression=dict(passed=52, warnings=22),
        audit_counts=dict(total=len(checks), **counts),
        excel_structure=json.loads((args.private / "excel-structure.json").read_text()),
        openapi_routes=json.loads((args.private / "route-inventory.json").read_text()),
        checks=checks,
    )
    text = json.dumps(result, indent=2, ensure_ascii=False)
    assert "Bearer " not in text and "postgresql+psycopg://" not in text
    assert "synthetic_password" not in text and "password_hash" not in text
    output = root / "docs/academic/auditoria-fase4a-resultados.json"
    output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps(dict(checks=len(checks), **counts)))


if __name__ == "__main__":
    main()
