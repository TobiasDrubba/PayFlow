# app/presentation/api.py
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.domain.models import Payment
from app.domain.services import list_payments
# --- Add these imports ---
from app.domain.services import (
    list_categories,
    add_category,
    update_payment_category,
    update_merchant_categories,
    get_category_tree,
    update_category_tree,
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
            cust_category=p.cust_category,
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

@app.post("/categories", response_model=str)
def create_category(req: CategoryRequest):
    return add_category(req.parent, req.child, req.subparent)

@app.get("/categories/tree", response_model=Dict[str, Any])
def get_categories_tree():
    return get_category_tree()

@app.put("/categories/tree")
def update_categories_tree(req: CategoryTreeRequest):
    update_category_tree(req.tree)
    return {"status": "updated"}

@app.patch("/payments/{payment_id}/category")
def update_payment_cust_category(payment_id: str, req: UpdateCategoryRequest):
    if req.all_for_merchant:
        updated = update_merchant_categories(payment_id, req.cust_category)
        return {"updated": updated}
    else:
        update_payment_category(payment_id, req.cust_category)
        return {"updated": 1}
