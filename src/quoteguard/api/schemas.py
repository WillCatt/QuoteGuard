"""API schemas."""

from __future__ import annotations

from quoteguard._compat import BaseModel, Field, ValidationError


class QuoteRequest(BaseModel):
    product_type: str
    property_type: str
    postcode: str
    security_features: str = ""
    occupancy: str

    def __post_init_model__(self) -> None:
        if self.product_type != "home_contents":
            raise ValidationError("QuoteRequest currently supports only home_contents")
        if len(self.postcode) != 4 or not self.postcode.isdigit():
            raise ValidationError("QuoteRequest.postcode must be a four-digit string")


class QuoteResponse(BaseModel):
    estimated_premium: float
    currency: str = "AUD"
    explanation: str = ""
    reference_id: str = Field(default="mock-price-v1")
