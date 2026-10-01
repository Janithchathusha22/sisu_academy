"""Small Supabase repository used by services and easily replaced by test fakes."""

from typing import Any, Protocol

from fastapi import Depends

from ..config import Settings
from ..database import user_client
from ..dependencies.auth import Principal, get_current_user, runtime_settings


class Repository(Protocol):
    def list(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        in_filters: dict[str, list[Any]] | None = None,
        select: str = "*",
        order: str = "created_at",
        desc: bool = True,
        limit: int = 200,
    ) -> list[dict[str, Any]]: ...

    def get(self, table: str, record_id: str, *, select: str = "*") -> dict[str, Any] | None: ...
    def create(self, table: str, values: dict[str, Any]) -> dict[str, Any]: ...
    def update(self, table: str, record_id: str, values: dict[str, Any]) -> dict[str, Any]: ...
    def delete(self, table: str, record_id: str) -> None: ...
    def count(self, table: str, *, filters: dict[str, Any] | None = None) -> int: ...


class SupabaseRepository:
    def __init__(self, client: Any):
        self.client = client

    def list(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        in_filters: dict[str, list[Any]] | None = None,
        select: str = "*",
        order: str = "created_at",
        desc: bool = True,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        query = self.client.table(table).select(select)
        for field, value in (filters or {}).items():
            query = query.eq(field, value)
        for field, values in (in_filters or {}).items():
            query = query.in_(field, values)
        if order:
            query = query.order(order, desc=desc)
        return query.limit(min(max(limit, 1), 500)).execute().data or []

    def get(self, table: str, record_id: str, *, select: str = "*") -> dict[str, Any] | None:
        rows = self.client.table(table).select(select).eq("id", record_id).limit(1).execute().data or []
        return rows[0] if rows else None

    def create(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        rows = self.client.table(table).insert(values).execute().data or []
        if not rows:
            raise RuntimeError(f"{table} insert returned no row")
        return rows[0]

    def update(self, table: str, record_id: str, values: dict[str, Any]) -> dict[str, Any]:
        rows = self.client.table(table).update(values).eq("id", record_id).execute().data or []
        if not rows:
            raise RuntimeError(f"{table} update returned no row")
        return rows[0]

    def delete(self, table: str, record_id: str) -> None:
        self.client.table(table).delete().eq("id", record_id).execute()

    def count(self, table: str, *, filters: dict[str, Any] | None = None) -> int:
        query = self.client.table(table).select("id", count="exact")
        for field, value in (filters or {}).items():
            query = query.eq(field, value)
        response = query.limit(1).execute()
        return int(response.count or 0)


def get_repository(
    principal: Principal = Depends(get_current_user),
    settings: Settings = Depends(runtime_settings),
) -> Repository:
    return SupabaseRepository(user_client(principal.token, settings))


def json_values(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=True)


def alias_record(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    if result.get("id") and not result.get("name"):
        result["name"] = result["id"]
    return result


def alias_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [alias_record(row) or {} for row in rows]
