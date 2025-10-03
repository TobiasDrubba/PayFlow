from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Body, UploadFile, File, Form, Request, Depends
from pydantic import BaseModel, Field, RootModel
from app.domain.models import Payment
from app.domain.payment_service import list_payments
from app.domain.payment_service import (
    update_payment_category,
    update_merchant_categories,
    get_category_tree,
    update_category_tree,
    aggregate_payments_by_category,
    aggregate_payments_sankey,
    list_categories,
    get_sums_for_ranges_service,
    import_payment_files_service,
    get_payments_csv_stream,
)
from sqlalchemy.orm import Session
from app.data.payment_repository import SessionLocal
from app.domain.user_service import get_current_user

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
    root: Dict[str, Dict[str, Optional[datetime]]] = Field(..., description="Mapping from name to {start, end}")

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

router = APIRouter(prefix="/payments", tags=["payments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("", response_model=List[PaymentResponse])
def get_all_payments_endpoint(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
) -> List[PaymentResponse]:
    payments = list_payments(db, current_user.id)
    return [PaymentResponse.from_domain(p) for p in payments]

@router.get("/categories", response_model=List[str])
def get_categories(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return list_categories(db, current_user.id)

@router.get("/categories/tree", response_model=Dict[str, Any])
def get_categories_tree(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_category_tree(db, current_user.id)

@router.put("/categories/tree")
def update_categories_tree(
    req: CategoryTreeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    update_category_tree(req.tree, db, current_user.id)
    return {"status": "updated"}

@router.patch("/{payment_id}/category")
def update_payment_cust_category(
    payment_id: int,
    req: UpdateCategoryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    try:
        if req.all_for_merchant:
            updated = update_merchant_categories(payment_id, req.cust_category, db, current_user.id)
            return {"updated": updated}
        else:
            update_payment_category(payment_id, req.cust_category, db, current_user.id)
            return {"updated": 1}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/aggregate")
def aggregate_payments_endpoint(
    req: AggregateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payments = list_payments(db, current_user.id)
    category_tree = get_category_tree(db, current_user.id)
    result = aggregate_payments_by_category(
        payments,
        category_tree,
        start_date=req.start_date,
        end_date=req.end_date
    )
    return result

class SankeyAggregateRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

@router.post("/aggregate/sankey")
def aggregate_payments_sankey_endpoint(
    req: SankeyAggregateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payments = list_payments(db, current_user.id)
    category_tree = get_category_tree(db, current_user.id)
    result = aggregate_payments_sankey(
        payments,
        category_tree,
        start_date=req.start_date,
        end_date=req.end_date
    )
    return result

@router.post("/sums")
def get_sums_for_ranges(
    req: SumsRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_sums_for_ranges_service(req.root, db, current_user.id)

@router.post("/import")
async def import_payments_endpoint(
    files: list[UploadFile] = File(..., description="Up to 3 files"),
    types: list[str] = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await import_payment_files_service(files, types, db, current_user.id)
    if result.get("errors"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={"detail": f"Some files failed to import: {'; '.join(result['errors'])}", "imported": result["imported"]}
        )
    return {"imported": result["imported"]}

@router.get("/download")
def download_all_payments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return get_payments_csv_stream(db, current_user.id)

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
    current_user=Depends(get_current_user)
):
    from app.domain.payment_service import submit_custom_payment
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
    ids: List[str]

@router.post("/delete")
def delete_payments(
    req: DeletePaymentsRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from app.domain.payment_service import delete_payments_by_ids
    try:
        deleted = delete_payments_by_ids(req.ids, db, current_user.id)
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
