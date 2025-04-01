from pydantic import BaseModel
from datetime import date
from typing import List


class CreditBase(BaseModel):
    issuance_date: date
    is_closed: bool
    body: float
    percent: float

    class Config:
        from_attributes = True


class OpenCredit(CreditBase):
    return_date: date
    overdue_days: int
    body_payments: float
    percent_payments: float

    class Config:
        from_attributes = True


class ClosedCredit(CreditBase):
    actual_return_date: date
    total_payments: float

    class Config:
        from_attributes = True


class UserCredits(BaseModel):
    credits: List[OpenCredit | ClosedCredit]

    class Config:
        from_attributes = True


class PlanPerformance(BaseModel):
    plan_month: date
    category: str
    plan_sum: float
    actual_sum: float
    performance_percent: float

    class Config:
        from_attributes = True


class YearPerformanceMonth(BaseModel):
    month_year: date
    issuance_count: int
    issuance_plan: float
    issuance_sum: float
    issuance_performance: float
    payment_count: int
    payment_plan: float
    payment_sum: float
    payment_performance: float
    issuance_year_percent: float
    payment_year_percent: float

    class Config:
        from_attributes = True


class YearPerformance(BaseModel):
    performance: List[YearPerformanceMonth]

    class Config:
        from_attributes = True
