from typing import List, Optional
from pydantic import BaseModel, Field, AliasChoices

class ExpenseItem(BaseModel):
    item: str = Field(..., description="Name of the item purchased", validation_alias=AliasChoices('name', 'item'))
    price: float = Field(..., description="Price of the item")
    quantity: float = Field(default=1.0, description="Quantity of the item purchased")
    unit_price: Optional[float] = Field(None, description="Price per unit of the item")
    description: Optional[str] = Field(None, description="Additional description of the item")


class ParsedDocument(BaseModel):
    vendor: str = Field(..., description="Name of the vendor or store")
    total: float = Field(..., description="Total amount of the receipt")
    items: List[ExpenseItem] = []

    # Optional fields for more detailed documents like invoices
    invoice_id: Optional[str] = Field(None, description="Invoice or receipt number")
    order_id: Optional[str] = Field(None, description="Order or reference number")
    purchase_date: Optional[str] = Field(None, description="Date of the purchase", alias="date")
    purchase_time: Optional[str] = Field(None, description="Time of the purchase")
    currency: Optional[str] = Field(None, description="Currency of the transaction (e.g., MYR)")
    tax_amount: Optional[float] = Field(None, description="Total tax amount")
    subtotal: Optional[float] = Field(None, description="Subtotal before taxes and discounts")
    payment_method: Optional[str] = Field(None, description="Method of payment (e.g., cash, credit card)")