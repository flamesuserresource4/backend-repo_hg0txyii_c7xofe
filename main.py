import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime, date

from database import db, create_document, get_documents
from schemas import UserProfile, DepreciationRecord, HarvestPlan, Memo

app = FastAPI(title="TAXism API", description="Smart tax-planning and compliance platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "TAXism backend running"}


# --- Utility models for requests ---
class DepreciationInput(BaseModel):
    asset_name: str
    cost_basis: float = Field(..., ge=0)
    placed_in_service: date
    life_years: int = Field(..., ge=1, le=40)


# --- Health/Test ---
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["connection_status"] = "Connected"
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# --- Schemas endpoint for viewer ---
@app.get("/schema")
def get_schema():
    # Minimal reflection output to power a simple schema viewer
    return {
        "collections": [
            {
                "name": "userprofile",
                "fields": list(UserProfile.model_fields.keys()),
                "title": "User Profile",
            },
            {
                "name": "depreciationrecord",
                "fields": list(DepreciationRecord.model_fields.keys()),
                "title": "Depreciation Records",
            },
            {
                "name": "harvestplan",
                "fields": list(HarvestPlan.model_fields.keys()),
                "title": "Harvest Plans",
            },
            {
                "name": "memo",
                "fields": list(Memo.model_fields.keys()),
                "title": "Defense Memos",
            },
        ]
    }


# --- Core capability endpoints ---
@app.post("/api/profile", response_model=dict)
def create_or_update_profile(profile: UserProfile):
    try:
        inserted_id = create_document("userprofile", profile)
        return {"status": "ok", "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profile", response_model=List[dict])
def list_profiles(limit: int = 20):
    try:
        docs = get_documents("userprofile", limit=limit)
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/depreciation/calc", response_model=DepreciationRecord)
def calculate_depreciation(payload: DepreciationInput):
    # Straight-line depreciation MVP
    annual = round(payload.cost_basis / payload.life_years, 2)
    schedule = []
    for year in range(payload.life_years):
        schedule.append(
            {
                "year": year + 1,
                "amount": annual,
            }
        )

    record = DepreciationRecord(
        asset_name=payload.asset_name,
        cost_basis=payload.cost_basis,
        placed_in_service=payload.placed_in_service,
        method="SL",
        life_years=payload.life_years,
        schedule=schedule,
    )
    return record


@app.post("/api/depreciation/save", response_model=dict)
def save_depreciation(record: DepreciationRecord):
    try:
        inserted_id = create_document("depreciationrecord", record)
        return {"status": "ok", "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HarvestInput(BaseModel):
    portfolio_name: str
    positions: List[dict]  # {symbol, cost_basis, current_price, quantity}
    threshold: float = 500.0


@app.post("/api/harvest/scan", response_model=HarvestPlan)
def scan_tax_loss_harvest(payload: HarvestInput):
    candidates = []
    for p in payload.positions:
        cb = float(p.get("cost_basis", 0))
        cp = float(p.get("current_price", 0))
        qty = float(p.get("quantity", 0))
        unrealized = round((cp - cb) * qty, 2)
        if unrealized < -abs(payload.threshold):
            candidates.append(
                {
                    "symbol": p.get("symbol"),
                    "unrealized": unrealized,
                    "note": "Loss exceeds threshold. Confirm wash sale windows before execution.",
                }
            )

    plan = HarvestPlan(
        portfolio_name=payload.portfolio_name,
        threshold=payload.threshold,
        positions_reviewed=len(payload.positions),
        candidates=candidates,
    )
    return plan


class MemoInput(BaseModel):
    title: str
    position_summary: str


@app.post("/api/memo/generate", response_model=Memo)
def generate_defense_memo(payload: MemoInput):
    # Simple templated memo generator (no external AI)
    memo_text = (
        f"Position: {payload.title}\n\n"
        f"Summary: {payload.position_summary}\n\n"
        "Rationale: This position is taken based on commonly accepted interpretations "
        "of applicable tax rules and administrative guidance. The taxpayer has a good-"
        "faith basis and has maintained contemporaneous records.\n\n"
        "Citations: [Add statute/reg cite placeholders here].\n\n"
        "Disclosure: Where required, the position will be properly disclosed to the tax authority."
    )
    memo = Memo(
        title=payload.title,
        position_summary=payload.position_summary,
        citations=[],
        memo_text=memo_text,
    )
    return memo


# Simple flags for overlooked write-offs (mock rules)
class ExpenseInput(BaseModel):
    category: str
    amount: float


@app.post("/api/flags/writeoffs", response_model=dict)
def writeoff_flags(expenses: List[ExpenseInput]):
    flags = []
    total = 0.0
    for e in expenses:
        total += e.amount
        if e.category.lower() in {"home office", "r&d", "depreciation", "mileage"}:
            flags.append({"category": e.category, "hint": "Potential deduction – ensure substantiation."})
    return {"total_reviewed": round(total, 2), "flags": flags}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
