#!/usr/bin/env python3
"""Fail when the active runtime still references the retired Frappe stack."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".js", ".vue", ".html", ".toml", ".json"}
SKIP_PARTS = {
    "node_modules",
    "dist",
    "public",
    "tests",
    "preview",
    "__pycache__",
}

BACKEND_PATTERNS = {
    "Frappe import/runtime": re.compile(r"\bfrappe\b", re.IGNORECASE),
    "MariaDB/MySQL runtime": re.compile(r"\b(?:mariadb|mysql)\b", re.IGNORECASE),
    "Redis runtime": re.compile(r"\bredis\b", re.IGNORECASE),
    "Bench runtime": re.compile(r"\bbench\b", re.IGNORECASE),
    "retired reporting environment": re.compile(
        r"SISU_(?:FRAPPE|SUPABASE_SYNC|SUPABASE_DATABASE|SUPABASE_SOURCE)", re.IGNORECASE
    ),
}
FRONTEND_PATTERNS = {
    "Frappe RPC URL": re.compile(r"/api/method|institute_lms\.", re.IGNORECASE),
    "Frappe development proxy": re.compile(r"SISU_FRAPPE_URL", re.IGNORECASE),
    "Frappe login/session route": re.compile(
        r"[\"']/(?:login\?redirect|api/method/logout|me(?:[\"'#?]))"
    ),
    "Frappe CSRF template": re.compile(r"csrf_token|X-Frappe-CSRF", re.IGNORECASE),
}


def files_under(path: Path):
    if path.is_file():
        yield path
        return
    for item in path.rglob("*"):
        if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES and not SKIP_PARTS.intersection(item.parts):
            yield item


def scan(paths: list[Path], patterns: dict[str, re.Pattern[str]]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        for file in files_under(path):
            try:
                lines = file.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(lines, 1):
                for label, pattern in patterns.items():
                    if pattern.search(line):
                        findings.append(f"{file.relative_to(ROOT)}:{number}: {label}")
    return findings


def main() -> int:
    findings = scan([ROOT / "backend", ROOT / "pyproject.toml"], BACKEND_PATTERNS)
    findings += scan(
        [ROOT / "frontend" / "src", ROOT / "frontend" / "vite.config.js", ROOT / "frontend" / "index.html"],
        FRONTEND_PATTERNS,
    )
    if findings:
        print("Retired runtime references found:")
        print("\n".join(f"- {item}" for item in findings))
        return 1
    print("Active runtime is free of Frappe, Bench, MariaDB, Redis and retired reporting references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
