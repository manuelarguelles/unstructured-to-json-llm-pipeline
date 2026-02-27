"""
models.py — Pydantic v2 schemas for structured extraction output.

Two core profiles:
  - CompanyProfile: general company data extracted from raw text
  - BuyerProfile: M&A buyer / PE firm data extracted from raw text
"""

from typing import Optional
from pydantic import BaseModel, field_validator


class CompanyProfile(BaseModel):
    """Structured profile of a company extracted from unstructured text."""

    company_name: str
    industry: str
    headquarters: Optional[str] = None
    employee_count: Optional[int] = None
    revenue_range: Optional[str] = None
    key_products: list[str] = []
    description: str
    confidence_score: float

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence_score must be between 0 and 1, got {v}")
        return round(v, 4)

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_name": "Acme Corp",
                "industry": "Technology",
                "headquarters": "San Francisco, CA",
                "employee_count": 1200,
                "revenue_range": "$50M-$100M",
                "key_products": ["CloudSync", "DataBridge", "AutoScale"],
                "description": "A mid-size SaaS company focused on cloud infrastructure.",
                "confidence_score": 0.92,
            }
        }
    }


class BuyerProfile(BaseModel):
    """Structured profile of a buyer / PE firm extracted from unstructured text."""

    company_name: str
    industry: str
    acquisition_interests: list[str] = []
    budget_range: Optional[str] = None
    key_contacts: list[dict] = []
    deal_history: list[str] = []
    confidence_score: float

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence_score must be between 0 and 1, got {v}")
        return round(v, 4)

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_name": "Initech Capital",
                "industry": "Private Equity",
                "acquisition_interests": ["B2B SaaS", "FinTech", "AI Infrastructure"],
                "budget_range": "$10M-$50M EBITDA",
                "key_contacts": [
                    {"name": "Bill Lumbergh", "title": "Managing Partner", "email": "blumbergh@initech.com"}
                ],
                "deal_history": ["Acquired DataCo 2022", "Merged with SyncSoft 2023"],
                "confidence_score": 0.87,
            }
        }
    }


# Schema registry — maps keyword hints to schema classes
SCHEMA_REGISTRY = {
    "company": CompanyProfile,
    "buyer": BuyerProfile,
    "pe": BuyerProfile,
    "capital": BuyerProfile,
    "ventures": BuyerProfile,
}


def infer_schema(filename: str) -> type[CompanyProfile] | type[BuyerProfile]:
    """Infer the appropriate Pydantic schema based on the filename."""
    name_lower = filename.lower()
    for keyword, schema in SCHEMA_REGISTRY.items():
        if keyword in name_lower:
            return schema
    return CompanyProfile  # default
