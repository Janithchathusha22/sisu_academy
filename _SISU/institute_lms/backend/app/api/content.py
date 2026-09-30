from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..dependencies.auth import Principal, get_current_user
from ..dependencies.authorization import institution_membership, require_institution_role, resolve_institution
from ..schemas.resources import NewsCreate, NewsUpdate, NotificationCreate, NotificationUpdate
from ..services.access import ensure_read, require_record
from ..services.repository import Repository, alias_record, alias_rows, get_repository, json_values

router = APIRouter(tags=["communications"])


def _notification_allowed(principal: Principal, row: dict) -> None:
    institution_id = str(row["institution_id"])
    if principal.is_super_admin or str(row["recipient_user_id"]) == principal.id:
        return
    membership = institution_membership(principal, institution_id)
    if membership.role != "institute_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Notification access denied")


@router.get("/notifications")
def list_notifications(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    filters: dict[str, object] = {"institution_id": selected}
    membership = principal.membership_for(selected)
    if not principal.is_super_admin and (not membership or membership.role != "institute_admin"):
        filters["recipient_user_id"] = principal.id
    return alias_rows(repository.list("notifications", filters=filters, limit=500))


@router.post("/notifications", status_code=status.HTTP_201_CREATED)
def create_notification(
    body: NotificationCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    institution_id = str(body.institution_id)
    require_institution_role(principal, institution_id, "institute_admin", "teacher")
    recipients = repository.list(
        "institution_memberships",
        filters={"institution_id": institution_id, "user_id": str(body.recipient_user_id), "status": "active"},
        limit=1,
    )
    if not recipients:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Recipient is not an active institution member")
    values = json_values(body)
    values["created_by"] = principal.id
    return alias_record(repository.create("notifications", values)) or {}


@router.get("/notifications/{notification_id}")
def get_notification(
    notification_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "notifications", notification_id)
    _notification_allowed(principal, row)
    return alias_record(row) or {}


@router.patch("/notifications/{notification_id}")
def update_notification(
    notification_id: str,
    body: NotificationUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "notifications", notification_id)
    _notification_allowed(principal, row)
    return alias_record(repository.update("notifications", notification_id, json_values(body))) or {}


@router.delete("/notifications/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "notifications", notification_id)
    _notification_allowed(principal, row)
    repository.delete("notifications", notification_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/news")
def list_news(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    return alias_rows(repository.list("news", filters={"institution_id": selected}, limit=500))


@router.post("/news", status_code=status.HTTP_201_CREATED)
def create_news(
    body: NewsCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    institution_id = str(body.institution_id)
    membership = require_institution_role(principal, institution_id, "institute_admin", "teacher")
    values = json_values(body)
    values["author_user_id"] = principal.id
    if membership:
        values["author_membership_id"] = membership.id
    return alias_record(repository.create("news", values)) or {}


@router.get("/news/{news_id}")
def get_news(
    news_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "news", news_id)
    ensure_read(principal, str(row["institution_id"]))
    return alias_record(row) or {}


def _manage_news(principal: Principal, row: dict) -> None:
    institution_id = str(row["institution_id"])
    membership = require_institution_role(principal, institution_id, "institute_admin", "teacher")
    if membership and membership.role == "teacher" and str(row.get("author_membership_id")) != membership.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Teachers can edit only their own news")


@router.patch("/news/{news_id}")
def update_news(
    news_id: str,
    body: NewsUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    row = require_record(repository, "news", news_id)
    _manage_news(principal, row)
    return alias_record(repository.update("news", news_id, json_values(body))) or {}


@router.delete("/news/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(
    news_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    row = require_record(repository, "news", news_id)
    _manage_news(principal, row)
    repository.delete("news", news_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
