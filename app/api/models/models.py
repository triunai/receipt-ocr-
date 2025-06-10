from typing import List
from pydantic import BaseModel, Field

class ExpenseItem(BaseModel):
    item: str = Field(..., alias="name")
    price: float

class ParsedReceipt(BaseModel):
    vendor: str
    total: float 
    items: List[ExpenseItem]
    date: str 