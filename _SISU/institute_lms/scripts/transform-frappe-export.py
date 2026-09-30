#!/usr/bin/env python3
"""Transform the two verified SISU Frappe entities into staged JSON.

This utility never opens a database connection and never creates Auth users.
Create Supabase Auth identities first, then provide an explicit old-user to UUID
mapping. Review the generated files before importing them into staging.
"""

from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, NAMESPACE_URL, uuid5


ROLE_MAP = {"Student": "student", "Teacher": "teacher", "Admin": "institute_admin"}
PROFILE_KIND = {"Student": "student", "Teacher": "teacher", "Admin": "institute"}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Transform IL Institute and IL Member CSV exports for Supabase staging."
    )
    result.add_argument("--input-dir", type=Path, required=True)
    result.add_argument("--auth-map", type=Path, required=True)
    result.add_argument("--output-dir", type=Path, required=True)
    result.add_argument("--source-site-id", required=True)
    return result


def find_export(directory: Path, names: tuple[str, ...]) -> Path:
    indexed = {item.name.casefold(): item for item in directory.iterdir() if item.is_file()}
    for name in names:
        if name.casefold() in indexed:
            return indexed[name.casefold()]
    raise FileNotFoundError(f"Missing export; expected one of: {', '.join(names)}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [{key: (value or "").strip() for key, value in row.items()} for row in csv.DictReader(stream)]


def stable_id(source_site_id: str, entity: str, legacy_name: str) -> str:
    if not legacy_name:
        raise ValueError(f"{entity} export contains a row without a Frappe name")
    return str(uuid5(NAMESPACE_URL, f"sisu:{source_site_id}:{entity}:{legacy_name}"))


def minor(value: str) -> int:
    try:
        amount = Decimal(value or "0")
    except InvalidOperation as exc:
        raise ValueError(f"Invalid money value: {value!r}") from exc
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError(f"Invalid money value: {value!r}")
    return int(amount * 100)


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_auth_map(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Auth map must be a non-empty JSON object")
    clean: dict[str, str] = {}
    for old_user, new_id in raw.items():
        clean[str(old_user).strip().casefold()] = str(UUID(str(new_id)))
    return clean


def write_json(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transform(args: argparse.Namespace) -> dict[str, int]:
    source = args.source_site_id.strip().lower()
    if not source or len(source) > 64:
        raise ValueError("source-site-id must contain 1-64 characters")

    institute_file = find_export(args.input_dir, ("IL Institute.csv", "il_institute.csv"))
    member_file = find_export(args.input_dir, ("IL Member.csv", "il_member.csv"))
    auth_map = load_auth_map(args.auth_map)
    institute_rows = read_csv(institute_file)
    member_rows = read_csv(member_file)

    institutions: list[dict] = []
    institution_ids: dict[str, str] = {}
    for row in institute_rows:
        legacy_name = row.get("name", "")
        identifier = stable_id(source, "institution", legacy_name)
        institution_ids[legacy_name] = identifier
        institutions.append(
            {
                "id": identifier,
                "legacy_source_site_id": source,
                "legacy_frappe_name": legacy_name,
                "code": row.get("code", "").upper(),
                "title": row.get("title", ""),
                "accent": row.get("accent") or None,
                "base_fee_minor": minor(row.get("base_fee", "0")),
                "billing_day": int(row.get("billing_day") or 1),
                "support_email": row.get("support_email") or None,
                "phone": row.get("phone") or None,
                "address": row.get("address") or None,
                "city": row.get("city") or None,
                "language": row.get("language") or "en",
                "school_mode": truthy(row.get("school_mode", "0")),
            }
        )

    profiles: dict[str, dict] = {}
    memberships: list[dict] = []
    for row in member_rows:
        old_user = row.get("user", "")
        user_id = auth_map.get(old_user.casefold())
        if not user_id:
            raise ValueError(f"No Supabase Auth UUID mapping for Frappe user {old_user!r}")
        institution_id = institution_ids.get(row.get("institute", ""))
        if not institution_id:
            raise ValueError(f"Unknown institute on member {row.get('name')!r}")
        old_role = row.get("role", "")
        if old_role not in ROLE_MAP:
            raise ValueError(f"Unsupported member role {old_role!r}")

        profiles[user_id] = {
            "id": user_id,
            "display_name": row.get("full_name") or old_user,
            "profile_kind": PROFILE_KIND[old_role],
            "language": row.get("language") or "en",
            "status": "verified",
        }
        memberships.append(
            {
                "id": stable_id(source, "membership", row.get("name", "")),
                "institution_id": institution_id,
                "user_id": user_id,
                "role": ROLE_MAP[old_role],
                "status": "active" if truthy(row.get("active", "1")) else "removed",
                "member_code": row.get("name") or None,
                "language": row.get("language") or "en",
                "legacy_source_site_id": source,
                "legacy_frappe_name": row.get("name", ""),
            }
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "institutions.json", institutions)
    write_json(args.output_dir / "profiles.json", list(profiles.values()))
    write_json(args.output_dir / "institution_memberships.json", memberships)
    return {
        "institutions": len(institutions),
        "profiles": len(profiles),
        "institution_memberships": len(memberships),
    }


def main() -> None:
    args = parser().parse_args()
    counts = transform(args)
    print(json.dumps({"transformed": counts, "database_written": False}, indent=2))


if __name__ == "__main__":
    main()
