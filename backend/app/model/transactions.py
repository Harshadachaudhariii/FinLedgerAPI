from pydantic import BaseModel, Field
from typing import Optional, Annotated, List,Literal
from app.enums.transaction import *
from datetime import date


class Transaction(BaseModel):
    type: Annotated[Literal["income", "expense"], Field(..., description="Type of transaction: income or expense")]
    category: Annotated[TransactionCategory, Field(..., description="Category of transaction")]
    amount: float=Field(..., description="Amount of transaction", gt=0)
    currency: str=Field(..., description="Currency of transaction")
    dates: date=Field(..., description="Date of transaction")    
    description: Optional[str]=Field(None, description="Description of transaction")
    merchant: Annotated[Optional[str], Field(None, max_length=100, description="Description of where user spend money")]
    payment_method: TransactionPaymentMethod=None
    status: Optional[TransactionStatus]=None
    notes:Optional[str]=None
    
class TransactionUpdate(BaseModel):
    type: Optional[Literal["income", "expense"]]=Field(None, description="Type of transaction: income or expense")
    category: Optional[TransactionCategory]=Field(None, description="Category of transaction")
    amount: Optional[float]=Field(None, description="Amount of transaction", gt=0)
    currency: Optional[str]=Field(None, description="Currency of transaction")
    dates: Optional[date]=Field(None, description="Date of transaction")    
    description: Optional[str]=Field(None, description="Description of transaction")
    merchant: Annotated[Optional[TransactionMerchant], Field(None,max_length=100, description="Description of where user spend money")]
    payment_method: Optional[TransactionPaymentMethod] =None
    status: Optional[TransactionStatus]=None
    notes:Optional[str]=None