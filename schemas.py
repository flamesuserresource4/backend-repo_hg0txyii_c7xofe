"""
Database Schemas for TAXism

Each Pydantic model below represents a MongoDB collection. The collection
name is the lowercase of the class name (e.g., UserProfile -> "userprofile").

These schemas are used both for validation and to power the built-in
schema viewer via GET /schema.
"""
from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import date


class UserProfile(BaseModel):
    """Primary user profile and eligibility context"""
    full_name: str = Field(..., description="Full legal name")
    email: EmailStr = Field(..., description="Primary email")
    country: str = Field(..., description="Country of tax residence")
    filing_status: Literal["single", "married_joint", "married_separate", "head_of_household"] = Field(
        ..., description="Filing status"
    )
    employment_type: Literal["salaried", "self_employed", "business_owner", "creator", "consultant"] = Field(
        ..., description="Primary income type"
    )
    entities: List[str] = Field(default_factory=list, description="Entity types the user has or plans to set up")
    risk_tolerance: Literal["low", "medium", "high"] = Field("medium", description="Risk posture for strategy pacing")


class Memo(BaseModel):
    """Defense memo stored for an optimization position"""
    title: str = Field(..., description="Memo title")
    position_summary: str = Field(..., description="Plain-English description of the tax position")
    citations: List[str] = Field(default_factory=list, description="Optional citations placeholders")
    memo_text: str = Field(..., description="Generated memo body")


class DepreciationRecord(BaseModel):
    """Calculated depreciation schedule persisted for future reference"""
    asset_name: str = Field(..., description="Asset description")
    cost_basis: float = Field(..., ge=0, description="Cost basis")
    placed_in_service: date = Field(..., description="Placed in service date")
    method: Literal["SL"] = Field("SL", description="Depreciation method (SL only in MVP)")
    life_years: int = Field(..., ge=1, le=40, description="Recovery period in years")
    schedule: List[dict] = Field(..., description="Year-by-year schedule entries")


class HarvestPlan(BaseModel):
    """Tax-loss harvesting plan snapshot"""
    portfolio_name: str = Field(..., description="Label for the portfolio scan")
    threshold: float = Field(500.0, ge=0, description="Min absolute loss per position to consider (in currency)")
    positions_reviewed: int = Field(..., ge=0)
    candidates: List[dict] = Field(default_factory=list, description="Positions recommended for harvest with warnings")


# Example collections kept for reference but not used by TAXism UI
class User(BaseModel):
    name: str
    email: str
    address: Optional[str] = None
    is_active: bool = True

class Product(BaseModel):
    title: str
    price: float
    in_stock: bool = True
