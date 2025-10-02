# app/presentation/api.py
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, Request
from pydantic import BaseModel, Field, RootModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.domain.models import Payment
from app.domain.services import list_payments
# --- Add these imports ---
from app.domain.services import (
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

# --- Endpoints ---



class PaymentResponse(BaseModel):
    id: str
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


app = FastAPI(title="Payment API", version="1.0.0")


# CORS config
origins = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",  # sometimes needed for localhost variants
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/payments", response_model=List[PaymentResponse])
def get_all_payments_endpoint() -> List[PaymentResponse]:
    """
    Returns all existing payments from persistent storage.
    """
    payments = list_payments()
    return [PaymentResponse.from_domain(p) for p in payments]

@app.get("/categories", response_model=List[str])
def get_categories():
    return list_categories()

@app.get("/categories/tree", response_model=Dict[str, Any])
def get_categories_tree():
    return get_category_tree()

@app.put("/categories/tree")
def update_categories_tree(req: CategoryTreeRequest):
    update_category_tree(req.tree)
    return {"status": "updated"}

@app.patch("/payments/{payment_id}/category")
def update_payment_cust_category(payment_id: str, req: UpdateCategoryRequest):
    try:
        if req.all_for_merchant:
            updated = update_merchant_categories(payment_id, req.cust_category)
            return {"updated": updated}
        else:
            update_payment_category(payment_id, req.cust_category)
            return {"updated": 1}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/payments/aggregate")
def aggregate_payments_endpoint(req: AggregateRequest):
    """
    Aggregates payments by category tree for a given date range.
    Returns nodes and links for Sankey diagram.
    """
    payments = list_payments()
    category_tree = get_category_tree()
    # Delegate aggregation logic to service layer
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

@app.post("/payments/aggregate/sankey")
def aggregate_payments_sankey_endpoint(req: SankeyAggregateRequest):
    """
    Aggregates payments and returns Sankey diagram data: nodes and links.
    """
    payments = list_payments()
    category_tree = get_category_tree()
    # Delegate Sankey aggregation logic to service layer
    result = aggregate_payments_sankey(
        payments,
        category_tree,
        start_date=req.start_date,
        end_date=req.end_date
    )
    return result

@app.post("/payments/sums")
def get_sums_for_ranges(req: SumsRequest = Body(...)):
    """
    Returns a mapping {name: sum} for each named date range.
    """
    # Move logic to service layer
    return get_sums_for_ranges_service(req.root)

@app.post("/payments/import")
async def import_payments_endpoint(
    files: list[UploadFile] = File(..., description="Up to 3 files"),
    types: list[str] = Form(...)
):
    """
    Import up to 3 payment files, each with its own type.
    """
    result = await import_payment_files_service(files, types)
    if result.get("errors"):
        return JSONResponse(
            status_code=400,
            content={"detail": f"Some files failed to import: {'; '.join(result['errors'])}", "imported": result["imported"]}
        )
    return {"imported": result["imported"]}

@app.get("/payments/download")
def download_all_payments():
    """
    Download all payments as a CSV file.
    """
    return get_payments_csv_stream()

class SubmitPaymentRequest(BaseModel):
    date: datetime
    amount: float
    currency: str
    merchant: str
    type: str
    source: Optional[str] = None
    note: Optional[str] = ""
    category: Optional[str] = ""

@app.post("/payments", response_model=PaymentResponse)
def submit_payment(req: SubmitPaymentRequest):
    """
    Submit a new payment. The id is set to 'custom+{date}'.
    """
    from app.domain.services import submit_custom_payment

    try:
        payment = submit_custom_payment(
            date=req.date,
            amount=req.amount,
            currency=req.currency,
            merchant=req.merchant,
            payment_type=req.type,
            source=req.source,
            note=req.note,
            category=req.category,
        )
        return PaymentResponse.from_domain(payment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class DeletePaymentsRequest(BaseModel):
    ids: List[str]

@app.post("/payments/delete")
def delete_payments(req: DeletePaymentsRequest):
    """
    Delete payments by their IDs.
    """
    from app.domain.services import delete_payments_by_ids
    try:
        deleted = delete_payments_by_ids(req.ids)
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
