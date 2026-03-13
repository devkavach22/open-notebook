from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PricingPlan(BaseModel):
    """Domain model for pricing plan"""
    id: Optional[str] = None
    name: str
    price: float
    currency: str = "USD"
    period: str = "month"
    description: str
    features: List[str]
    popular: bool = False
    active: bool = True
    max_notebooks: Optional[int] = None
    max_sources: Optional[int] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


class UserSubscription(BaseModel):
    """Domain model for user subscription"""
    id: Optional[str] = None
    user_id: str
    plan: str  # Record ID of pricing_plan
    status: str = "active"  # active, cancelled, expired
    start_date: datetime
    end_date: Optional[datetime] = None
    auto_renew: bool = True
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
