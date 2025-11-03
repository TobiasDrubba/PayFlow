from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field, RootModel
from sqlalchemy.orm import Session

from app.data.repositories.payment_repository import SessionLocal
from app.domain.models.payment import Payment
from app.domain.services.auth_service import get_current_user
from app.domain.services.payment_service import (
    aggregate_payments_sankey_db,
    all_merchant_same_category_service,
    get_category_tree,
    get_payments_csv_stream,
    get_sums_for_ranges_service,
    import_payment_files_service,
    list_categories,
    list_payments,
    update_category_tree,
    update_merchant_categories,
    update_payment_category,
)


# --- Category models ---
class CategoryRequest(BaseModel):
    parent: str
    child: str
    subparent: Optional[str] = None


class CategoryTreeRequest(BaseModel):
    tree: Dict[str, Any]


class UpdateCategoryRequest(BaseModel):
    cust_category: str
    all_for_merchant: bool = False


class AggregateRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SumsRequest(RootModel):
    root: Dict[str, Dict[str, Optional[Any]]] = Field(
        ..., description="Mapping from name to {start, end, days}"
    )


class PaymentResponse(BaseModel):
    id: int
    date: datetime
    amount: float
    currency: str
    merchant: str
    auto_category: str
    source: str
    type: str
    note: str = ""
    cust_category: str = ""

    @staticmethod
    def from_domain(p: Payment) -> "PaymentResponse":
        return PaymentResponse(
            id=p.id,
            date=p.date,
            amount=p.amount,
            currency=p.currency,
            merchant=p.merchant,
            auto_category=p.auto_category,
            source=p.source.value if isinstance(p.source, Enum) else str(p.source),
            type=p.type.value,
            note=p.note or "",
            cust_category=p.category,
        )


class PaginatedPaymentsResponse(BaseModel):
    payments: List[PaymentResponse]
    total: int
    page: int
    page_size: int


router = APIRouter(prefix="/api/payments", tags=["payments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=PaginatedPaymentsResponse)
def get_all_payments_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    currency: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, description="Search term"),
    sort_field: str = Query("date", description="Field to sort by"),
    sort_direction: str = Query("desc", description="Sort direction: 'asc' or 'desc'"),
) -> PaginatedPaymentsResponse:
    payments, total = list_payments(
        db,
        current_user.id,
        currency,
        page,
        page_size,
        search,
        sort_field,
        sort_direction,
    )
    return PaginatedPaymentsResponse(
        payments=[PaymentResponse.from_domain(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=List[str])
def get_categories(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return list_categories(db, current_user.id)


@router.get("/categories/tree", response_model=Dict[str, Any])
def get_categories_tree(
    db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return get_category_tree(db, current_user.id)


@router.put("/categories/tree")
def update_categories_tree(
    req: CategoryTreeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    update_category_tree(req.tree, db, current_user.id)
    return {"status": "updated"}


@router.patch("/{payment_id}/category")
def update_payment_cust_category(
    payment_id: int,
    req: UpdateCategoryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        if req.all_for_merchant:
            updated = update_merchant_categories(
                payment_id, req.cust_category, db, current_user.id
            )
            return {"updated": updated}
        else:
            update_payment_category(payment_id, req.cust_category, db, current_user.id)
            return {"updated": 1}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class SankeyAggregateRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    days: Optional[int] = None


@router.post("/aggregate/sankey")
def aggregate_payments_sankey_endpoint(
    req: SankeyAggregateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    currency: Optional[str] = None,
):
    category_tree = get_category_tree(db, current_user.id)
    result = aggregate_payments_sankey_db(
        db,
        current_user.id,
        category_tree,
        start_date=req.start_date,
        end_date=req.end_date,
        currency=currency,
        days=req.days,
    )
    return result


@router.post("/sums")
def get_sums_for_ranges(
    req: SumsRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    currency: Optional[str] = None,
    days: Optional[int] = Query(
        None, description="Sum payments within X days before newest payment"
    ),
    months: Optional[int] = Query(
        None,
        description="Sum payments for the Xth previous month (0=current, 1=past, ...)",
    ),
):
    return get_sums_for_ranges_service(
        req.root, db, current_user.id, currency, days=days, months=months
    )


@router.post("/import")
async def import_payments_endpoint(
    files: list[UploadFile] = File(..., description="Up to 3 files"),
    types: list[str] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await import_payment_files_service(files, types, db, current_user.id)
    if result.get("errors"):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=400,
            content={
                "detail": f"Some files failed to import: {'; '.join(result['errors'])}",
                "imported": result["imported"],
            },
        )
    return {"imported": result["imported"]}


@router.get("/download")
def download_all_payments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    currency: Optional[str] = None,
):
    return get_payments_csv_stream(db, current_user.id, currency)


class SubmitPaymentRequest(BaseModel):
    date: datetime
    amount: float
    currency: str
    merchant: str
    type: str
    source: Optional[str] = None
    note: Optional[str] = ""
    category: Optional[str] = ""


@router.post("", response_model=PaymentResponse)
def submit_payment(
    req: SubmitPaymentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.domain.services.payment_service import submit_custom_payment

    try:
        payment = submit_custom_payment(
            date=req.date,
            amount=req.amount,
            currency=req.currency,
            merchant=req.merchant,
            payment_type=req.type,
            db=db,
            user_id=current_user.id,
            source=req.source,
            note=req.note,
            category=req.category,
        )
        return PaymentResponse.from_domain(payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class DeletePaymentsRequest(BaseModel):
    ids: List[int]


@router.post("/delete")
def delete_payments(
    req: DeletePaymentsRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.domain.services.payment_service import delete_payments_by_ids

    try:
        deleted = delete_payments_by_ids(req.ids, db, current_user.id)
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class BatchPaymentRequest(BaseModel):
    payments: List[SubmitPaymentRequest]


@router.post("/batch", response_model=List[PaymentResponse])
def submit_payments_batch(
    req: BatchPaymentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.domain.services.payment_service import add_payments_list

    payments_data = [p.model_dump() for p in req.payments]
    # Convert datetime fields if needed
    for p in payments_data:
        if isinstance(p["date"], str):
            from dateutil.parser import parse

            p["date"] = parse(p["date"])
    added_payments = add_payments_list(payments_data, db, current_user.id)
    return [PaymentResponse.from_domain(p) for p in added_payments]


class ExchangeRateRequest(BaseModel):
    start: datetime
    end: datetime


@router.post("/exchange-rates/fetch")
def fetch_exchange_rates_endpoint(
    req: ExchangeRateRequest,
    db: Session = Depends(get_db),
):
    from app.domain.services.payment_service import fetch_and_store_exchange_rates

    try:
        fetch_and_store_exchange_rates(db, req.start, req.end)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class AllMerchantSameCategoryRequest(BaseModel):
    merchant: str
    cust_category: str


@router.post("/all-merchant-same-category")
def all_merchant_same_category(
    req: AllMerchantSameCategoryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        result = all_merchant_same_category_service(
            db, current_user.id, req.merchant, req.cust_category
        )
        return {"all_same": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
