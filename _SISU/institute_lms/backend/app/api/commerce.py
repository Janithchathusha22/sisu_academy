from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..dependencies.auth import Principal, get_current_user
from ..dependencies.authorization import institution_membership, resolve_institution
from ..schemas.resources import InvoiceCreate, InvoiceUpdate, PaymentCreate, PaymentUpdate
from ..services.access import ensure_manage, ensure_read, require_record
from ..services.repository import Repository, alias_record, alias_rows, get_repository, json_values

router = APIRouter(tags=["commerce"])


def _student_id(principal: Principal, institution_id: str) -> str | None:
    if principal.is_super_admin:
        return None
    membership = institution_membership(principal, institution_id)
    return membership.id if membership.role == "student" else None


def _invoice_visible(principal: Principal, invoice: dict) -> None:
    institution_id = str(invoice["institution_id"])
    student_id = _student_id(principal, institution_id)
    if student_id and str(invoice["student_membership_id"]) != student_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invoice access denied")


@router.get("/invoices")
def list_invoices(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    filters: dict[str, object] = {"institution_id": selected}
    student_id = _student_id(principal, selected)
    if student_id:
        filters["student_membership_id"] = student_id
    return alias_rows(repository.list("invoices", filters=filters, order="due_date", desc=False, limit=500))


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
def create_invoice(
    body: InvoiceCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    enrollment = require_record(repository, "enrollments", str(body.enrollment_id))
    institution_id = ensure_manage(repository, principal, "enrollments", enrollment, teachers=True)
    values = json_values(body)
    values.update(
        institution_id=institution_id,
        class_id=str(enrollment["class_id"]),
        student_membership_id=str(enrollment["student_membership_id"]),
        status="unpaid",
    )
    return alias_record(repository.create("invoices", values)) or {}


@router.get("/invoices/{invoice_id}")
def get_invoice(
    invoice_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    invoice = require_record(repository, "invoices", invoice_id)
    _invoice_visible(principal, invoice)
    return alias_record(invoice) or {}


@router.patch("/invoices/{invoice_id}")
def update_invoice(
    invoice_id: str,
    body: InvoiceUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    invoice = require_record(repository, "invoices", invoice_id)
    ensure_manage(repository, principal, "invoices", invoice, teachers=True)
    values = json_values(body)
    if values.get("status") == "paid" and not principal.platform_roles.intersection({"super_admin", "finance_admin"}):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only verified settlement can mark an invoice paid")
    return alias_record(repository.update("invoices", invoice_id, values)) or {}


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def void_invoice(
    invoice_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    invoice = require_record(repository, "invoices", invoice_id)
    ensure_manage(repository, principal, "invoices", invoice, teachers=True)
    if invoice.get("status") == "paid":
        raise HTTPException(status.HTTP_409_CONFLICT, "Paid invoices must be retained")
    repository.update("invoices", invoice_id, {"status": "void"})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/payments")
def list_payments(
    institution_id: str | None = Query(default=None),
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> list[dict]:
    selected = resolve_institution(principal, institution_id)
    assert selected is not None
    student_id = _student_id(principal, selected)
    if not student_id:
        return alias_rows(repository.list("payments", filters={"institution_id": selected}, limit=500))
    invoices = repository.list(
        "invoices",
        filters={"institution_id": selected, "student_membership_id": student_id},
        select="id",
        limit=500,
    )
    invoice_ids = [str(item["id"]) for item in invoices]
    if not invoice_ids:
        return []
    return alias_rows(repository.list("payments", in_filters={"invoice_id": invoice_ids}, limit=500))


@router.post("/payments", status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentCreate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    invoice = require_record(repository, "invoices", str(body.invoice_id))
    _invoice_visible(principal, invoice)
    if invoice.get("status") != "unpaid":
        raise HTTPException(status.HTTP_409_CONFLICT, "Invoice is not open for payment")
    values = {
        "institution_id": str(invoice["institution_id"]),
        "invoice_id": str(invoice["id"]),
        "amount_minor": int(invoice["amount_minor"]),
        "currency": invoice["currency"],
        "status": "pending",
        "provider": body.provider,
        "created_by": principal.id,
    }
    if body.provider_reference and principal.platform_roles.intersection({"super_admin", "finance_admin"}):
        values["provider_reference"] = body.provider_reference
    return alias_record(repository.create("payments", values)) or {}


@router.get("/payments/{payment_id}")
def get_payment(
    payment_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    payment = require_record(repository, "payments", payment_id)
    invoice = require_record(repository, "invoices", str(payment["invoice_id"]))
    _invoice_visible(principal, invoice)
    return alias_record(payment) or {}


def _require_finance(principal: Principal) -> None:
    if not principal.platform_roles.intersection({"super_admin", "finance_admin"}):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Finance role required")


@router.patch("/payments/{payment_id}")
def update_payment(
    payment_id: str,
    body: PaymentUpdate,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> dict:
    _require_finance(principal)
    require_record(repository, "payments", payment_id)
    return alias_record(repository.update("payments", payment_id, json_values(body))) or {}


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payment(
    payment_id: str,
    principal: Principal = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
) -> Response:
    _require_finance(principal)
    payment = require_record(repository, "payments", payment_id)
    if payment.get("status") != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Settled payment records must be retained")
    repository.delete("payments", payment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
