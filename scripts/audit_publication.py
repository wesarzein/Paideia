"""Conservative outgoing-history inventory. Findings never print matched values.

This supplements manual source/dataset review; it cannot certify absence of PII.
"""

import argparse
import json
import re
import subprocess
from pathlib import PurePosixPath

PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})"
    ),
    "aws_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "signed_jwt": re.compile(
        rb"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"
    ),
}


def git(*args):
    return subprocess.check_output(["git", *args])


def inventory(base):
    commits = git("rev-list", f"{base}..HEAD").decode().splitlines()
    objects = {}
    for commit in commits:
        for item in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
            if not item:
                continue
            metadata, name = item.split(b"\t", 1)
            mode, kind, oid = metadata.decode().split()
            path = name.decode("utf-8")
            if kind == "blob":
                objects.setdefault((oid, path), set()).add(commit[:12])
    findings, data_files, binaries = [], set(), set()
    for (oid, path), revisions in sorted(objects.items()):
        file = PurePosixPath(path)
        forbidden = (
            path.startswith(("config/local/", "database/local/", "database/backups/"))
            and file.name != ".gitkeep"
        ) or (file.name == ".env" or file.suffix == ".env")
        if forbidden or file.suffix.lower() in {
            ".dump",
            ".bak",
            ".pkl",
            ".joblib",
            ".pem",
            ".key",
        }:
            findings.append(
                {
                    "path": path,
                    "kind": "private_path_or_artifact",
                    "commits": sorted(revisions),
                }
            )
        data = git("cat-file", "blob", oid)
        for name, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append(
                    {"path": path, "kind": name, "commits": sorted(revisions)}
                )
        if (
            file.suffix.lower() in {".json", ".csv", ".xlsx", ".xls", ".sql"}
            and "package-lock" not in path
        ):
            data_files.add(path)
        if b"\0" in data:
            binaries.add(path)
    return {
        "base": base,
        "commit_count": len(commits),
        "blob_path_versions": len(objects),
        "findings": findings,
        "data_files_to_review": sorted(data_files),
        "binary_files_to_review": sorted(binaries),
        "manual_pii_review_required": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args()
    result = inventory(args.base)
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["findings"] else 0)
