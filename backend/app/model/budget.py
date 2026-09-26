from typing import Optional, Annotated, List,Literal
from pydantic import BaseModel, Field
from app.enums.budget import *
from datetime import date
from app.enums.transaction import TransactionCategory

class BudgetCreate(BaseModel):
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(...,description="Amount of transaction", gt=0)
    month: str = Field(...,description="Month of transaction in YYYY-MM format",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    period: Literal["monthly"]
    
class Budget(BaseModel):
    user_id:str
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(...,description="Amount of transaction", gt=0)
    period: Literal["monthly"]
    month: str = Field(...,description="Month of transaction in YYYY-MM format",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    created_at:date
    
class BudgetUpdate(BaseModel):
    user_id:Optional[str] =None
    category:Optional[Annotated[TransactionCategory, Field(description="Category of transaction")]] =None
    amount: Optional[float]=Field(description="Amount of transaction", gt=0)
    period: Optional[Literal["monthly"]] =None
    month: Optional[str] = Field(None,description="Month of transaction in YYYY-MM format",
            pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    created_at:Optional[date] =None
    
class BudgetStatus(BaseModel):
    budget_id: str
    category:Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    budget_amount: float=Field(...,description="Amount of transaction", gt=0)
    spent_amount: float=Field(...,description="How much spent amount", ge=0)
    remaining_amount: float=Field(description="Remaining amount")
    percentage_used:float=Field(description="Percentage of spent amount")
    status:Annotated[BudgetStatusType, Field(..., description="Status of amount used ")]